from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

from app.services.ingest import Chunk

PERSIST_DIR = Path(__file__).resolve().parents[2] / "resources" / "vectorstore"
COLLECTION_NAME = "company_docs"

_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Une "collection" Chroma, c'est l'équivalent d'une table 
# dans une base de données classique
def get_collection():
    client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_fn,
    )

# Cette fonction prend la liste de Chunk produite par load_all_chunks et 
# remplit la base vectorielle
def index_chunks(chunks):
    client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except chromadb.errors.NotFoundError:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_fn,
    )

    collection.add(
        ids=[c.id for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[c.metadata for c in chunks],
    )

def query(question, allowed_departments, n_results=4):
    collection = get_collection()
    result = collection.query(
        query_texts=[question],
        n_results=n_results,
        where={"department": {"$in": sorted(allowed_departments)}},
    )
    documents = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]
    return [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]