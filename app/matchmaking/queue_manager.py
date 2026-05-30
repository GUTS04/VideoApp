import uuid
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime

from app.schemas.gender import partner_gender_for


@dataclass
class QueueEntry:
    user_id: uuid.UUID
    username: str
    gender: str
    joined_at: datetime


class QueueManager:
    """FIFO matchmaking queue with duplicate prevention and gender constraints."""

    def __init__(self) -> None:
        self._queue: deque[QueueEntry] = deque()
        self._user_ids: set[uuid.UUID] = set()

    @property
    def size(self) -> int:
        return len(self._queue)

    def is_queued(self, user_id: uuid.UUID) -> bool:
        return user_id in self._user_ids

    def add(self, user_id: uuid.UUID, username: str, gender: str) -> QueueEntry:
        if user_id in self._user_ids:
            raise ValueError("User is already in the queue")
        entry = QueueEntry(
            user_id=user_id,
            username=username,
            gender=gender,
            joined_at=datetime.now(UTC),
        )
        self._queue.append(entry)
        self._user_ids.add(user_id)
        return entry

    def remove(self, user_id: uuid.UUID) -> QueueEntry | None:
        if user_id not in self._user_ids:
            return None
        self._user_ids.discard(user_id)
        for index, entry in enumerate(self._queue):
            if entry.user_id == user_id:
                del self._queue[index]
                return entry
        return None

    def pop_next_compatible_partner(
        self,
        *,
        exclude_user_id: uuid.UUID,
        seeker_gender: str,
    ) -> QueueEntry | None:
        """
        Remove and return the first queued user with opposite gender (FIFO among valid entries).
        Skips self and same-gender candidates.
        """
        required_partner_gender = partner_gender_for(seeker_gender)
        for index, entry in enumerate(self._queue):
            if entry.user_id == exclude_user_id:
                continue
            if entry.gender != required_partner_gender:
                continue
            del self._queue[index]
            self._user_ids.discard(entry.user_id)
            return entry
        return None

    def position(self, user_id: uuid.UUID) -> int | None:
        for index, entry in enumerate(self._queue, start=1):
            if entry.user_id == user_id:
                return index
        return None

    def waiting_count_for_partner_gender(self, seeker_gender: str) -> int:
        required = partner_gender_for(seeker_gender)
        return sum(1 for entry in self._queue if entry.gender == required)

    def snapshot(self) -> list[dict[str, str]]:
        return [
            {
                "user_id": str(entry.user_id),
                "username": entry.username,
                "gender": entry.gender,
                "joined_at": entry.joined_at.isoformat(),
            }
            for entry in self._queue
        ]
