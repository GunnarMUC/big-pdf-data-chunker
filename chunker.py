#!/usr/bin/env python3
"""
Nebenkosten-PDF Smart Chunker mit OCR-Unterstützung
"""

import fitz
import pdfplumber
import json
import re
import subprocess
from pathlib import Path
from tqdm import tqdm
import ollama
import sys

# ==================== KONFIGURATION ====================
OLLAMA_MODEL = "qwen2.5:14b"
MAX_PAGES_PER_CHUNK = 12
OUTPUT_DIR = "hierarchical_chunks"
RUN_OCR = True                    # Auf True lassen, wenn du viele gescannt PDFs hast

def is_pdf_searchable(pdf_path: Path) -> bool:
    """Prüft, ob das PDF bereits durchsuchbaren Text enthält"""
    try:
        doc = fitz.open(pdf_path)
        text = doc[0].get_text().strip()
        doc.close()
        return len(text) > 50
    except:
        return False

def run_ocr(input_pdf: Path) -> Path:
    """Führt OCR aus und gibt Pfad zur OCR-Version zurück"""
    ocr_pdf = input_pdf.with_name(input_pdf.stem + "_ocr" + input_pdf.suffix)
    
    if ocr_pdf.exists():
        print(f"✅ OCR-Version bereits vorhanden: {ocr_pdf.name}")
        return ocr_pdf
    
    print("🔄 Führe OCR durch (kann 30–90 Sekunden dauern)...")
    try:
        subprocess.run([
            "ocrmypdf",
            "--deskew", "--clean", "--force-ocr",
            "--pdf-renderer", "hocr",
            str(input_pdf),
            str(ocr_pdf)
        ], check=True)
        print(f"✅ OCR abgeschlossen: {ocr_pdf.name}")
        return ocr_pdf
    except subprocess.CalledProcessError:
        print("⚠️ OCR fehlgeschlagen – arbeite mit Original weiter")
        return input_pdf
    except FileNotFoundError:
        print("⚠️ ocrmypdf nicht gefunden. Installiere mit: brew install ocrmypdf")
        return input_pdf

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

def extract_page_content(doc: fitz.Document, page_num: int) -> str:
    page = doc[page_num]
    text = page.get_text("text")
    
    table_text = ""
    try:
        with pdfplumber.open(doc.name) as pdf:
            plumber_page = pdf.pages[page_num]
            tables = plumber_page.extract_tables()
            for table in tables:
                if table:
                    row_str = [" | ".join(str(cell) if cell is not None else "" for cell in row) for row in table]
                    table_text += "\n\n" + "\n".join(row_str)
    except:
        pass
    return clean_text(text + table_text)

def llm_detect_sections(page_contents: list) -> list:
    preview = "\n\n".join([f"Seite {i+1}:\n{content[:950]}" for i, content in enumerate(page_contents[:30])])
    
    prompt = f"""Du bist Experte für deutsche Nebenkosten- und Betriebskostenabrechnungen.

Analysiere den Text und erstelle eine klare Abschnittsstruktur.
Gib NUR gültiges JSON zurück:

{{
  "sections": [
    {{"title": "Kurzer Titel", "level": 1, "start_page": 1, "end_page": 7, "description": "Kurze Beschreibung"}}
  ]
}}

Typische Abschnitte: Deckblatt, Kostenübersicht, Verteilerschlüssel, Heizung/Lüften/Kühlen, Wasser/Abwasser, Grundsteuer, Versicherungen, Strom, Objektbetreuung, Aufzug etc.

Text:
{preview}
"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            options={"temperature": 0.1, "num_ctx": 16000}
        )
        content = response['message']['content']
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))["sections"]
    except Exception as e:
        print(f"LLM-Fehler: {e}")
    return []

def create_hierarchical_chunks(input_pdf_path: str):
    input_path = Path(input_pdf_path)
    if not input_path.exists():
        print(f"❌ Datei nicht gefunden: {input_path}")
        return

    working_pdf = input_path
    
    # OCR Schritt
    if RUN_OCR and not is_pdf_searchable(input_path):
        working_pdf = run_ocr(input_path)
    
    print(f"📄 Verarbeite: {working_pdf.name} ({len(fitz.open(working_pdf))} Seiten)")
    
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    doc = fitz.open(working_pdf)
    total_pages = len(doc)
    
    print("🔍 Extrahiere Inhalt...")
    page_contents = [extract_page_content(doc, p) for p in tqdm(range(total_pages))]
    
    print("🧠 LLM analysiert Struktur...")
    sections = llm_detect_sections(page_contents)
    
    if not sections:
        print("⚠️ Fallback: Gleichmäßige Chunks")
        sections = [{"title": f"Abschnitt {i+1}", "level": 1, 
                    "start_page": i*8+1, "end_page": min((i+1)*8, total_pages)} 
                   for i in range((total_pages + 7) // 8)]
    
    print(f"💾 Erstelle {len(sections)} Chunks...")
    for i, sec in enumerate(sections):
        start = max(0, sec.get("start_page", 1) - 1)
        end = min(total_pages, sec.get("end_page", start + MAX_PAGES_PER_CHUNK))
        
        full_content = "\n\n".join([f"--- Seite {p+1} ---\n{page_contents[p]}" for p in range(start, end)])
        
        metadata = {
            "chunk_id": i,
            "title": sec.get("title", f"Abschnitt {i}"),
            "level": sec.get("level", 1),
            "pages": list(range(start+1, end+1)),
            "page_count": end - start,
            "description": sec.get("description", ""),
            "source_pdf": input_path.name,
            "used_ocr": working_pdf != input_path
        }
        
        safe_title = re.sub(r'[^a-zA-Z0-9äöüÄÖÜß_-]', '_', metadata["title"])[:40]
        md_path = Path(OUTPUT_DIR) / f"chunk_{i:03d}_{safe_title}.md"
        json_path = Path(OUTPUT_DIR) / f"chunk_{i:03d}.json"
        
        md_content = f"""# {metadata['title']}
**Level:** {metadata['level']} | **Seiten:** {metadata['pages'][0]}-{metadata['pages'][-1]}

{full_content}
"""
        md_path.write_text(md_content, encoding="utf-8")
        json_path.write_text(json.dumps({**metadata, "content": full_content}, ensure_ascii=False, indent=2), encoding="utf-8")
        
        print(f"   ✓ {metadata['title']} ({metadata['page_count']} Seiten)")
    
    print(f"\n🎉 Fertig! Ergebnisse in Ordner: {Path(OUTPUT_DIR).absolute()}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = input("PDF-Pfad eingeben oder Datei hierher ziehen: ").strip().strip('"')
    
    create_hierarchical_chunks(pdf_path)