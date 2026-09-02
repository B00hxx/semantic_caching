import os
import re
import yaml
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from API.auth.security import User, get_current_admin
from config import settings
from semantic_caching.presidio_analyzer.prisidio_reload_service import reload_presidio_analyzer
router = APIRouter(prefix='/rules', tags=["rules"])

MAX_FILE_SIZE = 1 * 1024 * 1024

@router.post("/upload-redaction-rules")
async def upload_redaction_rules(file: UploadFile = File(...), current_user: User = Depends(get_current_admin)):
    name = os.path.basename(file.filename)

    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    if not (name.endswith(".yaml") or name.endswith(".yml")):
        raise HTTPException(
            status_code=400,
            detail="Only YAML files are allowed.",
        )

    rules_dir = settings.presidio.custom_rules_dir
    rules_path = Path(rules_dir).resolve()

    os.makedirs(rules_path, exist_ok=True)

    file_path = (rules_path / name).resolve()

    if not file_path.is_relative_to(rules_path):
        raise HTTPException(
            status_code=400,
            detail="Invalid file path.",
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large.",
        )

    try:
        parsed = yaml.safe_load(content)

        if not isinstance(parsed, dict) or "recognizers" not in parsed:
            raise ValueError(
                "YAML file must contain a top-level 'recognizers' key."
            )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid YAML structure: {e}",
        )

    with open(file_path, "wb") as f:
        f.write(content)
    try:
        await reload_presidio_analyzer()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Rules uploaded but analyzer reload failed: {e}",
    )

    return {
        "status": "uploaded",
        "filename": name,
    }