import logging
from pathlib import Path
from PIL import Image
import pytesseract
from app.parsers.base import BaseParser
from app.models import RawDocument, Page, Annotation

logger = logging.getLogger(__name__)

HANDWRITING_CONFIDENCE_THRESHOLD = 0.60
PAGE_TEXT_THRESHOLD = 15


class ImageParser(BaseParser):
    extensions = [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"]

    def parse(self, file_path: Path) -> RawDocument:
        img = Image.open(file_path)

        data = pytesseract.image_to_data(
            img,
            lang="deu",
            output_type=pytesseract.Output.DICT,
        )

        text = pytesseract.image_to_string(img, lang="deu").strip()

        annotations = self._detect_handwriting(data)

        return RawDocument(
            pages=[
                Page(
                    number=1,
                    text=text,
                    tables=[],
                    annotations=annotations,
                    ocr_confidence=self._mean_confidence(data),
                )
            ],
            metadata={
                "source_file": file_path.name,
                "format": file_path.suffix.lower().lstrip("."),
                "page_count": 1,
                "ocr_used": True,
                "width": img.width,
                "height": img.height,
            },
        )

    def _detect_handwriting(self, data: dict) -> list[Annotation]:
        annotations = []
        current_paragraph = -1
        paragraph_text: list[str] = []
        paragraph_confs: list[float] = []
        paragraph_numbers: list[int] = []

        for i in range(len(data["text"])):
            conf = data["conf"][i]
            word = data["text"][i].strip()
            par_num = data["par_num"][i]
            block_num = data["block_num"][i]
            line_num = data["line_num"][i]

            if not word or conf < 0:
                continue

            if par_num != current_paragraph and paragraph_text:
                self._flush_paragraph(
                    annotations, paragraph_text, paragraph_confs,
                    paragraph_numbers, block_num, line_num
                )
                paragraph_text.clear()
                paragraph_confs.clear()
                paragraph_numbers.clear()

            current_paragraph = max(current_paragraph, par_num)
            paragraph_text.append(word)
            paragraph_confs.append(conf)
            paragraph_numbers.append(par_num)

        if paragraph_text:
            self._flush_paragraph(
                annotations, paragraph_text, paragraph_confs,
                paragraph_numbers, 0, 0
            )

        return annotations

    def _flush_paragraph(
        self, annotations: list, words: list[str], confs: list[float],
        par_numbers: list[int], block_num: int, line_num: int
    ) -> None:
        if not words:
            return
        mean_conf = sum(confs) / len(confs) / 100.0
        full_text = " ".join(words)

        if mean_conf < HANDWRITING_CONFIDENCE_THRESHOLD:
            if len(full_text.split()) >= 3:
                annotations.append(
                    Annotation(
                        type="handwriting",
                        location=f"Block {block_num}, Zeile {line_num}",
                        text=full_text,
                        confidence=round(mean_conf, 2),
                        note="Bitte per Durchsicht prüfen",
                    )
                )

    @staticmethod
    def _mean_confidence(data: dict) -> float:
        confs = [c for c in data["conf"] if c > 0]
        if not confs:
            return 0.0
        return round(sum(confs) / len(confs) / 100.0, 2)
