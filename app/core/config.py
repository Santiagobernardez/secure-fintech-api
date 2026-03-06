import os

class Settings:
    PROJECT_NAME: str = "Secure Fintech API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    API_V1_PREFIX: str = "/api/v1"

settings = Settings()