from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    app: str
    environment: str
    database: str = Field(..., description="connected | disconnected")
