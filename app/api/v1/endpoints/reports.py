from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.reports import CreateReportRequest, ReportRead
from app.services.reports import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: CreateReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ReportRead:
    report = ReportService.create_report(
        db,
        reporter_id=current_user.id,
        reported_id=payload.reported_user_id,
        reason=payload.reason,
        description=payload.description,
        call_session_id=payload.call_session_id,
    )
    return ReportRead.model_validate(report)
