"""T2 test suite for group_by_key.

Correct behaviour: groups a list of (key, value) pairs into a dict mapping
each key to the list of associated values, preserving insertion order and
relative order within each group.

Introduced bug (incorrect_variable_reference): the append call uses `key`
instead of `value` — `result[key].append(key)` — so each group's value list
is populated with the key itself repeated rather than the actual values.
The bug is invisible when key == value; it is exposed on any input where
key != value.
"""

import unittest
from pathlib import Path


def _load_func(source_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_gbk_mod", source_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.group_by_key


_DEFAULT_SOURCE = str(
    Path(__file__).resolve().parents[2] / "functions" / "raw" / "group_by_key.py"
)
_SOURCE = _DEFAULT_SOURCE
group_by_key = _load_func(_SOURCE)


class GroupByKeyCorrectBehaviourTests(unittest.TestCase):
    """These tests all pass against the correct source."""

    def test_empty_returns_empty_dict(self):
        self.assertEqual(group_by_key([]), {})

    def test_single_pair(self):
        self.assertEqual(group_by_key([("x", 10)]), {"x": [10]})

    def test_multi_key_single_values(self):
        result = group_by_key([("a", 1), ("b", 2), ("c", 3)])
        self.assertEqual(result, {"a": [1], "b": [2], "c": [3]})

    def test_insertion_order_preserved(self):
        result = group_by_key([("b", 2), ("a", 1), ("c", 3)])
        self.assertEqual(list(result.keys()), ["b", "a", "c"])

    def test_repeated_keys_collect_all_values(self):
        result = group_by_key([("a", 1), ("b", 2), ("a", 3), ("c", 1), ("b", 4)])
        self.assertEqual(result, {"a": [1, 3], "b": [2, 4], "c": [1]})

    def test_relative_order_within_group_preserved(self):
        result = group_by_key([("k", 10), ("k", 20), ("k", 30)])
        self.assertEqual(result["k"], [10, 20, 30])


class GroupByKeyBugDetectionTests(unittest.TestCase):
    """These tests specifically expose the incorrect_variable_reference bug.

    The bug appends `key` instead of `value` into result[key]. Any input
    where key != value will produce a list of keys instead of values.
    """

    def test_values_are_not_keys_single_group(self):
        # key="a", values=[1,2,3] — buggy returns {"a":["a","a","a"]}
        result = group_by_key([("a", 1), ("a", 2), ("a", 3)])
        self.assertEqual(
            result["a"], [1, 2, 3],
            msg=f"Expected values [1, 2, 3] for key 'a' but got {result.get('a')}; "
                "buggy version appends the key instead of the value",
        )

    def test_values_are_not_keys_multiple_groups(self):
        result = group_by_key([("x", 10), ("y", 20), ("x", 30)])
        self.assertEqual(result["x"], [10, 30],
                         msg=f"group 'x' should be [10, 30], got {result.get('x')}")
        self.assertEqual(result["y"], [20],
                         msg=f"group 'y' should be [20], got {result.get('y')}")

    def test_value_type_differs_from_key_type(self):
        result = group_by_key([(1, "one"), (2, "two"), (1, "uno")])
        self.assertEqual(result[1], ["one", "uno"],
                         msg=f"Expected ['one','uno'] but got {result.get(1)}")
        self.assertEqual(result[2], ["two"],
                         msg=f"Expected ['two'] but got {result.get(2)}")


if __name__ == "__main__":
    unittest.main()
