import fitz
import pdfplumber
import subprocess
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.parsers.base import BaseParser
from app.models import RawDocument, Page, Table, Annotation

OCR_CACHE_DIR = Path("data/ocr_cache")


class PDFParser(BaseParser):
    extensions = [".pdf"]

    def parse(self, file_path: Path) -> RawDocument:
        working_pdf = self._ensure_ocr(file_path)
        doc = fitz.open(working_pdf)
        total_pages = len(doc)

        pages = []
        for page_num in range(total_pages):
            page_data = self._extract_page(doc, page_num)
            pages.append(page_data)

        doc.close()

        return RawDocument(
            pages=pages,
            metadata={
                "source_file": file_path.name,
                "format": "pdf",
                "page_count": total_pages,
                "ocr_used": working_pdf != file_path,
            },
        )

    def _ensure_ocr(self, file_path: Path) -> Path:
        doc = fitz.open(file_path)
        text = ""
        for i in range(min(3, len(doc))):
            text += doc[i].get_text()
        doc.close()

        if len(text.strip()) > 50:
            return file_path

        ocr_pdf = file_path.with_stem(file_path.stem + "_ocr")
        if ocr_pdf.exists():
            return ocr_pdf

        try:
            subprocess.run(
                [
                    "ocrmypdf",
                    "--deskew",
                    "--clean",
                    "--force-ocr",
                    "--pdf-renderer", "hocr",
                    str(file_path),
                    str(ocr_pdf),
                ],
                check=True,
                timeout=600,
            )
            return ocr_pdf
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return file_path

    def _extract_page(self, doc: fitz.Document, page_num: int) -> Page:
        page = doc[page_num]
        text = page.get_text("text")
        text = self._clean_text(text)

        tables = self._extract_tables(doc, page_num)

        annotations = self._detect_annotations(page, text)

        ocr_confidence = 0.85 if len(text.split()) < 20 else 0.98

        return Page(
            number=page_num + 1,
            text=text,
            tables=tables,
            annotations=annotations,
            ocr_confidence=ocr_confidence,
        )

    def _extract_tables(self, doc: fitz.Document, page_num: int) -> list[Table]:
        tables = []
        try:
            with pdfplumber.open(doc.name) as pdf:
                if page_num >= len(pdf.pages):
                    return tables
                plumber_page = pdf.pages[page_num]
                extracted = plumber_page.extract_tables()
                for table_data in extracted:
                    if not table_data or len(table_data) < 2:
                        continue
                    headers = [
                        str(cell).strip() if cell is not None else ""
                        for cell in table_data[0]
                    ]
                    rows = []
                    for row in table_data[1:]:
                        row_dict = {}
                        for j, cell in enumerate(row):
                            key = headers[j] if j < len(headers) else f"col_{j}"
                            row_dict[key] = str(cell).strip() if cell is not None else ""
                        rows.append(row_dict)
                    tables.append(
                        Table(
                            headers=headers,
                            rows=rows,
                            caption="",
                            page=page_num + 1,
                        )
                    )
        except Exception:
            pass
        return tables

    def _detect_annotations(self, page: fitz.Page, text: str) -> list[Annotation]:
        annotations = []
        for annot in page.annots():
            try:
                annot_type = annot.info.get("subtype", "")
                if annot_type in ("Text", "FreeText", "Ink"):
                    rect = annot.rect
                    location = f"Seite {page.number + 1}"
                    annot_text = annot.info.get("content", "")
                    annotations.append(
                        Annotation(
                            type="digital_note",
                            location=location,
                            text=annot_text,
                            confidence=1.0,
                            note="",
                        )
                    )
            except Exception:
                pass
        return annotations

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)
        return text.strip()
