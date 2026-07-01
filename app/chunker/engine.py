from __future__ import annotations
import logging
from pathlib import Path
from app.models import RawDocument, Chunk, Section
from app.parsers import parse_file
from app.chunker.heuristic import detect_sections
from app.chunker.llm_fallback import refine_sections

logger = logging.getLogger(__name__)

LLM_FALLBACK_THRESHOLD = 0.6


def process_document(file_path: Path, job_id: str, job=None) -> tuple[list[Chunk], RawDocument]:
    if job:
        job.meta["progress"] = 0.05
        job.meta["message"] = "Dokument wird eingelesen…"
        job.save_meta()

    raw_doc = parse_file(file_path)

    if job:
        job.meta["progress"] = 0.15
        job.meta["message"] = "Heuristische Analyse läuft…"
        job.save_meta()

    sections, confidence = detect_sections(raw_doc)

    if confidence < LLM_FALLBACK_THRESHOLD:
        if job:
            job.meta["progress"] = 0.25
            job.meta["message"] = "LLM-unterstützte Strukturanalyse…"
            job.save_meta()
        sections = refine_sections(raw_doc, sections)

    if job:
        job.meta["progress"] = 0.40
        job.meta["message"] = "Chunks werden erstellt…"
        job.save_meta()

    chunks = _build_chunks(raw_doc, sections, job_id, file_path.name)

    if job:
        job.meta["progress"] = 0.55
        job.meta["message"] = f"{len(chunks)} Chunks erstellt"
        job.save_meta()

    return chunks, raw_doc


def _build_chunks(doc: RawDocument, sections: list[Section], job_id: str, source_name: str) -> list[Chunk]:
    chunks = []
    for idx, section in enumerate(sections):
        start = max(0, section.start_page - 1)
        end = min(len(doc.pages), section.end_page)

        if start >= end:
            continue

        pages_in_section = doc.pages[start:end]
        page_numbers = list(range(start + 1, end + 1))

        all_text = "\n\n".join(
            [f"--- Seite {p.number} ---\n{p.text}" for p in pages_in_section]
        )
        all_tables = []
        all_annotations = []
        for p in pages_in_section:
            all_tables.extend(p.tables)
            all_annotations.extend(p.annotations)

        chunk_id = f"{job_id}_{idx:03d}"

        chunks.append(Chunk(
            chunk_id=chunk_id,
            doc_id=job_id,
            title=section.title,
            level=section.level,
            pages=page_numbers,
            content_text=all_text,
            tables=all_tables,
            annotations=all_annotations,
            confidence=section.confidence,
            source_file=source_name,
        ))

    return chunks
