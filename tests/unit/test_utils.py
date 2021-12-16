"""Module to test the utils module."""
from unittest import TestCase

from napps.kytos.flow_manager.utils import _valid_consistency_ignored, _validate_range


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
