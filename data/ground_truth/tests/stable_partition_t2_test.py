"""T2 test suite for stable_partition.

Correct behaviour: partitions items into (true_group, false_group) where
the first element is items for which predicate returns True, the second
for which it returns False. Relative order within each group is preserved.

Introduced bug (swapped_arguments): the return statement yields
(false_group, true_group) instead of (true_group, false_group), swapping
the two partitions. The groups themselves are correctly computed; only
their order in the tuple is wrong.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_sp_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.stable_partition


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "stable_partition.py"
)
_SOURCE = _DEFAULT_SOURCE
stable_partition = _load_func(_SOURCE)


class StablePartitionCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_list(self):
        self.assertEqual(stable_partition([], lambda x: True), ([], []))

    def test_all_true(self):
        result = stable_partition([1, 2, 3], lambda x: True)
        self.assertEqual(result, ([1, 2, 3], []))

    def test_all_false(self):
        result = stable_partition([1, 2, 3], lambda x: False)
        self.assertEqual(result, ([], [1, 2, 3]))

    def test_docstring_example_evens_first(self):
        result = stable_partition([1, 2, 3, 4, 5], lambda x: x % 2 == 0)
        self.assertEqual(result, ([2, 4], [1, 3, 5]))

    def test_string_predicate(self):
        result = stable_partition(["a", "b", "c"], lambda x: x > "a")
        self.assertEqual(result, (["b", "c"], ["a"]))

    def test_relative_order_preserved(self):
        items = [3, 1, 4, 1, 5, 9, 2, 6]
        true_g, false_g = stable_partition(items, lambda x: x > 3)
        self.assertEqual(true_g, [4, 5, 9, 6])
        self.assertEqual(false_g, [3, 1, 1, 2])


class StablePartitionBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the swapped_arguments bug.

    The bug returns (false_group, true_group) instead of (true_group, false_group).
    Detectable on any asymmetric partition where the two groups differ.
    """

    def test_first_element_is_true_group(self):
        # Evens satisfy the predicate; first tuple element must be the evens
        true_g, false_g = stable_partition([1, 2, 3, 4, 5], lambda x: x % 2 == 0)
        self.assertEqual(
            true_g, [2, 4],
            msg=f"First element of result must be the true-group [2,4]; "
                f"buggy returns false-group first; got true_g={true_g}, false_g={false_g}",
        )
        self.assertEqual(
            false_g, [1, 3, 5],
            msg=f"Second element must be false-group [1,3,5]; got {false_g}",
        )

    def test_single_true_item_first(self):
        # Only [2] satisfies x > 1; it must be the first group
        true_g, false_g = stable_partition([1, 2, 1], lambda x: x > 1)
        self.assertEqual(
            true_g, [2],
            msg=f"True group should be [2]; buggy swap would give false group first; got {true_g}",
        )
        self.assertEqual(
            false_g, [1, 1],
            msg=f"False group should be [1, 1]; got {false_g}",
        )

    def test_all_true_unaffected_by_swap(self):
        # When one group is empty the swap is invisible — but groups must still be correct
        true_g, false_g = stable_partition([2, 4, 6], lambda x: x % 2 == 0)
        self.assertEqual(true_g, [2, 4, 6])
        self.assertEqual(false_g, [])


if __name__ == "__main__":
    unittest.main()
