from fastembed import SparseTextEmbedding, TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchAny,
    MatchValue,
    Prefetch,
    SparseVector,
)

from app.core.config import get_settings
from app.ingestion.pipeline import COLLECTION_NAME

settings = get_settings()

dense_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
reranker_model = TextCrossEncoder(model_name="Xenova/ms-marco-MiniLM-L-6-v2")


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)


def build_access_filter(
    tenant_id: str,
    user_role: str,
    user_groups: list[str] | None = None,
) -> Filter:
    
    must_conditions = [
        FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
        FieldCondition(key="allowed_roles", match=MatchAny(any=[user_role])),
    ]

    if user_groups:
        must_conditions.append(
            FieldCondition(key="allowed_groups", match=MatchAny(any=user_groups))
        )

    return Filter(must=must_conditions)


def hybrid_search(
    query: str,
    tenant_id: str,
    user_role: str,
    user_groups: list[str] | None = None,
    top_k: int = 3,
) -> list[dict]:

    client = get_qdrant_client()

    dense_query = next(dense_model.embed([query])).tolist()
    sparse_raw = next(sparse_model.embed([query]))
    sparse_query = SparseVector(
        indices=sparse_raw.indices.tolist(),
        values=sparse_raw.values.tolist(),
    )

    access_filter = build_access_filter(tenant_id, user_role, user_groups)

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            Prefetch(
                query=dense_query,
                using="dense",
                filter=access_filter,
                limit=10,
            ),
            Prefetch(
                query=sparse_query,
                using="sparse",
                filter=access_filter,
                limit=10,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=10,
    )

    points = response.points
    if not points:
        return []

    documents_text = [p.payload["text"] for p in points]
    rerank_scores = list(reranker_model.rerank(query, documents_text))

    results = []
    for point, score in zip(points, rerank_scores):
        results.append(
            {
                "chunk_id": str(point.id),
                "document_id": point.payload.get("document_id"),
                "source": point.payload.get("source"),
                "category": point.payload.get("category"),
                "rerank_score": round(float(score), 4),
                "text": point.payload.get("text"),
            }
        )

    results.sort(key=lambda x: x["rerank_score"], reverse=True)
    return results[:top_k]