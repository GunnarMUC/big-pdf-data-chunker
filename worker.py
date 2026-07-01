import os
import shutil
import zipfile
from pathlib import Path
from rq import get_current_job

from app.chunker.engine import process_document
from app.models import generate_job_id
from app.output.jsonl_writer import write_jsonl
from app.output.md_writer import write_markdown

UPLOAD_FOLDER = Path(os.environ.get("UPLOAD_FOLDER", "data/uploads"))
OUTPUT_FOLDER = Path(os.environ.get("OUTPUT_FOLDER", "data/output"))


def process_single_file(stored_path: str, job_id: str):
    job = get_current_job()

    file_path = Path(stored_path)
    output_dir = OUTPUT_FOLDER / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    if job:
        job.meta["progress"] = 0.0
        job.meta["message"] = "Starte Verarbeitung…"
        job.save_meta()

    chunks, raw_doc = process_document(file_path, job_id, job=job)

    base_name = file_path.stem
    jsonl_path = output_dir / f"{base_name}.jsonl"
    md_path = output_dir / f"{base_name}.md"

    if job:
        job.meta["progress"] = 0.60
        job.meta["message"] = "Schreibe JSONL…"
        job.save_meta()

    write_jsonl(chunks, jsonl_path)

    if job:
        job.meta["progress"] = 0.70
        job.meta["message"] = "Schreibe Markdown…"
        job.save_meta()

    write_markdown(chunks, md_path)

    if job:
        job.meta["progress"] = 0.85
        job.meta["message"] = "Erstelle ZIP…"
        job.save_meta()

    zip_path = output_dir / "output.zip"
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(str(jsonl_path), jsonl_path.name)
        zf.write(str(md_path), md_path.name)

    if job:
        job.meta["progress"] = 1.0
        job.meta["message"] = "Fertig!"
        job.save_meta()

    return str(zip_path)
