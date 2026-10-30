"""Real-application evaluation on the React 18 + TypeScript multi-release SUT."""
from __future__ import annotations

import shutil
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

from mendlock.candidates import make_fingerprint
from mendlock.healer import HealConfig, Healer
from mendlock.model import load_default_model

SUT_DIR = Path(__file__).parent.parent / "sut-react"
RESULTS_DIR = Path(__file__).parent.parent / "results"
BASE_URL = "http://127.0.0.1:5173"


@dataclass
class ReactScenario:
    id: str
    category: str
    v1_selector: str
    intent: str
    expected_banner: str
    has_target_in_v2: bool


SCENARIOS = [
    ReactScenario(
        id="react-catalog-4070",
        category="context + reorder + label_shift",
        v1_selector="#add-gpu-4070",
        intent="Add the RTX 4070 Ti Workstation to the cart",
        expected_banner="Added RTX 4070 Ti Workstation to cart",
        has_target_in_v2=True,
    ),
    ReactScenario(
        id="react-checkout-order",
        category="id_churn + class_churn + decoy",
        v1_selector="#place-order-btn",
        intent="Place the corporate order and confirm payment",
        expected_banner="Corporate order #INV-2026 confirmed",
        has_target_in_v2=True,
    ),
    ReactScenario(
        id="react-wire-transfer",
        category="restyle + dom_wrap",
        v1_selector="button.js-send-wire",
        intent="Send the treasury wire transfer",
        expected_banner="Wire transfer dispatched",
        has_target_in_v2=True,
    ),
    ReactScenario(
        id="react-security-policy",
        category="tag_change + label_shift",
        v1_selector="#save-security-btn",
        intent="Save and update the security policy changes",
        expected_banner="Security policy updated",
        has_target_in_v2=True,
    ),
    ReactScenario(
        id="react-legacy-xml-removed",
        category="removed (target deleted in v2)",
        v1_selector="#export-legacy-xml",
        intent="Export the legacy XML report",
        expected_banner="Legacy XML exported",
        has_target_in_v2=False,
    ),
]


def _format_table(headers: list[str], rows: list[list[str]], right_align: set[int] | None = None) -> list[str]:
    right_align = right_align or set()
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    hdr = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    sep = "|-" + "-|-".join("-" * widths[i] for i in range(len(headers))) + "-|"
    out = [hdr, sep]
    for r in rows:
        cells = [
            r[i].rjust(widths[i]) if i in right_align else r[i].ljust(widths[i])
            for i in range(len(headers))
        ]
        out.append("| " + " | ".join(cells) + " |")
    return out


def _server_up(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1.0) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_react_server():
    if _server_up(BASE_URL):
        return None
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm is required to build/run sut-react")
    if not (SUT_DIR / "node_modules").exists():
        print("Installing sut-react dependencies via npm install...")
        subprocess.run([npm, "install"], cwd=str(SUT_DIR), check=True)
    proc = subprocess.Popen(
        [npm, "run", "dev"],
        cwd=str(SUT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(40):
        if _server_up(BASE_URL):
            return proc
        time.sleep(0.25)
    proc.terminate()
    raise RuntimeError("Timed out waiting for Vite React server on http://127.0.0.1:5173")


def make_banner_expect(expected_text: str):
    def expect(page) -> bool:
        loc = page.locator("#status-banner")
        return loc.is_visible() and expected_text in loc.inner_text()
    return expect


def run_react_benchmark() -> Path:
    proc = ensure_react_server()
    model = load_default_model()
    modes = ("gate", "verify", "verify_topk")
    table_rows: list[list[str]] = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_context(viewport={"width": 1200, "height": 850}).new_page()

            for sc in SCENARIOS:
                page.goto(f"{BASE_URL}/?release=v1")
                fp = make_fingerprint(page, sc.v1_selector, page_key="/")
                expect = make_banner_expect(sc.expected_banner)

                for m in modes:
                    page.goto(f"{BASE_URL}/?release=v2")
                    page.evaluate("() => window.localStorage.setItem('mendlock_last_action', 'clean')")
                    cfg = HealConfig(mode=m, max_attempts=3, guard_mutations=True)
                    res = Healer(model, cfg).heal(page, fp, sc.intent, expect)

                    healed_correctly = res.healed and sc.has_target_in_v2 and make_banner_expect(sc.expected_banner)(page)
                    false_commit = res.healed and not healed_correctly

                    table_rows.append([
                        sc.id,
                        sc.category,
                        m,
                        res.status,
                        str(len(res.attempts)),
                        str(int(healed_correctly)),
                        str(int(false_commit)),
                        str(len(res.blocked_requests)),
                        f"{res.latency_ms:.1f}",
                    ])
            browser.close()
    finally:
        if proc is not None:
            proc.terminate()

    headers = [
        "Scenario", "Mutation Type", "Mode", "Status",
        "Attempts", "Correct", "False Commit", "Blocked HTTP", "Latency (ms)",
    ]
    formatted = _format_table(headers, table_rows, right_align={4, 5, 6, 7, 8})
    lines = ["# React 18 + TypeScript Real-Application Case Study", ""] + formatted

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_md = RESULTS_DIR / "react_case_study.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines))
    return out_md


if __name__ == "__main__":
    run_react_benchmark()
