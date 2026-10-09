import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.blocks import BlockListResponse, BlockUserResponse
from app.services.blocks import BlockService

router = APIRouter(prefix="/blocks", tags=["blocks"])


@router.get("", response_model=BlockListResponse)
def list_blocks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BlockListResponse:
    items = BlockService.list_blocked(db, current_user.id)
    return BlockListResponse(items=[BlockUserResponse.model_validate(item) for item in items])


@router.post("/{blocked_user_id}", response_model=BlockUserResponse, status_code=status.HTTP_201_CREATED)
def block_user(
    blocked_user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BlockUserResponse:
    record = BlockService.block_user(db, blocker_id=current_user.id, blocked_id=blocked_user_id)
    return BlockUserResponse.model_validate(record)


@router.delete("/{blocked_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def unblock_user(
    blocked_user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    BlockService.unblock_user(db, blocker_id=current_user.id, blocked_id=blocked_user_id)
