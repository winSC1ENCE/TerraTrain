from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    database: str = "unknown"
    ollama: str = "unknown"
