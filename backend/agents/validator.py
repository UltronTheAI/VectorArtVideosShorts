from __future__ import annotations

from backend.schemas import Project
from backend.tools.scene_tools import validate_scene_parameters


class ValidationFailure(ValueError):
    pass


def validate_project(project: Project) -> Project:
    for scene in project.scenes:
        ok, errors = validate_scene_parameters(scene.model_dump())
        if not ok:
            raise ValidationFailure(f"{scene.id}: {'; '.join(errors)}")
    return project


def parse_project_with_retries(payload: dict, attempts: int = 3) -> Project:
    last: Exception | None = None
    for _ in range(attempts):
        try:
            return validate_project(Project.model_validate(payload))
        except Exception as exc:
            last = exc
    raise ValidationFailure(f"Project validation failed after {attempts} attempts: {last}")

