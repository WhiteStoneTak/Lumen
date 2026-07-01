"""Unit tests for src/experiment/score_t3_difficulty.py (W-04).

Covers tiering, the difficulty-weighted quality math, an end-to-end run of the
reference implementation (-> quality 1.0), the *controlled de-saturation* proof
(a candidate that passes the whole visible suite but fails a hidden check scores
< 1.0 while the frozen scorer would give 1.0), and metamorphic self-consistency
of every authored hidden module.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment import score_t3_difficulty as m  # noqa: E402

TESTS_DIR = ROOT / "data" / "ground_truth" / "tests"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestTiering(unittest.TestCase):
    def test_base_vs_edge(self):
        self.assertEqual(m._tier_of("mod.Cls.test_basic_case"), "base")
        self.assertEqual(m._tier_of("mod.Cls.test_empty_input"), "edge")
        self.assertEqual(m._tier_of("mod.Cls.test_raises_on_bad"), "edge")
        self.assertEqual(m._tier_of("mod.Cls.test_large_negative"), "edge")


class TestComputeQuality(unittest.TestCase):
    def test_weighting_math(self):
        driver_out = {
            "per_test": {
                "m.C.test_basic": True,      # base pass
                "m.C.test_empty": False,     # edge fail
            },
            "hidden": {"passed": 1, "total": 2},
            "meta": {"passed": 1, "total": 1},
        }
        q = m.compute_quality(driver_out)
        # base: 1/1 (w1), edge: 0/1 (w2), adversarial: 2/3 (w3)
        # wp = 1*1 + 0*2 + 2*3 = 7 ; wt = 1*1 + 1*2 + 3*3 = 12
        self.assertAlmostEqual(q["difficulty_quality"], 7 / 12, places=6)
        # frozen-equivalent = visible pass fraction = 1/2
        self.assertAlmostEqual(q["frozen_equiv_fraction"], 0.5, places=6)
        self.assertTrue(q["has_adversarial"])

    def test_all_pass_is_one(self):
        driver_out = {
            "per_test": {"a.b.test_x": True, "a.b.test_empty": True},
            "hidden": {"passed": 3, "total": 3},
            "meta": {"passed": 2, "total": 2},
        }
        self.assertEqual(m.compute_quality(driver_out)["difficulty_quality"], 1.0)


class TestReferenceScoresOne(unittest.TestCase):
    """The authored reference implementation must score a perfect quality."""

    def test_rotate_list_reference_is_one(self):
        hid = _load_module("_hid_rotate", m.HIDDEN_DIR / "rotate_list.py")
        import inspect

        src = inspect.getsource(hid.reference).replace("def reference(", "def rotate_list(")
        out = m.run_difficulty(src, "rotate_list",
                               TESTS_DIR / "rotate_list_t3_test.py",
                               m.HIDDEN_DIR / "rotate_list.py")
        self.assertNotIn("error", out)
        q = m.compute_quality(out)
        self.assertEqual(q["frozen_equiv_fraction"], 1.0)
        self.assertEqual(q["difficulty_quality"], 1.0)


class TestControlledDeSaturation(unittest.TestCase):
    """The instrument must pull a visible-passing but hidden-failing candidate < 1.0."""

    def test_strided_windows_ignore_partial(self):
        # Correct reversal, but ignores include_partial=True. The visible suite
        # never exercises include_partial, so the frozen scorer would give 1.0;
        # a hidden input probes it and the difficulty quality drops below 1.0.
        candidate = (
            "def strided_windows(items, size, stride, include_partial=False):\n"
            "    r = []\n    n = len(items)\n    i = 0\n"
            "    while i + size <= n:\n"
            "        r.append(list(items[i:i + size]))\n        i += stride\n"
            "    return r[::-1]\n"
        )
        out = m.run_difficulty(candidate, "strided_windows",
                               TESTS_DIR / "strided_windows_t3_test.py",
                               m.HIDDEN_DIR / "strided_windows.py")
        self.assertNotIn("error", out)
        q = m.compute_quality(out)
        self.assertEqual(q["frozen_equiv_fraction"], 1.0)   # passes ALL visible tests
        self.assertLess(q["difficulty_quality"], 1.0)       # but not the hidden layer


class TestMetamorphicSelfConsistency(unittest.TestCase):
    """Every relation must hold for its own reference, and the reference must
    pass the existing visible T3 suite."""

    def test_all_modules(self):
        for path in sorted(m.HIDDEN_DIR.glob("*.py")):
            fn = path.stem
            with self.subTest(func=fn):
                hid = _load_module(f"_hid_{fn}", path)
                ref = hid.reference
                # metamorphic relations hold for the reference
                for rel in getattr(hid, "METAMORPHIC", []):
                    self.assertTrue(rel(ref), f"{fn}:{rel.__name__} failed on reference")
                # reference passes the visible suite when one exists
                test_path = TESTS_DIR / f"{fn}_t3_test.py"
                if test_path.exists():
                    tmod = _load_module(f"_suite_{fn}", test_path)
                    setattr(tmod, fn, ref)
                    for attr in dir(tmod):
                        obj = getattr(tmod, attr)
                        if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
                            for mn in obj.__dict__:
                                meth = getattr(obj, mn, None)
                                if (callable(meth) and hasattr(meth, "__func__")
                                        and fn in meth.__func__.__globals__):
                                    meth.__func__.__globals__[fn] = ref
                    suite = unittest.TestLoader().loadTestsFromModule(tmod)
                    res = unittest.TextTestRunner(verbosity=0, stream=io.StringIO()).run(suite)
                    self.assertTrue(res.wasSuccessful(),
                                    f"{fn} reference fails its visible T3 suite")


if __name__ == "__main__":
    unittest.main()
