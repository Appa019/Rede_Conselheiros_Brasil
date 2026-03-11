"""Prediction-related Pydantic schemas."""

from pydantic import BaseModel


class PredictedLink(BaseModel):
    """A predicted future board connection."""

    source: str
    target: str
    probability: float
