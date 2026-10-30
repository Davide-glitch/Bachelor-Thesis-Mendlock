"""Browser-free unit tests for Mendlock."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from mendlock import features, stats
from mendlock.candidates import Candidate, Fingerprint
from mendlock.decision import plan
from mendlock.model import Logistic, Model, choose_tau_commit
from mendlock.patcher import patch_selector
from mendlock.store import FingerprintStore
from mendlock.text import LexicalBackend


class StatsTests(unittest.TestCase):
    def test_wilson_zero_events(self):
        p, lo, hi = stats.wilson(0, 100)
        self.assertEqual((p, lo), (0.0, 0.0))
        self.assertAlmostEqual(hi, 0.037, places=3)

    def test_exact_upper_rule_of_three(self):
        self.assertAlmostEqual(stats.exact_upper(0, 100, 0.05), 1 - 0.05 ** (1 / 100), places=4)

    def test_mcnemar(self):
        self.assertEqual(stats.mcnemar_exact(0, 0), 1.0)
        self.assertAlmostEqual(stats.mcnemar_exact(10, 2), 0.0386, places=3)


class TextTests(unittest.TestCase):
    def test_lexical_orders_sensibly(self):
        s = LexicalBackend().sim("Place the order and confirm payment", ["Place Order", "Save for later", ""])
        self.assertGreater(s[0], s[1])
        self.assertEqual(s[2], 0.0)


class PatcherTests(unittest.TestCase):
    def _patch(self, src, line, old, new, apply=True):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.py"
            p.write_text(src, encoding="utf-8")
            r = patch_selector(p, line, old, new, apply=apply)
            return r, p.read_text(encoding="utf-8")

    def test_replaces_only_call_argument(self):
        src = (
            "def test_a(hp):\n"
            '    hp.click("#old", intent="x", expect=lambda p: p.locator("#old").is_visible())\n'
            "def test_b(hp):\n"
            '    hp.click("#old", intent="y")\n'
        )
        r, out = self._patch(src, 2, "#old", "#new")
        self.assertEqual(r.replaced, 1)
        self.assertIn('hp.click("#new", intent="x"', out)
        self.assertIn('p.locator("#old")', out)
        self.assertIn('hp.click("#old", intent="y")', out)
        compile(out, "t.py", "exec")


class ModelTests(unittest.TestCase):
    def test_logistic_separates(self):
        rng = np.random.default_rng(0)
        X = np.vstack([rng.normal(0, 1, (200, 3)), rng.normal(2.5, 1, (200, 3))])
        y = np.array([0] * 200 + [1] * 200)
        m = Logistic(1.0).fit(X, y)
        acc = ((m.predict_proba(X) > 0.5) == y).mean()
        self.assertGreater(acc, 0.95)
        m2 = Logistic.from_dict(m.to_dict())
        np.testing.assert_allclose(m.predict_proba(X), m2.predict_proba(X))

    def test_choose_tau_commit_respects_budget(self):
        conf = [0.99, 0.95, 0.9, 0.85, 0.6, 0.55, 0.3]
        correct = [True, True, True, False, True, False, False]
        tau = choose_tau_commit(conf, correct, alpha=0.0, floor=0.0)
        accepted = [c >= tau for c in conf]
        self.assertEqual(sum(a and not ok for a, ok in zip(accepted, correct)), 0)


def _cand(**kw):
    base = dict(
        tag="button", id="", classes=[], attrs={}, role="button", text="Go",
        bbox=[10, 10, 80, 30], visible=True, enabled=True, path=["body", "div"],
        css_path="body > button", context="", gt=False,
    )
    base.update(kw)
    return Candidate(**base)


class LeakageTests(unittest.TestCase):
    def test_ground_truth_label_never_changes_features(self):
        old = _cand(id="place-order", classes=["btn"], text="Place Order")
        fp = Fingerprint("#place-order", "/", old, [1000, 700], None)
        a = [_cand(text="Place Order", gt=False), _cand(text="Cancel", gt=True, css_path="b > c")]
        b = [_cand(text="Place Order", gt=True), _cand(text="Cancel", gt=False, css_path="b > c")]
        Xa = features.compute(fp, a, "Place the order", [None, None], LexicalBackend(), [1000, 700])
        Xb = features.compute(fp, b, "Place the order", [None, None], LexicalBackend(), [1000, 700])
        np.testing.assert_array_equal(Xa, Xb)


if __name__ == "__main__":
    unittest.main()