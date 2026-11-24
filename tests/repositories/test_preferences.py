from datetime import time

import pytest

from zacretario.repositories.preferences import get_availability, update_availability
from zacretario.scheduling import Availability


def test_availability_defaults(session):
    assert get_availability(session, "juliano") == Availability(time(8), time(22), frozenset())


def test_update_availability_partial(session):
    update_availability(session, "juliano", day_start=time(7))
    update_availability(session, "juliano", blocked_weekdays={6})

    assert get_availability(session, "juliano") == Availability(time(7), time(22), frozenset({6}))


def test_update_availability_rejects_inverted_window(session):
    with pytest.raises(ValueError):
        update_availability(session, "juliano", day_start=time(23), day_end=time(7))


def test_update_availability_rejects_invalid_weekday(session):
    with pytest.raises(ValueError):
        update_availability(session, "juliano", blocked_weekdays={7})
