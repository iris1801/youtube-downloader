from flask import Flask, request, render_template, jsonify
from flask_socketio import SocketIO, emit
import yt_dlp
import musicbrainzngs
from mutagen.easyid3 import EasyID3
import os

app = Flask(__name__)
socketio = SocketIO(app)
download_directory = '/home/media'  # Change this to your desired download directory

musicbrainzngs.set_useragent("YT-Downloader", "0.86", "matteo@tripalle.it")

class MyLogger:
    def __init__(self):
        self.msgs = []

    def debug(self, msg):
        self.log(msg)

    def warning(self, msg):
        self.log(msg)

    def error(self, msg):
        self.log(msg)

    def log(self, msg):
        self.msgs.append(msg)
        socketio.emit('log', msg)

def progress_hook(d):
    if d['status'] == 'finished':
        socketio.emit('progress', {'status': 'finished'})
    elif d['status'] == 'downloading':
        p = d['_percent_str'].strip()
        socketio.emit('progress', {'status': 'downloading', 'progress': p})

def fetch_metadata(title):
    try:
        result = musicbrainzngs.search_recordings(recording=title, limit=1)
        recording = result['recording-list'][0]
        artist = recording['artist-credit'][0]['artist']['name']
        album = recording['release-list'][0]['title']
        track_title = recording['title']
        return {'artist': artist, 'album': album, 'title': track_title}
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        return None

def apply_metadata(file_path, metadata):
    try:
        audio = EasyID3(file_path)
        audio['artist'] = metadata['artist']
        audio['album'] = metadata['album']
        audio['title'] = metadata['title']
        audio.save()
    except Exception as e:
        print(f"Error applying metadata: {e}")

def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{download_directory}/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'logger': MyLogger(),
        'progress_hooks': [progress_hook],
        'noplaylist': True  # Ensures only the first video in the playlist is downloaded
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        title = info_dict.get('title', None)
        file_path = f"{download_directory}/{title}.mp3"
        
        if title:
            metadata = fetch_metadata(title)
            if metadata:
                artist_directory = os.path.join(download_directory, metadata['artist'])
                if not os.path.exists(artist_directory):
                    os.makedirs(artist_directory)
                
                new_file_path = os.path.join(artist_directory, f"{title}.mp3")
                os.rename(file_path, new_file_path)
                apply_metadata(new_file_path, metadata)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    download_audio(url)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5500, debug=True)
