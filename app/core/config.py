from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # MQTT Configuration
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_TOPIC_PREFIX: str = "smart_home"
    
    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./smart_server.db"
    
    # LLM Configuration
    LLM_PROVIDER: str = "local"
    LLM_MODEL_PATH: str = "./models/llama-7b.gguf"
    LLM_FALLBACK_PROVIDER: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # OTA Server Configuration
    OTA_FIRMWARE_DIR: str = "./ota"
    OTA_VERSION_FILE: str = "./ota/version.json"
    
    # Report Configuration
    REPORT_OUTPUT_DIR: str = "./reports"
    REPORT_TEMPLATE_DIR: str = "./templates/reports"
    
    # Tailscale Configuration (informational)
    TAILSCALE_HOSTNAME: str = "smart-server"
    
    # Security
    SECRET_KEY: str = "change_this_to_a_random_secret_key"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/smart_server.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
