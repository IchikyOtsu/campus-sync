from datetime import UTC, datetime


def overlaps(a_start, a_end, b_start, b_end): return a_start < b_end and b_start < a_end
def test_overlap_and_no_false_conflict():
    t = UTC
    assert overlaps(datetime(2026,9,23,10,tzinfo=t), datetime(2026,9,23,12,tzinfo=t), datetime(2026,9,23,10,30,tzinfo=t), datetime(2026,9,23,12,30,tzinfo=t))
    assert not overlaps(datetime(2026,9,23,10,tzinfo=t), datetime(2026,9,23,12,tzinfo=t), datetime(2026,9,23,12,tzinfo=t), datetime(2026,9,23,13,tzinfo=t))
