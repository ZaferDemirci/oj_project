from fastapi import APIRouter, Request, HTTPException, status, Depends
from datetime import datetime
import shutil
import json
import os

from app.utils.dependencies import require_admin
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.models.audit import AuditLog

router = APIRouter()
audit_repo = AuditRepository()

DATA_DIR = "data"
BACKUP_DIR = "data/backups"

@router.post("/admin/backups", status_code=status.HTTP_201_CREATED)
async def create_backup(
    request: Request,
    current_user: User = Depends(require_admin)) -> dict:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Generate backup ID
    backup_id = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    backup_path = os.path.join(BACKUP_DIR, backup_id)
    os.makedirs(backup_path, exist_ok=True)
    
    # Copy all JSON files from data/ to backup/
    manifest = {
        "backup_id": backup_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "files": []
    }
    
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json") and filename != "backups":
            src = os.path.join(DATA_DIR, filename)
            dst = os.path.join(backup_path, filename)
            shutil.copy2(src, dst)
            manifest["files"].append(filename)
    
    # Write manifest
    with open(os.path.join(backup_path, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    
    # Audit log
    audit_log = AuditLog.create_log(
        operator_id=current_user.id,
        action="CREATE_BACKUP",
        target_type="backup",
        target_id=backup_id,
        success=True
    )
    audit_repo.create(audit_log)
    
    return {
        "code": 201,
        "message": "backup created",
        "data": {
            "backup_id": backup_id,
            "created_at": manifest["created_at"],
        }
    }


@router.get("/admin/backups")
async def list_backups(
    request: Request,
    current_user: User = Depends(require_admin)) -> dict:
    if not os.path.exists(BACKUP_DIR):
        return {"code": 200, "message": "ok", "data": {"items": [], "total": 0}}
    
    backups = []
    for item in os.listdir(BACKUP_DIR):
        backup_path = os.path.join(BACKUP_DIR, item)
        if os.path.isdir(backup_path):
            manifest_path = os.path.join(backup_path, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                        backups.append(manifest)
                except:
                    backups.append({
                        "backup_id": item,
                        "created_at": "unknown",
                        "files": []
                    })
    
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "items": backups,
            "total": len(backups),
        }
    }


@router.post("/admin/backups/{backup_id}/restore")
async def restore_backup(
    backup_id: str,
    request: Request,
    current_user: User = Depends(require_admin)) -> dict:
    backup_path = os.path.join(BACKUP_DIR, backup_id)
    if not os.path.exists(backup_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found"
        )

    # Verify manifest exists
    manifest_path = os.path.join(backup_path, "manifest.json")
    if not os.path.exists(manifest_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backup manifest missing"
        )

    # Read manifest
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Create a safety backup of current data
    safety_dir = os.path.join(DATA_DIR, f"safety_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(safety_dir, exist_ok=True)
    for filename in manifest.get("files", []):
        src = os.path.join(DATA_DIR, filename)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(safety_dir, filename))

    # Atomic restore with auto revert
    restore_success = False
    try:
        # restore
        for filename in manifest.get("files", []):
            src = os.path.join(backup_path, filename)
            dst = os.path.join(DATA_DIR, filename)
            if os.path.exists(src):
                shutil.copy2(src, dst)
        restore_success = True
    except Exception as e:
        # Restore failed, revert from safety copy
        print(f"Restore failed, reverting from safety copy: {e}")
        try:
            for filename in manifest.get("files", []):
                safety_src = os.path.join(safety_dir, filename)
                dst = os.path.join(DATA_DIR, filename)
                if os.path.exists(safety_src):
                    shutil.copy2(safety_src, dst)
        except Exception as revert_err:
            # Even revert failed. Log manually
            print(f"CRITICAL: Revert failed! Data may be corrupted. Manual recovery needed: {revert_err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Restore failed AND revert failed! Manual recovery from {safety_dir} required."
            )
        # Revert succeeded, raise original error to user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore failed: {str(e)}. Reverted to safety copy."
        )

    # Restore succeeded. Clean up safety copy
    try:
        shutil.rmtree(safety_dir)
    except Exception:
        pass  # Best effort

    # Audit log
    audit_log = AuditLog.create_log(
        operator_id=current_user.id,
        action="RESTORE_BACKUP",
        target_type="backup",
        target_id=backup_id,
        success=True,
        detail=f"Restored from backup {backup_id} (safety copy at {safety_dir})"
    )
    audit_repo.create(audit_log)

    return {
        "code": 200,
        "message": "Backup restored successfully. Please re-login to refresh your session.",
        "data": None
    }