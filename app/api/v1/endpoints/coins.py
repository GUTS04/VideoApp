from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.coins import CoinBalanceResponse, CoinTransactionListResponse, CoinTransactionRead
from app.services.billing import coins_per_minute
from app.services.coins import CoinService

router = APIRouter(prefix="/coins", tags=["coins"])


@router.get("/balance", response_model=CoinBalanceResponse)
def get_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CoinBalanceResponse:
    balance = CoinService.get_balance(db, current_user.id)
    return CoinBalanceResponse(balance=balance, coins_per_minute=coins_per_minute())


@router.get("/transactions", response_model=CoinTransactionListResponse)
def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CoinTransactionListResponse:
    items, total = CoinService.list_transactions(db, current_user.id, skip=skip, limit=limit)
    return CoinTransactionListResponse(
        items=[CoinTransactionRead.model_validate(item) for item in items],
        total=total,
    )
