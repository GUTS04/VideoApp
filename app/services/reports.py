import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_report import UserReport

MAX_REPORTS_PER_HOUR = 10


class ReportService:
    @staticmethod
    def create_report(
        db: Session,
        *,
        reporter_id: uuid.UUID,
        reported_id: uuid.UUID,
        reason: str,
        description: str | None = None,
        call_session_id: uuid.UUID | None = None,
    ) -> UserReport:
        if reporter_id == reported_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot report yourself")
        reported = db.get(User, reported_id)
        if not reported:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        since = datetime.now(UTC) - timedelta(hours=1)
        recent_count = db.scalar(
            select(func.count())
            .select_from(UserReport)
            .where(UserReport.reporter_id == reporter_id, UserReport.created_at >= since)
        ) or 0
        if recent_count >= MAX_REPORTS_PER_HOUR:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many reports. Try again later.",
            )

        report = UserReport(
            reporter_id=reporter_id,
            reported_id=reported_id,
            reason=reason,
            description=description,
            call_session_id=call_session_id,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
