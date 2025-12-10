from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.report_generator import report_generator
from pydantic import BaseModel

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    report_type: str
    format: str = "html"
    device_id: Optional[str] = None
    hours: Optional[int] = 24


@router.get("/")
async def list_reports():
    """List all generated reports."""
    reports = await report_generator.list_reports()
    return {"reports": reports}


@router.post("/generate")
async def generate_report(request: ReportRequest):
    """Generate a new report."""
    try:
        if request.report_type == "device_status":
            result = await report_generator.generate_device_status_report(
                format=request.format
            )
        elif request.report_type == "sensor_data":
            result = await report_generator.generate_sensor_data_report(
                device_id=request.device_id,
                hours=request.hours or 24,
                format=request.format
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


@router.get("/device-status")
async def quick_device_status_report(format: str = Query(default="html")):
    """Quick endpoint to generate device status report."""
    result = await report_generator.generate_device_status_report(format=format)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.get("/sensor-data")
async def quick_sensor_data_report(
    device_id: Optional[str] = None,
    hours: int = Query(default=24),
    format: str = Query(default="html")
):
    """Quick endpoint to generate sensor data report."""
    result = await report_generator.generate_sensor_data_report(
        device_id=device_id,
        hours=hours,
        format=format
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result
