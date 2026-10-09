import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CoinBalanceResponse(BaseModel):
    balance: int
    coins_per_minute: float = Field(description="100 coins = 35 minutes")


class CoinTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: int
    transaction_type: str
    reason: str
    call_session_id: uuid.UUID | None
    created_at: datetime


class CoinTransactionListResponse(BaseModel):
    items: list[CoinTransactionRead]
    total: int
