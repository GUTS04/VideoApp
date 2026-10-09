import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.schemas.gender import is_valid_pair


@dataclass
class ActiveMatch:
    match_id: str
    user_a_id: uuid.UUID
    user_a_username: str
    user_b_id: uuid.UUID
    user_b_username: str
    created_at: datetime

    def partner_of(self, user_id: uuid.UUID) -> tuple[uuid.UUID, str] | None:
        if user_id == self.user_a_id:
            return self.user_b_id, self.user_b_username
        if user_id == self.user_b_id:
            return self.user_a_id, self.user_a_username
        return None

    def includes_user(self, user_id: uuid.UUID) -> bool:
        return user_id in (self.user_a_id, self.user_b_id)


class MatchManager:
    """In-memory active match registry — one match per user."""

    def __init__(self) -> None:
        self._matches: dict[str, ActiveMatch] = {}
        self._user_to_match: dict[uuid.UUID, str] = {}

    @property
    def active_match_count(self) -> int:
        return len(self._matches)

    def is_matched(self, user_id: uuid.UUID) -> bool:
        return user_id in self._user_to_match

    def get_match_for_user(self, user_id: uuid.UUID) -> ActiveMatch | None:
        match_id = self._user_to_match.get(user_id)
        if not match_id:
            return None
        return self._matches.get(match_id)

    def get_match_by_id(self, match_id: str) -> ActiveMatch | None:
        return self._matches.get(match_id)

    def create_match(
        self,
        *,
        user_a_id: uuid.UUID,
        user_a_username: str,
        user_a_gender: str,
        user_b_id: uuid.UUID,
        user_b_username: str,
        user_b_gender: str,
    ) -> ActiveMatch:
        if user_a_id == user_b_id:
            raise ValueError("Cannot match a user with themselves")
        if not is_valid_pair(user_a_gender, user_b_gender):
            raise ValueError("Invalid gender pairing for matchmaking")
        if user_a_id in self._user_to_match or user_b_id in self._user_to_match:
            raise ValueError("One or both users already have an active match")

        match_id = str(uuid.uuid4())
        match = ActiveMatch(
            match_id=match_id,
            user_a_id=user_a_id,
            user_a_username=user_a_username,
            user_b_id=user_b_id,
            user_b_username=user_b_username,
            created_at=datetime.now(UTC),
        )
        self._matches[match_id] = match
        self._user_to_match[user_a_id] = match_id
        self._user_to_match[user_b_id] = match_id
        return match

    def end_match(self, match_id: str) -> ActiveMatch | None:
        match = self._matches.pop(match_id, None)
        if not match:
            return None
        self._user_to_match.pop(match.user_a_id, None)
        self._user_to_match.pop(match.user_b_id, None)
        return match

    def end_match_for_user(self, user_id: uuid.UUID) -> ActiveMatch | None:
        match = self.get_match_for_user(user_id)
        if not match:
            return None
        return self.end_match(match.match_id)

    def snapshot(self) -> list[dict[str, str]]:
        return [
            {
                "match_id": match.match_id,
                "user_a_id": str(match.user_a_id),
                "user_b_id": str(match.user_b_id),
                "created_at": match.created_at.isoformat(),
            }
            for match in self._matches.values()
        ]
