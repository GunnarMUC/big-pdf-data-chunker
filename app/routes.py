import os
import shutil
import zipfile
from pathlib import Path
from flask import Blueprint, render_template, request, send_file, current_app
from redis import Redis
from rq import Queue

from app.models import generate_job_id

bp = Blueprint("main", __name__)


def _get_redis() -> Redis:
    return Redis.from_url(current_app.config["REDIS_URL"])


def _get_queue() -> Queue:
    return Queue("chunker-jobs", connection=_get_redis())


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    if not files or all(not f.filename for f in files):
        return '<p class="error-message">Keine Dateien ausgewählt</p>', 400

    cards = []
    for f in files:
        if not f.filename:
            continue

        job_id = generate_job_id()
        upload_dir = Path(current_app.config["UPLOAD_FOLDER"]) / job_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        output_dir = Path(current_app.config["OUTPUT_FOLDER"]) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        upload_path = upload_dir / f.filename
        f.save(str(upload_path))

        q = _get_queue()
        q.enqueue(
            "worker.process_single_file",
            str(upload_path),
            job_id,
            job_id=job_id,
            result_ttl=86400,
            job_timeout=current_app.config["RQ_TIMEOUT"],
        )

        cards.append(
            render_template("job_card.html", job_id=job_id, progress=0, message="In Warteschlange…")
        )

    return "".join(cards)


@bp.route("/status/<job_id>")
def status(job_id):
    q = _get_queue()
    job = q.fetch_job(job_id)

    if job is None:
        return render_template("job_card.html", job_id=job_id, status="error", message="Job nicht gefunden", progress=0)

    progress = job.meta.get("progress", 0.0) if job.meta else 0.0
    message = job.meta.get("message", "") if job.meta else ""

    if job.is_finished:
        output_dir = Path(current_app.config["OUTPUT_FOLDER"]) / job_id
        zip_path = output_dir / "output.zip"
        if zip_path.exists():
            return render_template("job_card.html", job_id=job_id, status="done", progress=1.0, message="Fertig!")
        return render_template("job_card.html", job_id=job_id, status="error", message="Ausgabedatei nicht gefunden", progress=0)

    if job.is_failed:
        err = str(job.exc_info) if job.exc_info else "Unbekannter Fehler"
        return render_template("job_card.html", job_id=job_id, status="error", message=err, progress=0)

    if job.is_started or job.is_queued:
        return render_template("job_card.html", job_id=job_id, status="processing", progress=progress, message=message)

    return render_template("job_card.html", job_id=job_id, status="error", message="Unbekannter Status", progress=0)


@bp.route("/download/<job_id>")
def download(job_id):
    output_dir = Path(current_app.config["OUTPUT_FOLDER"]) / job_id
    zip_path = output_dir / "output.zip"
    if not zip_path.exists():
        return "Datei nicht gefunden", 404
    return send_file(
        str(zip_path),
        as_attachment=True,
        download_name=f"Nebenkosten_Chunks_{job_id}.zip",
        mimetype="application/zip",
    )
