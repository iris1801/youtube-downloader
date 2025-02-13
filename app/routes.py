import yt_dlp
import os
import urllib.parse
from werkzeug.utils import safe_join
from flask import jsonify, send_file, render_template, request, redirect, url_for, send_from_directory
from flask_login import login_required, current_user
from celery.result import AsyncResult
from app import app
from app.forms import SearchForm
from app.tasks import download_video_task
from app.celery_worker import celery  # Import corretto

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)  # Assicura che la cartella esista

def search_youtube(query):
    """Funzione che usa yt-dlp per cercare video su YouTube."""
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch5',  # Cerca i primi 5 risultati
        'skip_download': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)

    results = []
    if 'entries' in info:
        for entry in info['entries']:
            results.append({
                'title': entry['title'],
                'url': entry['webpage_url'],
                'thumbnail': entry.get('thumbnail', ''),
                'duration': entry.get('duration', 0),
            })

    return results


@app.route('/')
def home():
    return redirect(url_for('dashboard'))  # Reindirizza direttamente alla dashboard


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    """Gestisce la dashboard e visualizza i file scaricati."""
    form = SearchForm()
    results = None
    files = get_downloaded_files()  # Ottieni la lista dei file scaricati

    if form.validate_on_submit():
        results = search_youtube(form.query.data)

    return render_template('dashboard.html', user=current_user, form=form, results=results, files=files)


@app.route('/download/<format_type>/<path:url>', methods=['POST'])
@login_required
def download(format_type, url):
    """Avvia il download in background con o senza fingerprinting."""
    data = request.get_json()
    fingerprinting = data.get("fingerprinting", False)  # ✅ Legge correttamente il valore

    print(f"[DEBUG] Fingerprinting ricevuto: {fingerprinting}")  # ✅ Debug per controllare

    task = celery.send_task("download_video_task", args=[url, format_type, fingerprinting])
    return jsonify({"task_id": task.id, "status": "Iniziato"})


@app.route('/task_status/<task_id>')
@login_required
def task_status(task_id):
    """Restituisce lo stato del download in corso con una gestione chiara."""
    task = AsyncResult(task_id, app=celery)

    # Se il task è fallito, interrompiamo il polling
    if task.state == 'FAILURE':
        return jsonify({"task_id": task.id, "status": "FAILED", "message": str(task.result)})

    # Se il task è completato, restituiamo il risultato finale
    if task.state == 'SUCCESS':
        return jsonify({"task_id": task.id, "status": "COMPLETED", "result": task.result})

    return jsonify({"task_id": task.id, "status": task.state})


def get_downloaded_files():
    """Restituisce la lista dei file già scaricati."""
    return [f for f in os.listdir(DOWNLOAD_FOLDER) if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, f))]




@app.route('/downloaded/<path:filename>')
@login_required
def downloaded_file(filename):
    """Permette di scaricare i file completati gestendo spazi e caratteri speciali."""
    decoded_filename = urllib.parse.unquote(filename)  # Decodifica gli spazi e caratteri speciali
    safe_filename = os.path.join(os.getcwd(), DOWNLOAD_FOLDER, decoded_filename)

    if not os.path.exists(safe_filename):
        return jsonify({"error": f"File non trovato: {decoded_filename}"}), 404

    return send_file(safe_filename, as_attachment=True)


@app.route('/delete/<filename>', methods=['DELETE'])
@login_required
def delete_file(filename):
    """Elimina un file scaricato."""
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": f"File {filename} eliminato con successo"})
    return jsonify({"error": "File non trovato"}), 404

