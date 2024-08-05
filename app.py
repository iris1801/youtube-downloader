from flask import Flask, request, render_template, jsonify
from flask_socketio import SocketIO, emit
import yt_dlp
import musicbrainzngs
from mutagen.easyid3 import EasyID3
import os

app = Flask(__name__)
socketio = SocketIO(app)
download_directory = '/home/media'  # Change this to your desired download directory

# Proxy settings
#http_proxy = "http://proxy-server-address:port"
#https_proxy = "http://proxy-server-address:port"
#os.environ['HTTP_PROXY'] = http_proxy
#os.environ['HTTPS_PROXY'] = https_proxy

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
        socketio.emit('log', {'msg': msg})

def progress_hook(d):
    if d['status'] == 'finished':
        socketio.emit('progress', {'status': 'finished'})
    elif d['status'] == 'downloading':
        p = d['_percent_str'].strip()
        socketio.emit('progress', {'status': 'downloading', 'progress': p})

def fetch_metadata(title):
    try:
        result = musicbrainzngs.search_recordings(recording=title, limit=1)
        if result['recording-list']:
            recording = result['recording-list'][0]
            recording_id = recording['id']
            return musicbrainzngs.get_recording_by_id(recording_id, includes=["artists", "releases"])
        else:
            return None
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        return None

def apply_metadata(file_path, metadata):
    try:
        audio = EasyID3(file_path)
        if 'artist-credit' in metadata['recording']:
            audio['artist'] = metadata['recording']['artist-credit'][0]['artist']['name']
        if 'release-list' in metadata['recording']:
            audio['album'] = metadata['recording']['release-list'][0]['title']
        audio['title'] = metadata['recording']['title']
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
        file_path = f
