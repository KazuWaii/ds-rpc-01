from app.services import vectorstore
from app.services.ingest import Chunk


def test_query_never_returns_disallowed_department_even_if_more_relevant(tmp_path, monkeypatch):
    """The core RBAC security guarantee, tested against the real embedding
    model and a real (temporary) Chroma collection -- no mocking. An HR
    chunk that is semantically closer to the question must still never be
    returned to a caller whose allowed_departments excludes "hr".
    """
    monkeypatch.setattr(vectorstore, "PERSIST_DIR", tmp_path)

    chunks = [
        Chunk(
            id="hr-1",
            text="Vendor budget increase details for the finance department expense report.",
            metadata={"department": "hr", "source": "hr/data.csv", "section": "row 1"},
        ),
        Chunk(
            id="marketing-1",
            text="Our social media campaign results for Q1.",
            metadata={"department": "marketing", "source": "marketing/report.md", "section": "Q1"},
        ),
    ]
    vectorstore.index_chunks(chunks)

    results = vectorstore.query(
        "What was the vendor budget increase?",
        allowed_departments={"marketing"},
        n_results=5,
    )

    assert len(results) == 1
    assert results[0]["metadata"]["department"] == "marketing"


def test_query_returns_all_allowed_departments(tmp_path, monkeypatch):
    monkeypatch.setattr(vectorstore, "PERSIST_DIR", tmp_path)

    chunks = [
        Chunk(id="f-1", text="Finance content.", metadata={"department": "finance", "source": "a", "section": "s"}),
        Chunk(id="h-1", text="HR content.", metadata={"department": "hr", "source": "b", "section": "s"}),
        Chunk(id="m-1", text="Marketing content.", metadata={"department": "marketing", "source": "c", "section": "s"}),
    ]
    vectorstore.index_chunks(chunks)

    results = vectorstore.query("content", allowed_departments={"finance", "hr", "marketing"}, n_results=10)

    assert {r["metadata"]["department"] for r in results} == {"finance", "hr", "marketing"}


def test_index_chunks_is_idempotent_on_rerun(tmp_path, monkeypatch):
    monkeypatch.setattr(vectorstore, "PERSIST_DIR", tmp_path)

    chunk = Chunk(id="f-1", text="Finance content.", metadata={"department": "finance", "source": "a", "section": "s"})
    vectorstore.index_chunks([chunk])
    vectorstore.index_chunks([chunk])  # re-running must not duplicate

    results = vectorstore.query("content", allowed_departments={"finance"}, n_results=10)
    assert len(results) == 1
