from api.scenes.schema import (
    Element,
    ElementType,
    Narration,
    Scene,
    SceneDocument,
    SceneKind,
)


def test_scene_document_round_trips():
    doc = SceneDocument(
        title="Photosynthesis",
        summary="How plants make food",
        scenes=[
            Scene(
                id="s0",
                narration=Narration(text="Plants turn light into sugar."),
                elements=[Element(id="s0-h", type=ElementType.heading, text="Photosynthesis")],
            )
        ],
    )
    restored = SceneDocument.model_validate_json(doc.model_dump_json())
    assert restored == doc
    assert restored.scenes[0].kind == SceneKind.slide
    assert restored.theme.primary == "#84cc16"


def test_scene_document_requires_at_least_one_scene():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SceneDocument(title="t", summary="s", scenes=[])
