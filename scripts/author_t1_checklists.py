"""Author the 30 confirmatory T1 property checklists (R5-1 / WOV-245).

Ground-truth checklists for the T1 (program-understanding) confirmatory study.
Each checklist is a `t1-checklist-v1` artifact: a list of objective, verifiable
properties of the canonical (correct) function, derived solely from its source
and docstring. The held-out pilot anchors (clamp, count_vowels, is_sorted) are
NOT re-authored here — they stay segregated from the confirmatory set.

Authoring constraints (so the deterministic R1-3 matcher behaves):
  * Each statement carries >= 2 distinctive anchor terms (parameter names, type
    names, domain nouns, multi-digit numbers, return structure) that a correct
    description naturally contains. The matcher requires min(2, n_terms) anchors
    present at a word boundary and not locally negated.
  * Properties span the four categories {inputs, outputs, behavior, edge_case}.
  * Target P in [7, 9] to preserve the anti-ceiling resolution argument
    (R1-3 §4): per-function attainable levels = P + 1 >= 8.

source_hash is the SHA-256 of the raw source file, matching the manifest's
`source_hash` (lineage.t1_source_hash). Frozen at the R5-1 commit; collection
(R5-2) happens strictly afterward, so git history proves prereg-before-data.

Run: PYTHONPATH=src python3 scripts/author_t1_checklists.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from utils.hash import hash_content  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "functions" / "raw"
OUT = REPO / "data" / "ground_truth" / "checklists"

# func_id -> list of (category, required, statement)
CHECKLISTS: dict[str, list[tuple[str, bool, str]]] = {
    "remove_adjacent_dups": [
        ("inputs", True, "Accepts a single parameter named items, annotated as a list."),
        ("outputs", True, "Returns a new list; the original input is left unchanged rather than mutated in place."),
        ("behavior", True, "Consecutive (adjacent) equal values are collapsed into a single occurrence."),
        ("behavior", True, "Non-adjacent duplicate values are preserved; only adjacent repeats are removed."),
        ("behavior", True, "The relative order of the retained elements is maintained."),
        ("edge_case", True, "An empty input list returns an empty list."),
        ("edge_case", True, "A single-element list is returned unchanged with its one element."),
        ("behavior", False, "Comparison uses equality, so the first element of each adjacent run is the one kept."),
    ],
    "batch_list": [
        ("inputs", True, "Accepts two parameters: items (a list) and batch_size (an int)."),
        ("outputs", True, "Returns a list of lists, each inner list being one consecutive batch."),
        ("behavior", True, "Each batch contains at most batch_size elements taken in order."),
        ("behavior", True, "The final batch may be smaller when len(items) is not divisible by batch_size."),
        ("behavior", True, "Batches are non-overlapping and cover the items left to right."),
        ("edge_case", True, "Returns an empty list when items is empty."),
        ("edge_case", True, "Returns an empty list when batch_size is less than 1."),
    ],
    "sliding_window_max": [
        ("inputs", True, "Accepts two parameters: nums (a list) and k (the window size, an int)."),
        ("outputs", True, "Returns a list containing the maximum of each window."),
        ("behavior", True, "Each window covers k consecutive elements and slides one position at a time."),
        ("behavior", True, "The output length is len(nums) - k + 1 for valid k."),
        ("edge_case", True, "Returns an empty list when nums is empty."),
        ("edge_case", True, "Returns an empty list when k is less than 1."),
        ("edge_case", True, "Returns an empty list when k is greater than len(nums)."),
    ],
    "rle_encode": [
        ("inputs", True, "Accepts a single parameter named items, a list."),
        ("outputs", True, "Returns a list of (value, count) pairs (tuples)."),
        ("behavior", True, "Consecutive equal values are collapsed into one (value, count) tuple."),
        ("behavior", True, "Non-consecutive duplicate values produce separate tuples."),
        ("behavior", True, "The order of first appearance of each run is preserved."),
        ("behavior", True, "The count records how many times the value repeats consecutively."),
        ("edge_case", True, "Returns an empty list for empty input."),
        ("edge_case", False, "A single element yields one tuple with count equal to 1."),
    ],
    "count_true_segments": [
        ("inputs", True, "Accepts a single parameter named flags, a list of booleans."),
        ("outputs", True, "Returns an int, the number of contiguous True segments."),
        ("behavior", True, "A segment is a maximal consecutive run of True values."),
        ("behavior", True, "Each maximal run of True increments the count once."),
        ("edge_case", True, "Returns 0 for an empty list."),
        ("edge_case", True, "Returns 0 when every flag is False."),
        ("behavior", False, "A False value ends the current segment so later True values start a new one."),
    ],
    "merge_sorted": [
        ("inputs", True, "Accepts two parameters a and b, both lists sorted in ascending order."),
        ("outputs", True, "Returns one list containing all elements from both inputs."),
        ("behavior", True, "The returned list is sorted in ascending order."),
        ("behavior", True, "Duplicate values across a and b are all preserved."),
        ("behavior", True, "Uses a two-pointer merge advancing through a and b."),
        ("edge_case", True, "When one input is empty the other list's elements are returned in order."),
        ("behavior", False, "Equal elements keep a's value before b's because the comparison uses a[i] <= b[j]."),
    ],
    "first_index_of_max": [
        ("inputs", True, "Accepts a single parameter named nums, a list."),
        ("outputs", True, "Returns an int, the index of the maximum value."),
        ("behavior", True, "Returns the lowest index when the maximum value occurs multiple times."),
        ("behavior", True, "Scans left to right and only updates on a strictly greater value."),
        ("edge_case", True, "Raises ValueError when nums is empty."),
        ("edge_case", True, "Returns 0 when all elements are equal."),
        ("behavior", False, "The index is 0-based."),
    ],
    "rotate_list": [
        ("inputs", True, "Accepts two parameters: items (a list) and k (an int shift amount)."),
        ("outputs", True, "Returns a new list rotated left by k positions."),
        ("behavior", True, "The element at index k becomes the new first element."),
        ("behavior", True, "k is taken modulo len(items), so any integer is valid."),
        ("edge_case", True, "Returns an empty list when items is empty."),
        ("edge_case", True, "Returns a copy unchanged when k modulo the length is 0."),
        ("behavior", False, "Rotation is to the left, equivalent to items[k:] concatenated with items[:k]."),
    ],
    "max_subarray_bounds": [
        ("inputs", True, "Accepts a single parameter named nums, a list of integers."),
        ("outputs", True, "Returns a tuple (start, end, total) of the maximum-sum contiguous subarray."),
        ("behavior", True, "Both start and end indices are inclusive and 0-based."),
        ("behavior", True, "Uses a modified Kadane's algorithm over the array."),
        ("behavior", True, "On ties for maximum sum, returns the subarray that starts earliest."),
        ("edge_case", True, "Returns (0, 0, 0) when nums is empty."),
        ("edge_case", True, "When all values are negative, returns the single largest element."),
    ],
    "longest_plateau": [
        ("inputs", True, "Accepts a single parameter named nums, a list of comparable elements."),
        ("outputs", True, "Returns a tuple (start, end, value) describing the longest run of equal elements."),
        ("behavior", True, "start and end are inclusive 0-based indices of the run."),
        ("behavior", True, "A plateau is a run of consecutive equal elements."),
        ("behavior", True, "On ties for longest, returns the run that starts earliest."),
        ("edge_case", True, "Returns (-1, -1, None) when nums is empty."),
        ("edge_case", False, "A single-element list yields (0, 0, value) for that element."),
    ],
    "group_and_aggregate": [
        ("inputs", True, "Accepts a single parameter named pairs, a list of (key, value) tuples."),
        ("outputs", True, "Returns a dict mapping each key to a stats dict."),
        ("behavior", True, "For each key it computes count, sum, min, and max of its values."),
        ("behavior", True, "Keys appear in insertion order of first appearance."),
        ("edge_case", True, "Returns an empty dict for empty input."),
        ("behavior", True, "Repeated keys accumulate into the same group rather than overwriting."),
        ("outputs", False, "count is an int while sum, min, and max reflect the numeric values."),
    ],
    "two_sum_sorted_pairs": [
        ("inputs", True, "Accepts two parameters: nums (a sorted list of integers) and target (an int)."),
        ("outputs", True, "Returns a list of (a, b) tuples where a + b equals target."),
        ("behavior", True, "Uses a two-pointer approach from both ends of the sorted list."),
        ("behavior", True, "Each returned pair satisfies a <= b."),
        ("behavior", True, "Duplicate value pairs are returned only once (unique pairs)."),
        ("behavior", True, "Pairs are ordered by ascending first element."),
        ("edge_case", True, "Returns an empty list when no pair sums to target."),
    ],
    "top_k_by": [
        ("inputs", True, "Accepts items, k, a primary key callable, and an optional tiebreak_key callable."),
        ("outputs", True, "Returns a list of at most k items ordered best to worst."),
        ("behavior", True, "Items are sorted by key descending (higher key ranks higher)."),
        ("behavior", True, "When primary keys tie and tiebreak_key is given, it sorts ascending by that secondary key."),
        ("behavior", True, "Ties are broken stably, preserving original order when keys are equal."),
        ("edge_case", True, "Returns an empty list when k is less than or equal to 0."),
        ("edge_case", True, "Returns fewer than k items when len(items) is smaller than k."),
    ],
    "tokenize_arithmetic": [
        ("inputs", True, "Accepts a single parameter named expr, a string arithmetic expression."),
        ("outputs", True, "Returns a list of (type, value) tuples in left-to-right order."),
        ("behavior", True, "Recognizes NUM tokens for integer or decimal numbers."),
        ("behavior", True, "Recognizes OP tokens for the operators plus, minus, star, and slash."),
        ("behavior", True, "Recognizes LPAREN and RPAREN tokens for parentheses."),
        ("behavior", True, "Whitespace between tokens is ignored."),
        ("edge_case", True, "A leading minus is treated as an OP, not part of a negative number."),
        ("behavior", False, "Multi-digit and decimal numbers are kept together as one NUM token."),
    ],
    "spiral_order": [
        ("inputs", True, "Accepts a single parameter named matrix, a list of equal-length rows."),
        ("outputs", True, "Returns a flat list of elements in clockwise spiral order."),
        ("behavior", True, "Traversal goes right, then down, then left, then up, repeating inward."),
        ("behavior", True, "Traversal starts at the top-left element."),
        ("edge_case", True, "Returns an empty list when the matrix is empty."),
        ("edge_case", True, "Returns an empty list when the matrix has zero columns."),
        ("behavior", False, "Each element of the matrix appears exactly once in the output."),
    ],
    "welford_running_stats": [
        ("inputs", True, "Accepts a single parameter named values, a list of floats."),
        ("outputs", True, "Returns a list of (count, mean, variance) tuples, one per input value."),
        ("behavior", True, "Uses Welford's online algorithm to update statistics incrementally."),
        ("behavior", True, "variance is the population variance, divided by count rather than count minus 1."),
        ("behavior", True, "count is 1-indexed and increases by one at each step."),
        ("edge_case", True, "Returns an empty list when values is empty."),
        ("edge_case", True, "variance at count 1 is 0.0."),
    ],
    "merge_intervals": [
        ("inputs", True, "Accepts a single parameter named intervals, a list of [start, end] pairs."),
        ("outputs", True, "Returns a list of merged, non-overlapping [start, end] intervals."),
        ("behavior", True, "Overlapping intervals are merged into one spanning interval."),
        ("behavior", True, "The result is sorted by start."),
        ("behavior", True, "Adjacent touching intervals are also merged."),
        ("edge_case", True, "Returns an empty list when intervals is empty."),
        ("behavior", False, "Intervals are first sorted by start before merging."),
    ],
    "equal_width_buckets": [
        ("inputs", True, "Accepts values (a non-empty list of floats) and n_buckets (an int >= 1)."),
        ("outputs", True, "Returns a list of 0-indexed bucket indices, one per value."),
        ("behavior", True, "Buckets have equal width computed from the min and max of values."),
        ("behavior", True, "A value equal to max_val always goes in the last bucket."),
        ("behavior", True, "The output order matches the input order of values."),
        ("edge_case", True, "When all values are equal, every value goes in bucket 0."),
        ("behavior", False, "The last bucket is inclusive on both ends."),
    ],
    "dense_rank": [
        ("inputs", True, "Accepts a single parameter named values, a list of numbers."),
        ("outputs", True, "Returns a list of integer ranks in the same order as the input."),
        ("behavior", True, "Ranks are 1-based (dense ranking)."),
        ("behavior", True, "Tied values receive the same rank."),
        ("behavior", True, "The next distinct value increases the rank by 1, not by the count of ties."),
        ("edge_case", True, "Returns an empty list when values is empty."),
        ("behavior", False, "Ranks correspond to the ascending order of distinct values."),
    ],
    "chunk_on_change": [
        ("inputs", True, "Accepts items and an optional key callable."),
        ("outputs", True, "Returns a list of non-empty sublists (chunks)."),
        ("behavior", True, "A new chunk starts each time the key value changes between consecutive items."),
        ("behavior", True, "Consecutive items with the same key are grouped into one chunk."),
        ("behavior", True, "When key is None, the item itself is used as the key."),
        ("edge_case", True, "Returns an empty list when items is empty."),
        ("behavior", False, "Each input item appears in exactly one chunk, preserving order."),
    ],
    "antidiagonals": [
        ("inputs", True, "Accepts a single parameter named matrix, a list of equal-length rows."),
        ("outputs", True, "Returns a list of antidiagonals, each itself a list of elements."),
        ("behavior", True, "Antidiagonals run from top-right toward bottom-left."),
        ("behavior", True, "The first antidiagonal contains matrix[0][0]."),
        ("behavior", True, "Within each antidiagonal, elements are ordered by increasing row index."),
        ("edge_case", True, "Returns an empty list when the matrix is empty."),
        ("behavior", False, "There are rows + cols - 1 antidiagonals in total."),
    ],
    "camel_to_snake": [
        ("inputs", True, "Accepts a single parameter named name, a camelCase or PascalCase string."),
        ("outputs", True, "Returns the snake_case version of the identifier."),
        ("behavior", True, "An underscore is inserted before an uppercase letter that follows a lowercase letter or digit."),
        ("behavior", True, "All characters are converted to lowercase."),
        ("behavior", True, "Abbreviations like XMLParser become xml_parser."),
        ("behavior", True, "No leading or trailing underscores are added."),
        ("edge_case", True, "An empty string is returned unchanged."),
    ],
    "find_balanced_spans": [
        ("inputs", True, "Accepts a string s and the open_char and close_char bracket characters."),
        ("outputs", True, "Returns a list of (start, end) index tuples."),
        ("behavior", True, "Each span covers an outermost balanced pair from open_char to its matching close_char."),
        ("behavior", True, "Nested brackets are not reported separately, only the outermost span."),
        ("behavior", True, "Unmatched brackets are ignored."),
        ("behavior", True, "Spans are returned in order of appearance."),
        ("edge_case", True, "Returns an empty list when there are no balanced pairs."),
    ],
    "frequency_table": [
        ("inputs", True, "Accepts a single parameter named values, a list of hashable items."),
        ("outputs", True, "Returns a list of (value, count, cumulative_fraction) tuples."),
        ("behavior", True, "The result is sorted by value ascending."),
        ("behavior", True, "count is the number of occurrences of each value."),
        ("behavior", True, "cumulative_fraction is the running sum of counts divided by the total length."),
        ("edge_case", True, "Returns an empty list for empty input."),
        ("outputs", False, "The final cumulative_fraction equals 1.0."),
    ],
    "sorted_list_intersection": [
        ("inputs", True, "Accepts two parameters a and b, both sorted lists of integers."),
        ("outputs", True, "Returns a sorted list, the multiset intersection of a and b."),
        ("behavior", True, "Each value appears min(count_in_a, count_in_b) times."),
        ("behavior", True, "Uses a two-pointer walk advancing through both sorted lists."),
        ("edge_case", True, "Returns an empty list when there are no common values."),
        ("edge_case", True, "Returns an empty list when either input is empty."),
        ("behavior", False, "Duplicate counts are preserved up to the smaller multiplicity."),
    ],
    "strided_windows": [
        ("inputs", True, "Accepts items, size, stride, and a boolean include_partial flag."),
        ("outputs", True, "Returns a list of windows, each a list of items."),
        ("behavior", True, "Windows start at indices 0, stride, 2*stride, and so on."),
        ("behavior", True, "Each full window has size elements."),
        ("behavior", True, "When include_partial is True, a shorter trailing window may be included."),
        ("behavior", True, "When include_partial is False, only full-sized windows are returned."),
        ("edge_case", False, "include_partial defaults to False."),
    ],
    "peak_valley_indices": [
        ("inputs", True, "Accepts a single parameter named nums, a list of numbers."),
        ("outputs", True, "Returns a list of (label, index) tuples labeled peak or valley."),
        ("behavior", True, "A strict local peak is greater than both neighbors."),
        ("behavior", True, "A strict local valley is less than both neighbors."),
        ("behavior", True, "Boundary elements at index 0 and the last index are never peaks or valleys."),
        ("behavior", True, "Results are returned in ascending index order."),
        ("edge_case", True, "Plateaus are excluded; a list shorter than 3 elements yields an empty list."),
    ],
    "segments_above_threshold": [
        ("inputs", True, "Accepts nums (a list of floats) and threshold (a float lower bound)."),
        ("outputs", True, "Returns a list of sublists, each a contiguous segment above threshold."),
        ("behavior", True, "Each segment is a maximal run of values strictly greater than threshold."),
        ("behavior", True, "Values less than or equal to threshold break a segment."),
        ("behavior", True, "The order of segments follows their order in nums."),
        ("edge_case", True, "Returns an empty list when no element exceeds threshold."),
        ("behavior", False, "The comparison is strict, so a value equal to threshold is excluded."),
    ],
    "stable_partition": [
        ("inputs", True, "Accepts items and a predicate callable returning a bool."),
        ("outputs", True, "Returns a tuple (true_group, false_group) of two lists."),
        ("behavior", True, "Items for which predicate returns True go in the first group."),
        ("behavior", True, "The remaining items go in the false_group."),
        ("behavior", True, "Relative order within each group is preserved (stable)."),
        ("edge_case", True, "Returns two empty lists when items is empty."),
        ("behavior", False, "Every input item appears in exactly one of the two groups."),
    ],
    "group_by_key": [
        ("inputs", True, "Accepts a single parameter named pairs, a list of (key, value) tuples."),
        ("outputs", True, "Returns a dict mapping each key to a list of its values."),
        ("behavior", True, "Values within each key group preserve their original relative order."),
        ("behavior", True, "Keys maintain insertion order of first appearance."),
        ("behavior", True, "Repeated keys append to the same list rather than overwriting."),
        ("edge_case", True, "Returns an empty dict for empty input."),
        ("edge_case", False, "A single pair yields one key mapping to a one-element list."),
    ],
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    written = 0
    p_counts = {}
    for func_id, props in CHECKLISTS.items():
        raw_path = RAW / f"{func_id}.py"
        if not raw_path.exists():
            raise SystemExit(f"missing raw source: {raw_path}")
        source_hash = hash_content(raw_path.read_text(encoding="utf-8"))
        properties = []
        for i, (category, required, statement) in enumerate(props, start=1):
            properties.append({
                "property_id": f"{func_id}.P{i:02d}",
                "category": category,
                "statement": statement,
                "required": required,
            })
        checklist = {
            "lumen_schema": "t1-checklist-v1",
            "func_id": func_id,
            "source_hash": source_hash,
            "authored_for": "R5-1 confirmatory T1 (WOV-245)",
            "properties": properties,
        }
        (OUT / f"{func_id}.json").write_text(
            json.dumps(checklist, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written += 1
        p_counts[func_id] = len(properties)
    print(f"wrote {written} checklists to {OUT.relative_to(REPO)}")
    import statistics
    vals = list(p_counts.values())
    print(f"P distribution: min={min(vals)} max={max(vals)} mean={statistics.mean(vals):.2f}")
    from collections import Counter
    print("P counts:", dict(sorted(Counter(vals).items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
