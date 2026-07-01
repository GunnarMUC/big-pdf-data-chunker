from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


def check_redis(redis_url: str) -> dict:
    try:
        from redis import Redis
        r = Redis.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
        r.ping()
        info = r.info("server")
        return {
            "status": "ok",
            "version": info.get("redis_version", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_ollama(host: str, model: str) -> dict:
    try:
        import ollama
        client = ollama.Client(host=host, timeout=5)
        tags = client.list()
        models = [m["name"] for m in tags.get("models", [])]
        model_norm = model.split(":")[0].lower()
        found = any(model_norm in m.lower() for m in models)

        if found:
            return {"status": "ok", "model": model, "available": True, "models_count": len(models)}
        else:
            preview = ", ".join(models[:8])
            return {
                "status": "warning", "model": model, "available": False,
                "models_count": len(models),
                "error": f"Modell '{model}' nicht gefunden. Verfügbar: {preview}"
            }
    except Exception as e:
        return {"status": "warning", "error": f"Ollama nicht erreichbar: {e}. LLM-Fallback deaktiviert."}


def check_tesseract() -> dict:
    try:
        result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, timeout=5)
        version_line = result.stdout.strip().split("\n")[0] if result.stdout else "unknown"
        lang_result = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=5)
        langs = [l.strip() for l in lang_result.stdout.strip().split("\n")[1:] if l.strip()]
        deu_present = "deu" in langs
        return {
            "status": "ok" if deu_present else "warning",
            "version": version_line,
            "languages": langs,
            "german": deu_present,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_ocrmypdf() -> dict:
    try:
        result = subprocess.run(["ocrmypdf", "--version"], capture_output=True, text=True, timeout=5)
        return {"status": "ok", "version": result.stdout.strip()}
    except FileNotFoundError:
        return {"status": "warning", "error": "ocrmypdf nicht gefunden. OCR deaktiviert."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_disk(folders: list[str]) -> dict:
    ok = True
    items = {}
    for folder in folders:
        path = Path(folder)
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            usage = shutil.disk_usage(path)
            free_gb = round(usage.free / (1024 ** 3), 1)
            items[os.path.basename(folder) or folder] = {
                "status": "ok",
                "free_gb": free_gb,
                "writable": True,
            }
        except Exception as e:
            ok = False
            items[os.path.basename(folder) or folder] = {
                "status": "error",
                "error": str(e),
            }
    return {"status": "ok" if ok else "error", "folders": items}


def check_python_packages() -> dict:
    required = {
        "flask": "Flask", "fitz": "PyMuPDF", "pdfplumber": "pdfplumber",
        "docx": "python-docx", "openpyxl": "openpyxl",
        "PIL": "Pillow", "pytesseract": "pytesseract",
        "redis": "redis", "rq": "rq", "ollama": "ollama",
    }
    ok = True
    items = {}
    for module, package in required.items():
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "installed")
            items[package] = {"status": "ok", "version": str(version)}
        except ImportError:
            ok = False
            items[package] = {"status": "error", "error": "Nicht installiert"}
    return {"status": "ok" if ok else "error", "packages": items}


def run_all_checks(
    redis_url: str = "redis://redis:6379",
    ollama_host: str = "http://host.docker.internal:11434",
    ollama_model: str = "qwen2.5:14b",
    data_folders: Optional[list[str]] = None,
) -> dict:
    if data_folders is None:
        data_folders = ["data/uploads", "data/output", "data/ocr_cache"]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "redis": check_redis(redis_url),
            "ollama": check_ollama(ollama_host, ollama_model),
            "tesseract": check_tesseract(),
            "ocrmypdf": check_ocrmypdf(),
            "disk": check_disk(data_folders),
            "python_packages": check_python_packages(),
        },
        "overall_status": "ok",
    }


def cli_report(checks: dict) -> str:
    lines = []
    lines.append("=" * 50)
    lines.append("  System-Check: Big PDF Data Chunker")
    lines.append("=" * 50)

    for name, check in checks["checks"].items():
        status = check.get("status", "unknown")
        icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}.get(status, "❓")
        lines.append(f"\n{icon} {name.upper()}")

        for key, val in check.items():
            if key == "status":
                continue
            if isinstance(val, dict):
                for k, v in val.items():
                    if isinstance(v, dict):
                        s = v.get("status", "")
                        si = {"ok": "  ✅", "warning": "  ⚠️", "error": "  ❌"}.get(s, "  →")
                        detail = v.get("error") or v.get("version") or v.get("free_gb") or ""
                        if isinstance(detail, (int, float)) and "free_gb" in v:
                            detail = f"{detail} GB frei"
                        elif isinstance(detail, bool):
                            detail = "beschreibbar" if detail else "nicht beschreibbar"
                        lines.append(f"  {si} {k}: {detail}")
                    else:
                        lines.append(f"     {k}: {v}")
            elif isinstance(val, list):
                lines.append(f"  → {key}: {', '.join(str(x) for x in val)}")
            else:
                lines.append(f"  → {key}: {val}")

    lines.append(f"\n{'=' * 50}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(cli_report(run_all_checks()))
