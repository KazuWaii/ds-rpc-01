from pathlib import Path
from dataclasses import dataclass
import pandas as pd
import re # (expressions régulières)


DATA_DIR = Path(__file__).resolve().parents[2] / "resources" / "data"
# Regex to cut md files into sections based on headers
_HEADER_RE = re.compile(r"^(#{1,2})\s+(.+)$", re.MULTILINE)
# Chunk size and overlap for splitting text into smaller pieces
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150

class Chunk:
    def __init__(self, id, text, metadata):
        self.id = id
        self.text = text
        self.metadata = metadata

def load_all_chunks(data_dir):
        all_chunks = []
        for department_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
            department = department_dir.name
            for file_path in sorted(department_dir.iterdir()):
                if file_path.suffix == ".md":
                    all_chunks.extend(_load_markdown_file(file_path, department))
                elif file_path.suffix == ".csv":
                    all_chunks.extend(_load_csv_file(file_path, department))
        
        return all_chunks

def _load_csv_file(file_path, department):
    chunks = []
    df = pd.read_csv(file_path)
    
    for row_idx, row in df.iterrows():
        sentence = "; ".join(f"{col}: {row[col]}" for col in df.columns)
        chunk = Chunk(id=f"{department}_{file_path.stem}_{row_idx}", 
                      text=sentence, 
                      metadata={"department": department,
                                "source": file_path.relative_to(DATA_DIR).as_posix(),
                                "section": f"row_{row_idx}"})
        chunks.append(chunk)

    return chunks


def _split_by_headers(text):
    matches = list(_HEADER_RE.finditer(text))

    # cas ou le texte ne contient pas de headers
    if not matches:
        return [("", text)]

    sections = []
    for i, m in enumerate(matches):
        # debut du texte de la section
        start = m.start()
        # fin du texte de la section
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        header = m.group(2).strip()
        sections.append((header, text[start:end].strip()))
    return sections


def _nearest_whitespace(text, index, search_window=50):
    window_start = max(0, index - search_window)
    space_pos = text.rfind(" ", window_start, index)
    return space_pos + 1 if space_pos != -1 else index

def _split_by_size(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    if len(text) <= chunk_size:
        return [text]
    else:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                end = _nearest_whitespace(text, end)
            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = end - overlap
        return chunks

def _load_markdown_file(file_path, department):
    text = file_path.read_text(encoding="utf-8")
    chunks = []

    for header, section_text in _split_by_headers(text):
        for i, piece in enumerate(_split_by_size(section_text)):
            chunk = Chunk(
                id=f"{department}_{file_path.stem}_{header}_part{i}",
                text=piece,
                metadata={
                    "source": file_path.relative_to(DATA_DIR).as_posix(),
                    "department": department,
                    "section": header or file_path.stem,
                    "part": i,
                },
            )
            chunks.append(chunk)

    return chunks