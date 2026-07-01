from __future__ import annotations
import mimetypes
from pathlib import Path
from app.parsers.base import BaseParser
from app.parsers.pdf_parser import PDFParser
from app.parsers.image_parser import ImageParser
from app.parsers.docx_parser import DocxParser
from app.parsers.xlsx_parser import XlsxParser
from app.models import RawDocument


PARSERS: list[BaseParser] = [
    PDFParser(),
    ImageParser(),
    DocxParser(),
    XlsxParser(),
]

EXTENSION_MAP: dict[str, BaseParser] = {}
for parser in PARSERS:
    for ext in parser.extensions:
        EXTENSION_MAP[ext.lower()] = parser


def guess_format(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext in EXTENSION_MAP:
        return ext
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        if "pdf" in mime:
            return ".pdf"
        if "image" in mime:
            return ".png"
        if "word" in mime or "docx" in mime:
            return ".docx"
        if "spreadsheet" in mime or "xlsx" in mime or "excel" in mime:
            return ".xlsx"
    return ext


def get_parser(file_path: Path) -> BaseParser | None:
    ext = guess_format(file_path)
    return EXTENSION_MAP.get(ext)


def parse_file(file_path: Path) -> RawDocument:
    parser = get_parser(file_path)
    if parser is None:
        raise ValueError(f"Kein Parser für Format: {file_path.suffix}")
    return parser.parse(file_path)
