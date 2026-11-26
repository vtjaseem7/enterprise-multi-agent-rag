import hashlib
import uuid
from pathlib import Path
import pymupdf  
from fastembed import SparseTextEmbedding, TextEmbedding
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Modifier,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.core.config import get_settings

settings = get_settings()

COLLECTION_NAME = "company_knowledge"


dense_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)


def ensure_collection_exists(client: QdrantClient) -> None:
    if client.collection_exists(COLLECTION_NAME):
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": VectorParams(size=384, distance=Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(modifier=Modifier.IDF),
        },
    )
    print(f"Created Qdrant collection: {COLLECTION_NAME}")


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            hasher.update(block)
    return hasher.hexdigest()


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        pages = []
        with pymupdf.open(file_path) as doc:
            for page in doc:
                pages.append(page.get_text("text"))
        return "\n".join(pages)

    raise ValueError(f"Unsupported file type: {suffix}")


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 120) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def ingest_file(
    file_path: str | Path,
    tenant_id: str,
    allowed_roles: list[str],
    allowed_groups: list[str] | None = None,
    category: str = "general",
) -> dict:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    client = get_qdrant_client()
    ensure_collection_exists(client)

    content_hash = compute_sha256(path)
    raw_text = extract_text(path).strip()
    if not raw_text:
        raise ValueError("Extracted text is empty.")


    chunks = chunk_text(raw_text)

    dense_embeddings = list(dense_model.embed(chunks))
    sparse_embeddings = list(sparse_model.embed(chunks))

    document_id = str(uuid.uuid4())
    points = []

    for idx, (chunk, dense_vec, sparse_vec) in enumerate(
        zip(chunks, dense_embeddings, sparse_embeddings)
    ):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": dense_vec.tolist(),
                    "sparse": SparseVector(
                        indices=sparse_vec.indices.tolist(),
                        values=sparse_vec.values.tolist(),
                    ),
                },
                payload={
                    "tenant_id": tenant_id,
                    "document_id": document_id,
                    "chunk_index": idx,
                    "source": path.name,
                    "category": category,
                    "content_hash": content_hash,
                    "allowed_roles": allowed_roles,
                    "allowed_groups": allowed_groups or [],
                    "text": chunk,
                },
            )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)

    return {
        "document_id": document_id,
        "source": path.name,
        "content_hash": content_hash,
        "chunks_indexed": len(points),
    }