import json
import re
import os
from app.models import Section, RawDocument

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")
MAX_PREVIEW_CHARS = 900
MAX_PREVIEW_PAGES = 35


def refine_sections(doc: RawDocument, existing_sections: list[Section]) -> list[Section]:
    try:
        import ollama
    except ImportError:
        return existing_sections

    client = ollama.Client(host=OLLAMA_HOST)
    preview = _build_preview(doc)

    prompt = f"""Du bist Experte für deutsche Nebenkosten- und Betriebskostenabrechnungen.

Analysiere den Text und erstelle eine präzise Abschnittsstruktur.
Gib NUR gültiges JSON zurück, kein Markdown, keine Erklärung:

{{
  "sections": [
    {{"title": "Kurzer Titel", "level": 1, "start_page": 1, "end_page": 7, "confidence": 0.95}}
  ]
}}

Typische Abschnitte: Deckblatt, Kostenübersicht, Verteilerschlüssel, Heizung, Warmwasser, Kaltwasser, Abwasser, Grundsteuer, Versicherungen, Strom/Allgemeinstrom, Objektbetreuung/Hausmeister, Aufzug, Reinigung, Gartenpflege, Schornsteinfeger, Müll/Abfall, Winterdienst, Unterschriften.

Seiten: 1 bis {len(doc.pages)}.
Text:

{preview}
"""

    try:
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_ctx": 16000},
        )
        content = response["message"]["content"]
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if not json_match:
            return existing_sections

        data = json.loads(json_match.group(0))
        llm_sections = data.get("sections", [])
        if not llm_sections:
            return existing_sections

        result = []
        for sec in llm_sections:
            result.append(Section(
                title=sec.get("title", "Abschnitt"),
                level=sec.get("level", 1),
                start_page=max(1, sec.get("start_page", 1)),
                end_page=min(len(doc.pages), sec.get("end_page", len(doc.pages))),
                confidence=min(1.0, max(0.0, sec.get("confidence", 0.8))),
            ))
        return result

    except Exception:
        return existing_sections


def _build_preview(doc: RawDocument) -> str:
    preview_pages = doc.pages[:MAX_PREVIEW_PAGES]
    lines = []
    for page in preview_pages:
        lines.append(f"Seite {page.number}:\n{page.text[:MAX_PREVIEW_CHARS]}")
    return "\n\n".join(lines)
