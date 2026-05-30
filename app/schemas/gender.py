from enum import StrEnum


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


def partner_gender_for(gender: str) -> str:
    """Return the only valid partner gender for matchmaking."""
    if gender == Gender.MALE:
        return Gender.FEMALE
    if gender == Gender.FEMALE:
        return Gender.MALE
    raise ValueError(f"Unsupported gender: {gender!r}")


def is_valid_pair(gender_a: str, gender_b: str) -> bool:
    return gender_a != gender_b and {gender_a, gender_b} == {Gender.MALE, Gender.FEMALE}
