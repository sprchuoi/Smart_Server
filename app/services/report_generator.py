import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
import pandas as pd

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.database import Device, SensorData, Report
from sqlalchemy import select, func

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Service for generating various types of reports."""
    
    def __init__(self):
        self.output_dir = Path(settings.REPORT_OUTPUT_DIR)
        self.template_dir = Path(settings.REPORT_TEMPLATE_DIR)
        self._ensure_directories()
        self._setup_jinja()
    
    def _ensure_directories(self):
        """Ensure report directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Create .gitkeep file
        gitkeep = self.output_dir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
    
    def _setup_jinja(self):
        """Setup Jinja2 template environment."""
        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(self.template_dir))
            )
        except Exception as e:
            logger.error(f"Error setting up Jinja2: {e}")
            self.jinja_env = None
    
    async def generate_device_status_report(self, format: str = "html") -> Dict[str, Any]:
        """Generate device status report."""
        try:
            async with AsyncSessionLocal() as session:
                # Get all devices
                result = await session.execute(select(Device))
                devices = result.scalars().all()
                
                # Prepare report data
                report_data = {
                    "title": "Device Status Report",
                    "generated_at": datetime.utcnow().isoformat(),
                    "total_devices": len(devices),
                    "online_devices": sum(1 for d in devices if d.status == "online"),
                    "offline_devices": sum(1 for d in devices if d.status == "offline"),
                    "devices": [
                        {
                            "id": d.device_id,
                            "name": d.name,
                            "type": d.device_type,
                            "status": d.status,
                            "firmware_version": d.firmware_version,
                            "last_seen": d.last_seen.isoformat() if d.last_seen else None
                        }
                        for d in devices
                    ]
                }
                
                # Generate report file
                if format == "html":
                    filename = await self._generate_html_report("device_status", report_data)
                elif format == "pdf":
                    filename = await self._generate_pdf_report("device_status", report_data)
                else:
                    filename = await self._generate_json_report("device_status", report_data)
                
                # Store report record in database
                report = Report(
                    report_type="device_status",
                    title=report_data["title"],
                    file_path=str(filename),
                    status="completed",
                    parameters=json.dumps({"format": format}),
                    completed_at=datetime.utcnow()
                )
                session.add(report)
                await session.commit()
                
                return {
                    "success": True,
                    "report_id": report.id,
                    "file_path": str(filename),
                    "format": format
                }
                
        except Exception as e:
            logger.error(f"Error generating device status report: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_sensor_data_report(
        self,
        device_id: Optional[str] = None,
        hours: int = 24,
        format: str = "html"
    ) -> Dict[str, Any]:
        """Generate sensor data report with charts."""
        try:
            async with AsyncSessionLocal() as session:
                # Query sensor data
                query = select(SensorData).where(
                    SensorData.timestamp >= datetime.utcnow() - timedelta(hours=hours)
                )
                
                if device_id:
                    query = query.where(SensorData.device_id == device_id)
                
                query = query.order_by(SensorData.timestamp)
                result = await session.execute(query)
                sensor_data = result.scalars().all()
                
                # Prepare data for report
                df = pd.DataFrame([
                    {
                        "device_id": sd.device_id,
                        "sensor_type": sd.sensor_type,
                        "value": sd.value,
                        "unit": sd.unit,
                        "timestamp": sd.timestamp
                    }
                    for sd in sensor_data
                ])
                
                # Generate charts
                chart_paths = []
                if not df.empty:
                    chart_paths = await self._generate_sensor_charts(df)
                
                report_data = {
                    "title": f"Sensor Data Report - Last {hours} Hours",
                    "generated_at": datetime.utcnow().isoformat(),
                    "device_id": device_id or "All Devices",
                    "hours": hours,
                    "total_readings": len(sensor_data),
                    "charts": chart_paths,
                    "summary": self._calculate_sensor_summary(df) if not df.empty else {}
                }
                
                # Generate report file
                if format == "html":
                    filename = await self._generate_html_report("sensor_data", report_data)
                elif format == "pdf":
                    filename = await self._generate_pdf_report("sensor_data", report_data)
                else:
                    filename = await self._generate_json_report("sensor_data", report_data)
                
                # Store report record
                report = Report(
                    report_type="sensor_data",
                    title=report_data["title"],
                    file_path=str(filename),
                    status="completed",
                    parameters=json.dumps({"device_id": device_id, "hours": hours, "format": format}),
                    completed_at=datetime.utcnow()
                )
                session.add(report)
                await session.commit()
                
                return {
                    "success": True,
                    "report_id": report.id,
                    "file_path": str(filename),
                    "format": format
                }
                
        except Exception as e:
            logger.error(f"Error generating sensor data report: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_sensor_charts(self, df: pd.DataFrame) -> List[str]:
        """Generate charts from sensor data."""
        chart_paths = []
        
        try:
            # Group by sensor type and create charts
            for sensor_type in df['sensor_type'].unique():
                sensor_df = df[df['sensor_type'] == sensor_type]
                
                plt.figure(figsize=(10, 6))
                
                for device_id in sensor_df['device_id'].unique():
                    device_data = sensor_df[sensor_df['device_id'] == device_id]
                    plt.plot(
                        device_data['timestamp'],
                        device_data['value'],
                        label=f"{device_id}",
                        marker='o'
                    )
                
                plt.xlabel('Timestamp')
                plt.ylabel(f"Value ({sensor_df['unit'].iloc[0]})")
                plt.title(f"Sensor Data: {sensor_type}")
                plt.legend()
                plt.grid(True)
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                # Save chart
                chart_filename = f"chart_{sensor_type.replace('/', '_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
                chart_path = self.output_dir / chart_filename
                plt.savefig(chart_path)
                plt.close()
                
                chart_paths.append(str(chart_filename))
                
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
        
        return chart_paths
    
    def _calculate_sensor_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary statistics from sensor data."""
        summary = {}
        
        try:
            for sensor_type in df['sensor_type'].unique():
                sensor_df = df[df['sensor_type'] == sensor_type]
                summary[sensor_type] = {
                    "min": float(sensor_df['value'].min()),
                    "max": float(sensor_df['value'].max()),
                    "mean": float(sensor_df['value'].mean()),
                    "median": float(sensor_df['value'].median()),
                    "std": float(sensor_df['value'].std()),
                    "count": int(sensor_df['value'].count())
                }
        except Exception as e:
            logger.error(f"Error calculating summary: {e}")
        
        return summary
    
    async def _generate_html_report(self, report_type: str, data: Dict[str, Any]) -> Path:
        """Generate HTML report."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f"{report_type}_{timestamp}.html"
        
        # Simple HTML template if Jinja2 template doesn't exist
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{data.get('title', 'Report')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .metadata {{ color: #666; font-size: 0.9em; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .chart {{ margin: 20px 0; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>{data.get('title', 'Report')}</h1>
            <p class="metadata">Generated at: {data.get('generated_at', '')}</p>
            <div class="summary">
                <h2>Summary</h2>
                <pre>{json.dumps(data, indent=2, default=str)}</pre>
            </div>
        </body>
        </html>
        """
        
        with open(filename, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Generated HTML report: {filename}")
        return filename
    
    async def _generate_pdf_report(self, report_type: str, data: Dict[str, Any]) -> Path:
        """Generate PDF report using weasyprint."""
        # First generate HTML
        html_path = await self._generate_html_report(report_type, data)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        pdf_filename = self.output_dir / f"{report_type}_{timestamp}.pdf"
        
        try:
            from weasyprint import HTML
            HTML(str(html_path)).write_pdf(pdf_filename)
            logger.info(f"Generated PDF report: {pdf_filename}")
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            return html_path  # Return HTML as fallback
        
        return pdf_filename
    
    async def _generate_json_report(self, report_type: str, data: Dict[str, Any]) -> Path:
        """Generate JSON report."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f"{report_type}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Generated JSON report: {filename}")
        return filename
    
    async def list_reports(self) -> List[Dict[str, Any]]:
        """List all generated reports."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Report).order_by(Report.created_at.desc())
                )
                reports = result.scalars().all()
                
                return [
                    {
                        "id": r.id,
                        "type": r.report_type,
                        "title": r.title,
                        "file_path": r.file_path,
                        "status": r.status,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "completed_at": r.completed_at.isoformat() if r.completed_at else None
                    }
                    for r in reports
                ]
        except Exception as e:
            logger.error(f"Error listing reports: {e}")
            return []


# Global report generator instance
report_generator = ReportGenerator()
