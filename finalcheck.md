# Final Check — Big PDF Data Chunker

**Repo:** https://github.com/GunnarMUC/big-pdf-data-chunker  
**28 Dateien, 3 Commits, Docker-Build verifiziert**

## Komponenten-Status

| Komponente | Status |
|-----------|--------|
| 4 Format-Parser (PDF/DOCX/XLSX/Bild) | ✅ |
| 19 Heuristik-Marker für dt. Nebenkosten | ✅ getestet (0,89 Confidence) |
| LLM-Fallback (Ollama/Qwen 2.5 14B) | ✅ |
| JSONL + Markdown Output | ✅ |
| Handschrift-Erkennung + Prüfhinweise | ✅ |
| Web UI (HTMX Drag & Drop) | ✅ |
| Async Queue (Redis/RQ, 8 Min Timeout) | ✅ |
| Docker-Compose (web + worker + redis) | ✅ |
| System-Health-Check (CLI + Web + JSON) | ✅ |

## Starten

```bash
ollama serve
docker compose up --build
# → http://localhost:5000
```

## Systemvoraussetzungen (MacBook)

| Software | Version | Status |
|----------|---------|--------|
| Docker Desktop | 29.5.3 | ✅ |
| Docker Compose | v5.1.4 | ✅ |
| Ollama | 0.30.10 | ✅ |
| Tesseract | 5.5.2 | ✅ (deu im Container) |
| ocrmypdf | 17.6.0 | ✅ |
| Disk frei | 654 GB | ✅ |

## Datenfluss

```
Upload → Parser → RawDocument → heuristic.py → (LLM-Fallback) → JSONL + MD → ZIP
```

## Output pro Dokument

- `.jsonl` — JSON Lines (maschinenlesbar, für downstream KI)
- `.md` — Markdown (menschlich lesbar, Kontrollansicht)
- `.zip` — beides gepackt als Download
