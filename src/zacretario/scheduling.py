from dataclasses import dataclass, field
from datetime import time


@dataclass(frozen=True)
class Availability:
    day_start: time = time(8)
    day_end: time = time(22)
    # Weekday numbers, 0 = Monday
    blocked_weekdays: frozenset[int] = field(default_factory=frozenset)
