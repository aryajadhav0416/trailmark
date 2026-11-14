"""Pydantic schemas for request/response validation (skeleton)."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Healthcheck response model."""

    status: str
