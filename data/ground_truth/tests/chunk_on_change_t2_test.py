"""T2 test suite for chunk_on_change.

Correct behaviour: splits items into maximal runs of consecutive equal-key
items. When the key changes, a new chunk is started and current_key is
updated to the new item's key.

Introduced bug (incorrect_variable_reference): when a new chunk is started
on a key change, `current_key` is never updated to the new item's key. This
causes any run of three or more distinct consecutive keys to merge incorrectly
because later items are still compared against the original key.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_coc_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.chunk_on_change


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "chunk_on_change.py"
)
_SOURCE = _DEFAULT_SOURCE
chunk_on_change = _load_func(_SOURCE)


class ChunkOnChangeCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_empty(self):
        self.assertEqual(chunk_on_change([]), [])

    def test_single_item(self):
        self.assertEqual(chunk_on_change([1]), [[1]])

    def test_all_same(self):
        self.assertEqual(chunk_on_change([1, 1, 1]), [[1, 1, 1]])

    def test_two_distinct_groups(self):
        self.assertEqual(chunk_on_change([1, 1, 2, 2]), [[1, 1], [2, 2]])

    def test_example_from_docstring(self):
        self.assertEqual(
            chunk_on_change([1, 1, 2, 2, 1, 3]),
            [[1, 1], [2, 2], [1], [3]],
        )

    def test_with_key_function(self):
        result = chunk_on_change(["ab", "ac", "b", "bc"], key=lambda s: s[0])
        self.assertEqual(result, [["ab", "ac"], ["b", "bc"]])


class ChunkOnChangeBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the incorrect_variable_reference bug.

    The buggy version never updates current_key after starting a new chunk.
    After the first key-change, all subsequent items are compared against the
    original key, causing wrong splits for inputs with 3+ distinct consecutive keys.
    """

    def test_three_distinct_keys_produces_three_chunks(self):
        # [1, 2, 3]: after switching to 2, current_key stays 1 in buggy version;
        # 3 != 1 (stale key), so a new chunk is started each time — happens to be
        # correct here. The real failure is with repeated third-group items.
        result = chunk_on_change([1, 2, 3])
        self.assertEqual(
            result, [[1], [2], [3]],
            msg=f"Expected [[1],[2],[3]] but got {result}",
        )

    def test_three_groups_third_has_repeat(self):
        # [1, 2, 2, 3, 3]: after switching to '2', current_key stays '1'.
        # second '2' compares '2' != '1' (stale) -> starts yet another chunk
        # so buggy: [[1],[2],[2],[3],[3]] instead of [[1],[2,2],[3,3]]
        result = chunk_on_change([1, 2, 2, 3, 3])
        self.assertEqual(
            result, [[1], [2, 2], [3, 3]],
            msg=f"Expected [[1],[2,2],[3,3]] but got {result}; "
                "buggy version splits consecutive equal items after first key-change",
        )

    def test_two_changes_with_repeated_second_key(self):
        # [5, 7, 7]: after switching to 7, buggy current_key stays 5;
        # second 7 != 5 (stale) -> starts a new chunk
        result = chunk_on_change([5, 7, 7])
        self.assertEqual(
            result, [[5], [7, 7]],
            msg=f"Expected [[5],[7,7]] but got {result}; "
                "buggy version incorrectly splits the run of 7s",
        )
