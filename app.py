from flask import Flask, request, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
import yt_dlp

app = Flask(__name__)
socketio = SocketIO(app)
download_directory = '/home/media'  # Change this to your desired download directory

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
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        download_audio(url)
        return redirect(url_for('index'))
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5500)
