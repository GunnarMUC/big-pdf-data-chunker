import os
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Annotation:
    type: str
    location: str
    text: str
    confidence: float
    note: str = "Bitte per Durchsicht prüfen"


@dataclass
class Table:
    headers: list[str]
    rows: list[dict]
    caption: str = ""
    page: int = 0


@dataclass
class Page:
    number: int
    text: str = ""
    tables: list[Table] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    ocr_confidence: float = 1.0


@dataclass
class RawDocument:
    pages: list[Page]
    metadata: dict = field(default_factory=dict)


@dataclass
class Section:
    title: str
    level: int = 1
    start_page: int = 1
    end_page: int = 1
    confidence: float = 1.0


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    level: int
    pages: list[int]
    content_text: str
    tables: list[Table] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    confidence: float = 1.0
    source_file: str = ""


def generate_job_id() -> str:
    return uuid.uuid4().hex[:12]
