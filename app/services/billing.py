"""Call billing calculations. Backend is the source of truth."""

from math import ceil

# 100 coins = 35 minutes
COINS_PER_PACKAGE = 100
MINUTES_PER_PACKAGE = 35
SECONDS_PER_PACKAGE = MINUTES_PER_PACKAGE * 60


def coins_for_duration_seconds(duration_seconds: int) -> int:
    """Billable coins for a duration (rounded up to whole coins)."""
    if duration_seconds <= 0:
        return 0
    return ceil(duration_seconds * COINS_PER_PACKAGE / SECONDS_PER_PACKAGE)


def coins_per_minute() -> float:
    return COINS_PER_PACKAGE / MINUTES_PER_PACKAGE
