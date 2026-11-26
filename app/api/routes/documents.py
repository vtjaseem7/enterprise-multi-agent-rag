from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from app.core.security import CurrentUser, get_current_user
from app.ingestion.pipeline import ingest_file

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

UPLOAD_DIR = Path("data/raw")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("general"),
    allowed_roles: str = Form("admin,employee"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Admin-only endpoint to save a file and index it into Qdrant."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can upload documents.",
        )

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".txt", ".md", ".pdf"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt, .md, and .pdf files are supported.",
        )

    saved_path = UPLOAD_DIR / Path(file.filename).name
    content = await file.read()
    saved_path.write_bytes(content)

    roles_list = [r.strip() for r in allowed_roles.split(",") if r.strip()]
    try:
        result = ingest_file(
            file_path=saved_path,
            tenant_id=current_user.tenant_id,
            allowed_roles=roles_list,
            category=category,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return {"status": "indexed", **result}
