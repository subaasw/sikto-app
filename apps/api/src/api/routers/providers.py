from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.agent.catalog import available_providers
from api.config import Settings, get_settings

router = APIRouter(tags=["providers"])


class ProviderResponse(BaseModel):
    id: str
    label: str
    models: list[str]
    default: str


@router.get("/providers", response_model=list[ProviderResponse])
async def list_providers(
    settings: Settings = Depends(get_settings),
) -> list[ProviderResponse]:
    return [
        ProviderResponse(id=p.id, label=p.label, models=p.models, default=p.default)
        for p in available_providers(settings)
    ]
