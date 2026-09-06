"""Datasets catalogue router."""
from fastapi import APIRouter
from app.models.schemas import DatasetInfo
from app.services import dataset_service

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetInfo])
def list_datasets():
    """Return all available datasets with metadata."""
    return dataset_service.list_datasets()


@router.get("/{dataset_id}", response_model=DatasetInfo)
def get_dataset(dataset_id: str):
    """Return metadata for a specific dataset."""
    datasets = dataset_service.list_datasets()
    for ds in datasets:
        if ds.id == dataset_id:
            return ds
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
