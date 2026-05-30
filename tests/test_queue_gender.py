"""Unit tests for gender-aware queue (no database)."""

import uuid

from app.matchmaking.queue_manager import QueueManager


def test_fifo_among_opposite_gender_only() -> None:
    queue = QueueManager()
    male1 = uuid.uuid4()
    male2 = uuid.uuid4()
    female1 = uuid.uuid4()

    queue.add(male1, "male1", "male")
    queue.add(male2, "male2", "male")
    queue.add(female1, "female1", "female")

    partner = queue.pop_next_compatible_partner(exclude_user_id=female1, seeker_gender="female")
    assert partner is not None
    assert partner.user_id == male1
    assert partner.gender == "male"

    partner2 = queue.pop_next_compatible_partner(exclude_user_id=uuid.uuid4(), seeker_gender="female")
    assert partner2 is not None
    assert partner2.user_id == male2


def test_same_gender_not_popped() -> None:
    queue = QueueManager()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    queue.add(user_a, "user_a", "male")
    partner = queue.pop_next_compatible_partner(exclude_user_id=user_b, seeker_gender="male")
    assert partner is None
    assert queue.size == 1


def test_self_not_matched_from_queue() -> None:
    queue = QueueManager()
    user_id = uuid.uuid4()
    queue.add(user_id, "solo", "female")
    partner = queue.pop_next_compatible_partner(exclude_user_id=user_id, seeker_gender="female")
    assert partner is None
