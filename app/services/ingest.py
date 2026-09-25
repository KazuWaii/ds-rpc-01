from pathlib import Path
from dataclasses import dataclass

DATA_DIR = Path(__file__).resolve().parents[2] / "resources" / "data"

@dataclass
class Chunk:
    def __init__(self, id, text, metadata):
        self.id = id
        self.text = text
        self.metadata = metadata

    def load_all_chunks(self, data_dir):
        None