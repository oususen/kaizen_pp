from __future__ import annotations

from pathlib import Path
from typing import IO

from django.conf import settings


def save_proposal_image(file_obj, management_no: str, kind: str) -> str:
    """Persist uploaded image and return relative path under MEDIA_ROOT."""
    ext = Path(file_obj.name).suffix or ".jpg"
    relative_path = Path("proposals") / management_no / f"{kind}{ext}"
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    with absolute_path.open("wb") as dest:
        for chunk in file_obj.chunks() if hasattr(file_obj, "chunks") else [file_obj.read()]:
            dest.write(chunk)
    return str(relative_path).replace("\\", "/")
