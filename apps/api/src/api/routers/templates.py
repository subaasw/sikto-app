from fastapi import APIRouter

from api.scenes.templates import TEMPLATES, Template

router = APIRouter()


@router.get("/templates", response_model=list[Template])
def list_templates() -> list[Template]:
    """The available lesson visual templates (palette + background presets)."""
    return list(TEMPLATES.values())
