import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class OTAService:
    """OTA (Over-The-Air) firmware update service."""
    
    def __init__(self):
        self.firmware_dir = Path(settings.OTA_FIRMWARE_DIR)
        self.version_file = Path(settings.OTA_VERSION_FILE)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure OTA directories exist."""
        self.firmware_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default version file if it doesn't exist
        if not self.version_file.exists():
            self._create_default_version_file()
    
    def _create_default_version_file(self):
        """Create default version.json file."""
        default_version = {
            "version": "1.0.0",
            "build": 1,
            "release_date": datetime.utcnow().isoformat(),
            "changelog": "Initial release",
            "firmware_url": "/api/ota/firmware/firmware.bin",
            "checksum": "",
            "size_bytes": 0,
            "min_required_version": "0.0.0"
        }
        
        try:
            with open(self.version_file, 'w') as f:
                json.dump(default_version, f, indent=2)
            logger.info(f"Created default version file at {self.version_file}")
        except Exception as e:
            logger.error(f"Error creating default version file: {e}")
    
    def get_version_info(self) -> Dict[str, Any]:
        """Get current firmware version information."""
        try:
            if self.version_file.exists():
                with open(self.version_file, 'r') as f:
                    return json.load(f)
            else:
                return {"error": "Version file not found"}
        except Exception as e:
            logger.error(f"Error reading version file: {e}")
            return {"error": str(e)}
    
    def check_update(self, current_version: str) -> Dict[str, Any]:
        """Check if update is available for given version."""
        try:
            version_info = self.get_version_info()
            
            if "error" in version_info:
                return version_info
            
            latest_version = version_info.get("version", "0.0.0")
            
            # Simple version comparison (should use proper semver in production)
            if self._is_newer_version(latest_version, current_version):
                return {
                    "update_available": True,
                    "latest_version": latest_version,
                    "current_version": current_version,
                    "version_info": version_info
                }
            else:
                return {
                    "update_available": False,
                    "latest_version": latest_version,
                    "current_version": current_version
                }
                
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return {"error": str(e)}
    
    def _is_newer_version(self, latest: str, current: str) -> bool:
        """Compare version strings (simple implementation)."""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(latest_parts), len(current_parts))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            current_parts.extend([0] * (max_len - len(current_parts)))
            
            return latest_parts > current_parts
        except Exception:
            return False
    
    def get_firmware_path(self, filename: str = "firmware.bin") -> Optional[Path]:
        """Get path to firmware file."""
        firmware_path = self.firmware_dir / filename
        
        if firmware_path.exists():
            return firmware_path
        else:
            logger.warning(f"Firmware file not found: {firmware_path}")
            return None
    
    def update_version_info(self, version_data: Dict[str, Any]) -> bool:
        """Update version.json with new version information."""
        try:
            # Merge with existing data
            current_info = self.get_version_info()
            if "error" not in current_info:
                current_info.update(version_data)
                version_data = current_info
            
            # Add update timestamp
            version_data["updated_at"] = datetime.utcnow().isoformat()
            
            with open(self.version_file, 'w') as f:
                json.dump(version_data, f, indent=2)
            
            logger.info(f"Updated version info: {version_data.get('version')}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating version info: {e}")
            return False
    
    def upload_firmware(self, firmware_content: bytes, filename: str = "firmware.bin") -> Dict[str, Any]:
        """Upload new firmware file."""
        try:
            firmware_path = self.firmware_dir / filename
            
            # Write firmware file
            with open(firmware_path, 'wb') as f:
                f.write(firmware_content)
            
            size_bytes = len(firmware_content)
            
            # Calculate checksum (simple implementation)
            import hashlib
            checksum = hashlib.sha256(firmware_content).hexdigest()
            
            logger.info(f"Uploaded firmware: {filename} ({size_bytes} bytes)")
            
            return {
                "success": True,
                "filename": filename,
                "size_bytes": size_bytes,
                "checksum": checksum,
                "path": str(firmware_path)
            }
            
        except Exception as e:
            logger.error(f"Error uploading firmware: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global OTA service instance
ota_service = OTAService()
