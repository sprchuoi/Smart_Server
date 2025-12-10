from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

from app.core.config import settings
from app.core.logging import logger
from app.core.database import init_db
from app.services.mqtt_bridge import mqtt_bridge
from app.services.llm_service import llm_service
from app.services.ota_service import ota_service
from app.services.report_generator import report_generator

# Import API routers
from app.api import devices, chat, ota, reports
from app.api.websocket import manager, handle_websocket_message

# Create FastAPI app
app = FastAPI(
    title="Smart Server",
    description="Raspberry Pi Smart Home Server with MQTT, LLM, OTA, and Reporting",
    version="1.0.0",
    debug=settings.DEBUG
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(devices.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(ota.router, prefix="/api")
app.include_router(reports.router, prefix="/api")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Smart Server...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Initialize LLM service
        await llm_service.initialize()
        logger.info("LLM service initialized")
        
        # Setup and connect MQTT bridge
        mqtt_bridge.setup(asyncio.get_event_loop())
        await mqtt_bridge.connect()
        logger.info("MQTT bridge connected")
        
        logger.info("Smart Server started successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Shutting down Smart Server...")
    
    try:
        await mqtt_bridge.disconnect()
        logger.info("MQTT bridge disconnected")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("Smart Server shut down")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Smart Server",
        "version": "1.0.0",
        "status": "running",
        "mqtt_connected": mqtt_bridge.connected,
        "endpoints": {
            "api": "/api",
            "docs": "/docs",
            "websocket": "/ws"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mqtt_connected": mqtt_bridge.connected,
        "database": "connected"
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await manager.send_personal_message(
            {
                "type": "connected",
                "message": "Connected to Smart Server"
            },
            websocket
        )
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(websocket, data)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
