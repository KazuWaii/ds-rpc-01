import pandas as pd

from app.services import ingest


def test_split_by_headers_splits_on_h1_and_h2():
    text = "# Title\nIntro text.\n## Section One\nContent one.\n## Section Two\nContent two."
    sections = ingest._split_by_headers(text)
    assert [header for header, _ in sections] == ["Title", "Section One", "Section Two"]


def test_split_by_headers_ignores_h3():
    text = "## Section\n### Subsection\nBody text."
    sections = ingest._split_by_headers(text)
    assert len(sections) == 1
    assert sections[0][0] == "Section"


def test_split_by_headers_no_headers_returns_whole_text():
    text = "Just a plain paragraph, no headers at all."
    assert ingest._split_by_headers(text) == [("", text)]


def test_nearest_whitespace_finds_space_in_window():
    text = "hello world this is a test"
    index = text.index("world") + 3  # lands mid-word, inside "world"
    result = ingest._nearest_whitespace(text, index, search_window=10)
    assert text[:result] == "hello "


def test_nearest_whitespace_falls_back_to_index_if_no_space():
    text = "a" * 100
    assert ingest._nearest_whitespace(text, 50, search_window=10) == 50


def test_split_by_size_short_text_is_a_single_piece():
    text = "short text"
    assert ingest._split_by_size(text, chunk_size=900, overlap=150) == [text]


def test_split_by_size_terminates_and_covers_long_text():
    text = "word " * 1000  # 5000 chars, well over chunk_size
    pieces = ingest._split_by_size(text, chunk_size=900, overlap=150)
    # Regression test: a missing termination check here used to hang forever
    # once `end` reached the end of the text (see git history).
    assert 1 < len(pieces) < 100
    assert all(len(p) <= 900 for p in pieces)


def test_load_csv_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "DATA_DIR", tmp_path)
    dept_dir = tmp_path / "hr"
    dept_dir.mkdir()
    csv_path = dept_dir / "people.csv"
    pd.DataFrame({"name": ["Alice", "Bob"], "salary": [1000, 2000]}).to_csv(csv_path, index=False)

    chunks = ingest._load_csv_file(csv_path, "hr")

    assert len(chunks) == 2
    assert chunks[0].metadata == {"department": "hr", "source": "hr/people.csv", "section": "row_0"}
    assert "Alice" in chunks[0].text
    assert "1000" in chunks[0].text
    assert chunks[0].id != chunks[1].id


def test_load_markdown_file_one_chunk_per_short_section(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "DATA_DIR", tmp_path)
    dept_dir = tmp_path / "finance"
    dept_dir.mkdir()
    md_path = dept_dir / "doc.md"
    md_path.write_text(
        "# Title\nIntro.\n## Section A\nShort content A.\n## Section B\nShort content B.",
        encoding="utf-8",
    )

    chunks = ingest._load_markdown_file(md_path, "finance")

    assert len(chunks) == 3  # Title, Section A, Section B -- none need size-splitting
    assert {c.metadata["section"] for c in chunks} == {"Title", "Section A", "Section B"}
    assert all(c.metadata["department"] == "finance" for c in chunks)
    assert all(c.metadata["source"] == "finance/doc.md" for c in chunks)
    assert all("part" in c.metadata for c in chunks)


def test_load_all_chunks_on_real_project_data():
    # Regression test against the actual resources/data/ fixture used
    # throughout this project -- these exact numbers were verified by hand
    # (and by scripts/build_index.py's output) many times during development.
    chunks = ingest.load_all_chunks(ingest.DATA_DIR)
    assert len(chunks) == 249

    by_department = {}
    for c in chunks:
        by_department[c.metadata["department"]] = by_department.get(c.metadata["department"], 0) + 1

    assert by_department == {
        "engineering": 43,
        "finance": 28,
        "general": 22,
        "hr": 100,
        "marketing": 56,
    }
