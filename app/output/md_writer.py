from pathlib import Path
from app.models import Chunk


def write_markdown(chunks: list[Chunk], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []

    lines.append(f"# Dokument: {chunks[0].source_file if chunks else 'Unbekannt'}")
    lines.append("")

    for chunk in chunks:
        heading_prefix = "#" * min(chunk.level + 1, 6)
        lines.append(f"{heading_prefix} {chunk.title}")
        lines.append("")
        lines.append(f"> **Seiten:** {chunk.pages[0]}–{chunk.pages[-1]} | **Konfidenz:** {chunk.confidence * 100:.0f}%")
        lines.append("")

        for table in chunk.tables:
            lines.append(f"### Tabelle{' — ' + table.caption if table.caption else ''}")
            if table.headers:
                lines.append("")
                lines.append("| " + " | ".join(table.headers) + " |")
                lines.append("|" + "|".join(["-" * max(len(h), 3) for h in table.headers]) + "|")
                for row in table.rows:
                    cells = [str(row.get(h, "")) for h in table.headers]
                    lines.append("| " + " | ".join(cells) + " |")
            lines.append("")

        if chunk.content_text.strip():
            lines.append(chunk.content_text.strip())
            lines.append("")

        for ann in chunk.annotations:
            lines.append(f"> ⚠️ **{ann.type}** — {ann.location}")
            lines.append(f"> Text: _{ann.text}_  ")
            lines.append(f"> Konfidenz: {ann.confidence * 100:.0f}% — {ann.note}")
            lines.append("")

        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
