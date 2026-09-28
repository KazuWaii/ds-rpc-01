"""One-off indexing job: chunk every file in resources/data and embed it into Chroma.

Run whenever the source documents change:
    uv run python scripts/build_index.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ingest import DATA_DIR, load_all_chunks
from app.services.vectorstore import index_chunks


def main():
    chunks = load_all_chunks(DATA_DIR)
    print(f"Loaded {len(chunks)} chunks from resources/data/")

    by_department = {}
    for c in chunks:
        by_department[c.metadata["department"]] = by_department.get(c.metadata["department"], 0) + 1
    for department, count in sorted(by_department.items()):
        print(f"  {department}: {count} chunks")

    index_chunks(chunks)
    print("Indexed into resources/vectorstore/")


if __name__ == "__main__":
    main()
