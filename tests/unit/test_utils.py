"""Module to test the utils module."""
from datetime import timedelta
from unittest import TestCase

from napps.kytos.flow_manager.utils import (
    _valid_consistency_ignored,
    _validate_range,
    get_min_wait_diff,
)


class TestUtils(TestCase):
    """Test Utils."""

    def test_validate_range_exceptions(self):
        """Test _validate_range exceptions."""

        test_data = [((1,), ValueError), ((2, 1), ValueError), ((1, "1"), TypeError)]
        for values, exception in test_data:
            with self.subTest(values=values, exception=exception):

                with self.assertRaises(exception) as exc:
                    _validate_range(values)

                assert str(exc)

    def test_valid_consistency_ignored_false_cases(self):
        """Test _valid_consistency_ignored False cases."""

        test_data = [[(1,)], ["2"]]
        for values in test_data:
            with self.subTest(values=values):
                assert not _valid_consistency_ignored(values)

    def test_get_min_wait_diff_early_return(self):
        """Test get_min_wait diff early return."""
        test_data = [(1, 2, 3), (3, 4, 0)]
        for dt_t2, dt_t1, min_wait in test_data:
            with self.subTest(dt_t2=dt_t2, dt_t1=dt_t1, min_wait=min_wait):
                assert get_min_wait_diff(dt_t2, dt_t1, min_wait) == 0

    def test_get_min_wait_diff(self):
        """Test get_min_wait diff values."""
        test_data = [
            (timedelta(seconds=8), timedelta(seconds=2), 4),
            (timedelta(seconds=8), timedelta(seconds=2), 6),
        ]
        for dt_t2, dt_t1, min_wait in test_data:
            with self.subTest(dt_t2=dt_t2, dt_t1=dt_t1, min_wait=min_wait):
                assert (
                    get_min_wait_diff(dt_t2, dt_t1, min_wait)
                    == (dt_t2 - dt_t1).total_seconds() - min_wait
                )
