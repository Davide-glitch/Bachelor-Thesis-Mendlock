"""Browser integration tests verifying speculative healing, rollback, and mutation guards."""
import dataclasses
import tempfile
import unittest
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
    HAVE_PW = True
except Exception:
    HAVE_PW = False

from mendlock import HealConfig, Healer, HealingPage
from mendlock.candidates import make_fingerprint
from mendlock.model import DEFAULT_MODEL_PATH, load_default_model
from mendlock.verify import attempt_click
from bench import corpus

PAGE = """<!doctype html><html><body style="font-family:sans-serif;padding:24px">
<h2>Checkout</h2><div class="actions">__BUTTONS__</div>
<div id="result" style="display:none">Order placed</div><div id="toast" style="display:none"></div>
<script>
document.addEventListener('click', function (e) {
  var el = e.target.closest('[data-act]'); if (!el) return;
  var act = el.getAttribute('data-act');
  window.localStorage.setItem('last_clicked', act);
  if (act === 'result') { document.getElementById('result').style.display = 'block'; }
  else if (act === 'post') {
    fetch('http://127.0.0.1:9/x', {method: 'POST', body: 'x', mode: 'no-cors'}).catch(function () {})
      .then(function () { document.getElementById('result').style.display = 'block'; });
  } else { var t = document.getElementById('toast'); t.textContent = act; t.style.display = 'block'; }
});
</script></body></html>"""
BTN = (
    '<button type="button" id="__ID__" data-act="__ACT__" '
    'style="padding:8px 16px;margin-right:8px;background:#2563eb;color:#fff">__LABEL__</button>'
)


def button(id_, act, label):
    return BTN.replace("__ID__", id_).replace("__ACT__", act).replace("__LABEL__", label)


def expect_result(page):
    return page.locator("#result").is_visible()


@unittest.skipUnless(HAVE_PW, "playwright not installed")
@unittest.skipUnless(DEFAULT_MODEL_PATH.exists(), "train default model first")
class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)
        cls.tmp = Path(tempfile.mkdtemp())
        cls.model = load_default_model()
        cls.BASE_BUTTONS = button("place-order", "result", "Place Order") + button("cancel", "Cancelled", "Cancel order")
        cls.CHURNED_BUTTONS = button("btn-83921", "result", "Place Order") + button("cancel-77123", "Cancelled", "Cancel order")
        cls.base = cls._write("base.html", cls.BASE_BUTTONS)
        cls.churned = cls._write("churned.html", cls.CHURNED_BUTTONS)
        cls.lookalike = cls._write(
            "lookalike.html",
            button("preview-3921", "Preview opened", "Place order preview") + button("cancel", "Cancelled", "Cancel order"),
        )
        cls.poster = cls._write("poster.html", button("go", "post", "Send"))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    @classmethod
    def _write(cls, name, buttons) -> str:
        p = cls.tmp / name
        p.write_text(PAGE.replace("__BUTTONS__", buttons), encoding="utf-8")
        return p.resolve().as_uri()

    def setUp(self):
        self.ctx = self.browser.new_context(viewport={"width": 1000, "height": 700})
        self.page = self.ctx.new_page()

    def tearDown(self):
        self.ctx.close()

    def test_wrong_attempt_rolls_back_dom_and_local_storage(self):
        self.page.goto(self.base)
        fp = make_fingerprint(self.page, "#place-order")
        self.page.goto(self.lookalike)
        self.page.evaluate("() => window.localStorage.setItem('last_clicked', 'clean')")
        model = dataclasses.replace(self.model, tau_commit=0.0)
        res = Healer(model, HealConfig(mode="verify")).heal(self.page, fp, "Place the order", expect_result)
        self.assertEqual(res.status, "REJECTED_VERIFICATION")
        self.assertFalse(self.page.locator("#toast").is_visible())
        self.assertEqual(self.page.evaluate("() => window.localStorage.getItem('last_clicked')"), "clean")

    def test_mutation_guard_blocks_post_requests(self):
        self.page.goto(self.poster)
        res = attempt_click(self.page, "#go", expect_result, guard_mutations=True)
        self.assertTrue(res.verified)
        self.assertEqual(len(res.blocked_requests), 1)


if __name__ == "__main__":
    unittest.main()