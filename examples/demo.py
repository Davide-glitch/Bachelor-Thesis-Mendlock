"""End-to-end demonstration of Mendlock recording, speculative healing, and AST patching."""
import runpy
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from mendlock import HealConfig, HealingPage
from bench import corpus

TEST_SRC = '''\
def run(hp, page, base_url, mutated_url, expect):
    page.goto(base_url)
    hp.click("{sel}", intent="{intent}", expect=expect)
    page.goto(mutated_url)
    hp.click("{sel}", intent="{intent}", expect=expect)
'''


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    for seed in range(30):
        rec = corpus.write_case(tmp, "checkout", "class_churn", seed)
        if not rec["oracle_blind"]:
            break
    test_file = tmp / "test_checkout.py"
    test_file.write_text(TEST_SRC.format(sel=rec["old_selector"], intent=rec["intent"]), encoding="utf-8")
    print("--- test source BEFORE ---\n" + test_file.read_text(encoding="utf-8"))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        hp = HealingPage(
            page,
            heal=HealConfig(mode="verify_topk"),
            out_dir=str(tmp / ".mendlock"),
            patch_mode="apply",
        )
        ns = runpy.run_path(str(test_file))
        ns["run"](
            hp, page,
            (tmp / rec["base_page"]).resolve().as_uri(),
            (tmp / rec["mutated_page"]).resolve().as_uri(),
            corpus.make_expect(rec["result_text"]),
        )
        browser.close()

    ev = hp.events[-1]
    print(
        f"--- heal event ---\nstatus={ev['status']} verified={ev['verified']} "
        f"confidence={ev['confidence']} latency={ev['latency_ms']}ms\n"
        f"healed selector: {ev['attempts'][-1]['css_path']}"
    )
    print("--- test source AFTER ---\n" + test_file.read_text(encoding="utf-8"))
    print("log + diff written to", tmp / ".mendlock")


if __name__ == "__main__":
    main()