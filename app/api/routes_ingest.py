from fastapi import APIRouter, File, UploadFile

from app.models.schemas import IngestResponse
from app.services.ingest_service import IngestService


router = APIRouter(prefix="/ingest", tags=["ingest"])
ingest_service = IngestService()


@router.post("/file", response_model=IngestResponse)
async def ingest_file(file: UploadFile = File(...)) -> IngestResponse:
    return await ingest_service.ingest_upload(file)
