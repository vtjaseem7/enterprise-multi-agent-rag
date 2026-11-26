from fastapi import FastAPI
from pydantic import BaseModel
from app.api.routes import chat, documents
from app.core.security import CurrentUser, create_access_token

app = FastAPI(
    title="Enterprise Multi-Agent RAG API",
    version="1.0.0",
)

app.include_router(chat.router)
app.include_router(documents.router)


@app.get("/api/v1/health", tags=["System"])
def health_check() -> dict:
    return {"status": "ok"}


class DevTokenRequest(BaseModel):
    user_id: str = "user_1"
    tenant_id: str = "tenant_acme"
    role: str = "customer"  # Try "customer" or "admin"


@app.post("/api/v1/auth/dev-token", tags=["Auth (Dev)"])
def generate_dev_token(req: DevTokenRequest) -> dict:
    """Development helper to mint a JWT for testing roles."""
    token = create_access_token(
        CurrentUser(
            user_id=req.user_id,
            tenant_id=req.tenant_id,
            role=req.role,
        )
    )
    return {"access_token": token, "token_type": "bearer"}