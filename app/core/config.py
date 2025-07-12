from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/rinha_db"
    
    # Application
    port: int = 9999
    host: str = "0.0.0.0"
    
    # Payment Processors
    payment_0_url: str = "http://localhost:3001"
    payment_1_url: str = "http://localhost:3002"
    
    # Performance
    max_workers: int = 10
    request_timeout: int = 5
    
    # Health Check
    health_check_interval: int = 5
    
    # Circuit Breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 30
    
    # Database Pool
    pool_size: int = 20
    max_overflow: int = 30


settings = Settings()
