
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)n
[![CI](https://github.com/GunnarMUC/big-pdf-data-chunker/actions/workflows/ci.yml/badge.svg)](https://github.com/GunnarMUC/big-pdf-data-chunker/actions)

# Big PDF Data Chunker

**Pre-process multi-format business documents into clean, structured chunks optimized for local LLM consumption.**

> Cloud LLMs have 200K token context windows. Your local LLM has 8K.  
> Cloud LLMs can ingest raw PDFs. Your local LLM needs structured data.  
> **This tool bridges that gap.**

---

## The Problem

Local LLMs (Llama, Qwen, Mistral, DeepSeek) running on consumer hardware fundamentally differ from cloud APIs:

| | Cloud LLM (GPT-4, Claude) | Local LLM (Qwen, Llama) |
|---|---|---|
| **Context window** | 128K – 2M tokens | 4K – 32K tokens |
| **Document ingestion** | Native PDF/image parsing | Text-only input |
| **Data privacy** | Data leaves your machine | 100% local |
| **Cost** | Per-token pricing | Free (your hardware) |

A 200-page utility bill, contract, or financial report cannot be fed to a local model directly. Even if chunked naively (every 8 pages), the LLM loses cross-section context, table relationships, and metadata.

## What This Tool Does

**Big PDF Data Chunker** ingests multi-format business documents and produces **intelligently structured, machine-readable datasets** that a local LLM (or any downstream AI pipeline) can actually work with.

### Input
- **PDF** (searchable + scanned via OCR)
- **DOCX** (Word documents with heading hierarchy)
- **XLSX** (Excel workbooks, one sheet = one chunk)
- **Images** (PNG, JPG, TIFF — OCR with handwriting detection)

All files up to 200+ pages, no size limit. Multi-file upload supported.

### Processing
1. **Format detection** → Appropriate parser
2. **OCR** (if needed) for scanned PDFs and images
3. **Text + table extraction** with structure preservation
4. **Intelligent section detection** via heuristics (19 markers for German utility bills, extensible)
5. **LLM fallback** (optional, local Ollama) for ambiguous documents
6. **Handwriting detection** with confidence markers and review notes

### Output
- **`document.jsonl`** — One JSON object per logical section, stream-readable by any LLM ingestion pipeline (RAG, embeddings, fine-tuning)
- **`document.md`** — Human-readable Markdown for manual review
- **`output.zip`** — Both packaged for download

Each chunk carries metadata: source file, page range, section title, tables (structured as arrays), handwriting annotations with confidence scores, and overall section confidence.

## Why This Matters

### For local LLM applications

Modern local LLM workflows (RAG, summarization, Q&A over documents) rely on **clean, pre-chunked data**. The quality of your chunks directly determines the quality of your LLM responses. Naive page-based splitting:

- Breaks tables across pages
- Loses section context
- Mixes unrelated content
- Misses handwritten notes and annotations

Intelligent, content-aware chunking solves all of these.

### For privacy-sensitive industries

Companies handling **financial documents**, **legal contracts**, **medical records**, or **tax filings** cannot upload them to cloud AI services (GDPR, attorney-client privilege, trade secrets). This tool runs **entirely locally** — all data stays on your machine, processed by your local LLM.

### Real-world use case: German Utility Bill Auditing (Betriebskosten)

The tool was originally built for auditing German "Nebenkostenabrechnungen" (utility/service charge statements). A single bill can span 200+ pages with:

- Cost overviews and distribution keys
- Heating, water, electricity breakdowns
- Insurance, property tax, maintenance costs
- Handwritten corrections and notes from landlords

The chunker identifies all 17+ standard sections (Heizung, Warmwasser, Grundsteuer, Versicherungen, Aufzug, etc.), extracts tables with their headers, flags handwritten annotations, and outputs structured JSONL ready for a local LLM to perform legal compliance checks against German tenancy law (BetrKV, BGB, HeizkostenV).

## Quick Start

### Prerequisites

- **Docker Desktop**
- **Ollama** (optional, only for LLM fallback on ambiguous documents)

### 1. Pull the LLM model (optional)

```bash
ollama pull qwen2.5:14b
ollama serve
```

### 2. Start the app

```bash
git clone https://github.com/GunnarMUC/big-pdf-data-chunker
cd big-pdf-data-chunker
docker compose up --build
```

### 3. Open the UI

→ **http://localhost:5000**

Drag & drop your documents. The app processes them asynchronously with live progress. Download the structured JSONL + Markdown as a ZIP.

## Output Format

### JSONL (machine-readable)

```jsonl
{"chunk_id":"abc123_003","doc_id":"abc123","title":"Heizkostenabrechnung 2024","level":1,"pages":[4,7],"source_file":"abrechnung.pdf","content":"Die Heizkosten verteilen sich wie folgt...","tables":[{"headers":["Einheit","Verbrauch","Kosten"],"rows":[{"Einheit":"Haus A","Verbrauch":"12500","Kosten":"1250.00"}],"caption":"Heizkostenverteilung","page":5}],"annotations":[{"type":"handwriting","location":"Absatz 3, Standort B","text":"falscher Zähler","confidence":0.42,"note":"Bitte per Durchsicht prüfen"}],"confidence":0.93}
```

### Markdown (human-readable)

```markdown
## Heizkostenabrechnung 2024

> **Seiten:** 4–7 | **Konfidenz:** 93%

### Tabelle — Heizkostenverteilung

| Einheit | Verbrauch | Kosten |
|---------|-----------|--------|
| Haus A  | 12.500    | 1.250,00 € |

> ⚠️ **handwriting** — Absatz 3, Standort B  
> Text: _falscher Zähler_  
> Konfidenz: 42% — Bitte per Durchsicht prüfen
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Docker Container                                        │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐     │
│  │ Flask UI  │  │  Redis   │  │  RQ Worker       │     │
│  │ Port 5000 │  │ (Queue)  │  │  (Background)    │     │
│  └──────────┘  └──────────┘  └──────┬───────────┘     │
│                                     │                   │
│              ┌──────────────────────┼───────────┐      │
│              │  Parsers             │  Chunking  │      │
│              │  PDF│DOCX│XLSX│IMG  │  Heuristic │      │
│              │  + OCR + Handschrift │  + LLM     │      │
│              └──────────────────────┴───────────┘      │
│                                     │                   │
│                                     ▼                   │
│                          JSONL + MD + ZIP               │
└─────────────────────────────────────────────────────────┘
                              │
        host.docker.internal:11434
                              │
┌─────────────────────────────┼───────────────────────────┐
│  Your Mac                   │                           │
│  ┌──────────────────────────┴──────────────────┐       │
│  │  Ollama (Qwen 2.5 14B / optional)           │       │
│  └─────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Flask 3 + HTMX + Gunicorn |
| Queue | Redis + RQ |
| PDF parsing | PyMuPDF + pdfplumber |
| OCR | Tesseract 5 (German + Fraktur) + ocrmypdf |
| DOCX parsing | python-docx |
| XLSX parsing | openpyxl |
| Image OCR | Pillow + pytesseract |
| LLM (optional) | Ollama (Qwen 2.5 14B, Llama 3.1, Mistral) |
| Container | Docker + Docker Compose |

## Diagnostics

The app includes a built-in system health check that validates all dependencies at startup or on demand:

```bash
# CLI check (from the container or host)
python -m app.check

# Web dashboard (visual, real-time)
open http://localhost:5000/health

# JSON API (for scripts / monitoring)
curl http://localhost:5000/health?format=json
```

**Checks performed:** Redis (queue), Ollama (LLM fallback), Tesseract + German language pack, ocrmypdf, disk space and write permissions, all Python package dependencies. Each check has a 3-5 second timeout — nothing blocks startup.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama server address |
| `OLLAMA_MODEL` | `qwen2.5:14b` | LLM model for section detection fallback |
| `RQ_TIMEOUT` | `480` | Max processing time per job (seconds) |
| `SECRET_KEY` | auto-generated | Flask session key |

## License

Private project. Local, non-commercial use.

---

**Built for the era of local AI.** Cloud LLMs are powerful but not always available, affordable, or permissible. This tool makes local LLMs practical for real-world business documents.
