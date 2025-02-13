import os
import subprocess
from app import app, db
import time

# Creazione automatica del database se non esiste
with app.app_context():
    db.create_all()

# Avvia Celery in background e registra i log
def start_celery():
    log_file = "celery.log"
    
    with open(log_file, "w") as f:
        celery_worker_cmd = [
            "celery", "-A", "app.celery_worker.celery", "worker", "--loglevel=info"
        ]
        subprocess.Popen(celery_worker_cmd, stdout=f, stderr=f)

    # Attendere qualche secondo per verificare se Celery è partito
    time.sleep(3)
    with open(log_file, "r") as f:
        logs = f.read()
        if "ERROR" in logs or "Exception" in logs:
            print("⚠️  Errore nel processo Celery! Controlla celery.log per dettagli.")
        else:
            print("✅ Celery avviato correttamente!")

if __name__ == '__main__':
    start_celery()  # Avvia Celery automaticamente
    app.run(host='0.0.0.0', port=5000, debug=True)

