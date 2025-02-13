import yt_dlp
import os
import acoustid
import musicbrainzngs
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB
from pydub import AudioSegment
from app.celery_worker import celery

# Configura MusicBrainz
musicbrainzngs.set_useragent("Ytdownloader", "1.0", "iris180196@gmail.com")

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

LOG_FILE = os.path.join(DOWNLOAD_FOLDER, "fingerprint.log")

def log_message(message):
    """Scrive un messaggio nel file di log."""
    with open(LOG_FILE, "a") as f:
        f.write(f"{message}\n")
    print(message)

@celery.task(name="download_video_task")
def download_video_task(url, format_type, fingerprinting=False):
    """Scarica il video/audio e applica il fingerprinting se richiesto."""
    log_message(f"🔹 Iniziato download: {url} | Formato: {format_type} | Fingerprinting: {fingerprinting}")

    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
    }

    if format_type == 'video':
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
    elif format_type == 'audio':
        ydl_opts['format'] = 'bestaudio'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info_dict)
        output_file = filename.replace('.webm', '.mp3') if format_type == 'audio' else filename

    if format_type == 'audio' and fingerprinting:
        log_message(f"🎵 Fingerprinting attivato per {output_file}")
        apply_fingerprinting(output_file)

    return {"status": "COMPLETED", "filename": os.path.basename(output_file)}

def apply_fingerprinting(audio_file):
    """Esegue fingerprinting e aggiunge metadati da MusicBrainz."""
    
    try:
        print(f"🎵 Fingerprinting attivato per {audio_file}")

        # Controlla se il file esiste prima di procedere
        if not os.path.exists(audio_file):
            print(f"❌ Errore: File non trovato - {audio_file}")
            return

        # Esegui fingerprinting
        duration, fingerprint = acoustid.fingerprint_file(audio_file)

        print(f"🔍 Fingerprint generato: {fingerprint}")

        # Cerca la traccia su MusicBrainz
        result = acoustid.lookup("rUhtVeMTV6", fingerprint, duration)

        if not result or result['status'] != 'ok' or not result['results']:
            print("❌ Nessun risultato trovato per il fingerprint")
            return

        track_info = result['results'][0]['recordings'][0]
        title = track_info.get('title', 'Sconosciuto')
        artist = track_info.get('artists', [{}])[0].get('name', 'Sconosciuto')
        album = track_info.get('releasegroups', [{}])[0].get('title', 'Sconosciuto')

        print(f"🎵 Metadati trovati: {artist} - {title} (Album: {album})")

        # Aggiungi i metadati al file MP3
        audio = MP3(audio_file, ID3=ID3)
        if not audio.tags:
            audio.tags = ID3()

        audio.tags.add(TIT2(encoding=3, text=title))  # Titolo
        audio.tags.add(TPE1(encoding=3, text=artist))  # Artista
        audio.tags.add(TALB(encoding=3, text=album))  # Album
        audio.save()

        print("✅ Metadati salvati correttamente!")

    except Exception as e:
        print(f"❌ Errore nel fingerprinting: {str(e)}")
