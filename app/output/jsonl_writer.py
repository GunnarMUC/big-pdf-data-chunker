import json
from pathlib import Path
from app.models import Chunk


def write_jsonl(chunks: list[Chunk], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            record = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "level": chunk.level,
                "pages": chunk.pages,
                "page_count": len(chunk.pages),
                "source_file": chunk.source_file,
                "content": chunk.content_text,
                "tables": [
                    {
                        "headers": t.headers,
                        "rows": t.rows,
                        "caption": t.caption,
                        "page": t.page,
                    }
                    for t in chunk.tables
                ],
                "annotations": [
                    {
                        "type": a.type,
                        "location": a.location,
                        "text": a.text,
                        "confidence": a.confidence,
                        "note": a.note,
                    }
                    for a in chunk.annotations
                ],
                "confidence": chunk.confidence,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return output_path
