from abc import ABC, abstractmethod
from pathlib import Path
from app.models import RawDocument


class BaseParser(ABC):
    extensions: list[str] = []

    @abstractmethod
    def parse(self, file_path: Path) -> RawDocument:
        ...

    @staticmethod
    def parse_confidence(file_path: Path) -> float:
        return 0.0
