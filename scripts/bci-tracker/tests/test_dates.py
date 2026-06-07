from datetime import date

from bci_tracker.dates import compute_window, to_local_date


def test_compute_window_uses_local_business_date():
    window = compute_window("Asia/Shanghai", 7, today=date(2026, 6, 5))
    assert window.start == date(2026, 5, 29)
    assert window.end == date(2026, 6, 5)
    assert window.padded_start == date(2026, 5, 28)
    assert window.padded_end == date(2026, 6, 6)


def test_compute_window_supports_same_day_window():
    window = compute_window("Asia/Shanghai", 0, today=date(2026, 6, 5))
    assert window.start == date(2026, 6, 5)
    assert window.end == date(2026, 6, 5)


def test_to_local_date_converts_utc_boundary():
    assert to_local_date("2026-06-04T18:00:00Z", "Asia/Shanghai").isoformat() == "2026-06-05"
