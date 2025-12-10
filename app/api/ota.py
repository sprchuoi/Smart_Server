from fastapi import APIRouter, HTTPException, Query, File, UploadFile, Response
from fastapi.responses import FileResponse
from typing import Optional

from app.services.ota_service import ota_service
from pydantic import BaseModel

router = APIRouter(prefix="/ota", tags=["ota"])


class VersionInfo(BaseModel):
    version: str
    build: int
    release_date: str
    changelog: str
    firmware_url: str
    checksum: str
    size_bytes: int
    min_required_version: str


class UpdateCheckRequest(BaseModel):
    current_version: str
    device_id: Optional[str] = None


@router.get("/version")
async def get_version():
    """Get current firmware version information."""
    version_info = ota_service.get_version_info()
    
    if "error" in version_info:
        raise HTTPException(status_code=404, detail=version_info["error"])
    
    return version_info


@router.post("/check-update")
async def check_update(request: UpdateCheckRequest):
    """Check if firmware update is available."""
    result = ota_service.check_update(request.current_version)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/firmware/{filename}")
async def download_firmware(filename: str):
    """Download firmware file."""
    firmware_path = ota_service.get_firmware_path(filename)
    
    if not firmware_path:
        raise HTTPException(status_code=404, detail="Firmware file not found")
    
    return FileResponse(
        firmware_path,
        media_type="application/octet-stream",
        filename=filename
    )


@router.post("/firmware/upload")
async def upload_firmware(
    file: UploadFile = File(...),
    version: str = Query(...),
    changelog: str = Query(default="")
):
    """Upload new firmware file."""
    try:
        # Read firmware content
        content = await file.read()
        
        # Upload firmware
        result = ota_service.upload_firmware(content, file.filename or "firmware.bin")
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        
        # Update version info
        version_data = {
            "version": version,
            "changelog": changelog,
            "checksum": result["checksum"],
            "size_bytes": result["size_bytes"],
            "firmware_url": f"/api/ota/firmware/{file.filename or 'firmware.bin'}"
        }
        
        ota_service.update_version_info(version_data)
        
        return {
            "success": True,
            "message": "Firmware uploaded successfully",
            "version": version,
            **result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading firmware: {str(e)}")
