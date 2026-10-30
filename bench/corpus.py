"""Synthetic mutation corpus generator with realistic page chrome and decoys."""
from __future__ import annotations

import copy
import html
import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

LOOKS = {
    "primary": "background:#2563eb;color:#fff;border:0",
    "secondary": "background:#e5e7eb;color:#111827;border:1px solid #d1d5db",
    "danger": "background:#dc2626;color:#fff;border:0",
    "link": "background:transparent;color:#2563eb;border:0;text-decoration:underline",
}
LAYOUTS = {
    "row": ".actions{display:flex;gap:12px;flex-wrap:wrap;align-items:center}",
    "col": ".actions{display:flex;flex-direction:column;gap:10px;align-items:flex-start}",
    "grid": ".actions{display:grid;grid-template-columns:repeat(2,max-content);gap:12px}",
}
BASE_CSS = (
    "body{font-family:system-ui,sans-serif;background:#f4f6f8;margin:0;padding:24px}"
    ".chrome{display:flex;gap:14px;margin-bottom:16px;font-size:14px}"
    ".card{background:#fff;max-width:560px;padding:24px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)}"
    "h2{margin:0 0 8px}h3{margin:14px 0 8px;font-size:16px}.note{color:#6b7280;font-size:14px;margin:6px 0}"
    ".group{margin-top:12px}#toast{margin-top:12px;color:#92400e}#result{margin-top:12px;color:#166534;font-weight:600}"
    "footer{margin-top:20px;display:flex;gap:12px;font-size:13px}"
)
FILLER = [
    "Prices include VAT where applicable.",
    "Need help? Contact support any time.",
    "Your data is encrypted in transit.",
    "Estimated delivery: 3-5 business days.",
]
CHROME_NAV = [
    ("Home", "toast:Navigated home"),
    ("Catalog", "toast:Catalog opened"),
    ("Notifications", "toast:No new alerts"),
    ("Help Center", "toast:Help opened"),
]
CHROME_FOOTER = [
    ("Privacy Policy", "toast:Privacy policy"),
    ("Terms of Service", "toast:Terms of service"),
    ("Cookie Settings", "toast:Cookie modal"),
]
SCRIPT = """
const RESULT = __RESULT__;
document.addEventListener('click', function (e) {
  const el = e.target.closest('[data-act]');
  if (!el) return;
  if (el.tagName === 'A') e.preventDefault();
  const act = el.getAttribute('data-act');
  const r = document.getElementById('result'), t = document.getElementById('toast');
  if (act === 'result') { r.textContent = RESULT; r.style.display = 'block'; }
  else if (act === 'weak') { r.textContent = RESULT + ' (preview only)'; r.style.display = 'block'; }
  else if (act.indexOf('toast:') === 0) { t.textContent = act.slice(6); t.style.display = 'block'; }
});
"""


@dataclass
class Control:
    label: str
    look: str = "secondary"
    effect: str = "none"
    tag: str = "button"
    id: str | None = None
    classes: list = field(default_factory=list)
    target: bool = False
    hidden: bool = False
    wrap: int = 0
    alts: list = field(default_factory=list)


@dataclass
class Group:
    heading: str
    controls: list


@dataclass
class Page:
    title: str
    blurb: str
    layout: str
    result: str
    groups: list
    filler: int = 1

    def controls(self):
        return [c for g in self.groups for c in g.controls]

    def target(self):
        return next((c for c in self.controls() if c.target), None)


TEMPLATES = {
    "checkout": dict(
        title="Checkout", blurb="Order total: $49.99 - 2 items", layout="row", ood=False,
        intent="Place the order and confirm payment", result="Order placed",
        target=("Place Order", "primary", ["Confirm & Pay", "Complete purchase", "Pay now"]),
        decoys=[("Save for later", "secondary", "toast:Saved for later"),
                ("Apply coupon", "secondary", "toast:Coupon applied"),
                ("Cancel order", "danger", "toast:Order cancelled")],
        weak="Place order preview"),
    "login": dict(
        title="Sign in", blurb="Welcome back - enter your credentials", layout="col", ood=False,
        intent="Sign in to the account", result="Signed in",
        target=("Sign in", "primary", ["Log in", "Continue", "Access account"]),
        decoys=[("Forgot password?", "link", "toast:Reset link sent"),
                ("Create account", "secondary", "toast:Registration opened"),
                ("Sign in with SSO", "secondary", "toast:Redirecting to SSO")],
        weak="Sign in as guest"),
    "newsletter": dict(
        title="Newsletter", blurb="Get weekly product updates", layout="row", ood=False,
        intent="Subscribe to the newsletter", result="Subscribed",
        target=("Subscribe", "primary", ["Sign up", "Join now", "Get updates"]),
        decoys=[("Unsubscribe", "secondary", "toast:Unsubscribed"),
                ("Manage preferences", "link", "toast:Preferences opened"),
                ("Not now", "link", "toast:Maybe later")],
        weak="Subscribe demo"),
    "settings": dict(
        title="Settings", blurb="Update your profile preferences", layout="row", ood=False,
        intent="Save the profile changes", result="Changes saved",
        target=("Save changes", "primary", ["Apply", "Update profile", "Confirm changes"]),
        decoys=[("Delete account", "danger", "toast:Account deletion requested"),
                ("Reset to defaults", "secondary", "toast:Defaults restored"),
                ("Discard changes", "link", "toast:Changes discarded")],
        weak="Save changes draft"),
    "cart": dict(
        title="Shop", blurb="Handmade items - free returns", layout="col", ood=False,
        intent="Add the Blue Mug to the cart", result="Blue Mug added",
        target=("Add to cart", "primary", ["Add to basket", "Buy now", "Add item"]),
        decoys=[], weak="Add Blue Mug sample"),
    "search": dict(
        title="Search", blurb="Find articles and guides", layout="row", ood=False,
        intent="Run the search", result="3 results",
        target=("Search", "primary", ["Find", "Go", "Look up"]),
        decoys=[("Clear", "link", "toast:Cleared"),
                ("Advanced search", "secondary", "toast:Advanced options"),
                ("Filters", "secondary", "toast:Filters opened")],
        weak="Search suggestions"),
    "transfer": dict(
        title="Transfer", blurb="Move money between your accounts", layout="col", ood=True,
        intent="Send the money transfer", result="Transfer sent",
        target=("Send money", "primary", ["Transfer now", "Pay", "Submit transfer"]),
        decoys=[("Request money", "secondary", "toast:Request created"),
                ("Schedule transfer", "secondary", "toast:Scheduled"),
                ("Cancel", "danger", "toast:Cancelled")],
        weak="Send money test"),
    "upload": dict(
        title="Upload", blurb="Attach a document to your application", layout="grid", ood=True,
        intent="Upload the selected file", result="File uploaded",
        target=("Upload file", "primary", ["Send file", "Attach", "Submit document"]),
        decoys=[("Remove file", "danger", "toast:File removed"),
                ("Browse files", "secondary", "toast:Browsing"),
                ("Download template", "link", "toast:Template downloaded")],
        weak="Upload file preview"),
}
CATEGORIES = ["id_churn", "class_churn", "label_shift", "dom_wrap", "reorder", "tag_change", "restyle", "removed"]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _finish(c: Control) -> Control:
    c.classes = ["btn", f"btn-{c.look}", f"js-{c.id}"]
    return c


def instantiate(name: str, rng: random.Random, blind: bool) -> Page:
    t = TEMPLATES[name]
    tlabel, tlook, alts = t["target"]
    if name == "cart":
        groups = []
        for head, key in [("Red Scarf - $18", "red-scarf"), ("Blue Mug - $12", "blue-mug"), ("Green Hat - $22", "green-hat")]:
            is_t = key == "blue-mug"
            ctrls = [
                Control(tlabel, "primary", "result" if is_t else f"toast:Added {head.split(' - ')[0]}",
                        id=f"add-{key}", target=is_t, alts=list(alts) if is_t else []),
                Control("Wishlist", "link", "toast:Saved to wishlist", id=f"wishlist-{key}"),
            ]
            if blind and is_t:
                ctrls.append(Control(t["weak"], "primary", "weak", id="add-blue-mug-sample"))
            rng.shuffle(ctrls)
            groups.append(Group(head, [_finish(c) for c in ctrls]))
        rng.shuffle(groups)
    else:
        ctrls = [Control(tlabel, tlook, "result", id=slug(tlabel), target=True, alts=list(alts))]
        ctrls += [Control(lb, lk, ef, id=slug(lb)) for lb, lk, ef in t["decoys"]]
        if blind:
            ctrls.append(Control(t["weak"], "primary", "weak", id=slug(t["weak"])))
        rng.shuffle(ctrls)
        groups = [Group("", [_finish(c) for c in ctrls])]
    return Page(t["title"], t["blurb"], t["layout"], t["result"], groups, filler=rng.randint(0, 3))


def _control_html(c: Control) -> str:
    attrs = []
    if c.id:
        attrs.append(f'id="{html.escape(c.id)}"')
    if c.classes:
        attrs.append(f'class="{" ".join(c.classes)}"')
    attrs.append(f'data-act="{html.escape(c.effect)}"')
    if c.target and not c.hidden:
        attrs.append('data-gt="1"')
    style = LOOKS[c.look] + ";padding:8px 16px;border-radius:6px;font:inherit;cursor:pointer"
    if c.tag != "button":
        style += ";display:inline-block;text-decoration:none"
    if c.hidden:
        style += ";display:none"
    a = " ".join(attrs)
    label = html.escape(c.label)
    if c.tag == "button":
        out = f'<button type="button" {a} style="{style}">{label}</button>'
    elif c.tag == "a":
        out = f'<a href="#" role="button" {a} style="{style}">{label}</a>'
    else:
        out = f'<div role="button" tabindex="0" {a} style="{style}">{label}</div>'
    for _ in range(c.wrap):
        out = f'<div class="w">{out}</div>'
    return out


def render(pg: Page) -> str:
    nav_items = "".join(
        f'<a href="#nav" data-act="{ef}" style="{LOOKS["link"]}">{lb}</a>' for lb, ef in CHROME_NAV
    )
    foot_items = "".join(
        f'<button type="button" data-act="{ef}" style="{LOOKS["secondary"]};padding:4px 10px;border-radius:4px">{lb}</button>'
        for lb, ef in CHROME_FOOTER
    )
    sections = []
    for g in pg.groups:
        head = f"<h3>{html.escape(g.heading)}</h3>" if g.heading else ""
        items = "".join(_control_html(c) for c in g.controls)
        sections.append(f'<section class="group">{head}<div class="actions">{items}</div></section>')
    notes = "".join(f'<p class="note">{FILLER[i % len(FILLER)]}</p>' for i in range(pg.filler))
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(pg.title)}</title>'
        f"<style>{BASE_CSS}{LAYOUTS[pg.layout]}</style></head><body>"
        f'<nav class="chrome">{nav_items}</nav>'
        f'<main class="card"><h2>{html.escape(pg.title)}</h2><p>{html.escape(pg.blurb)}</p>{notes}{"".join(sections)}'
        '<div id="toast" role="status" style="display:none"></div>'
        '<div id="result" role="status" style="display:none"></div></main>'
        f"<footer>{foot_items}</footer>"
        f"<script>{SCRIPT.replace('__RESULT__', json.dumps(pg.result))}</script></body></html>"
    )


def _dyn_id(rng, base: str) -> str:
    return rng.choice([
        f"{base}-{rng.getrandbits(20):05x}",
        f"ember{rng.randint(100, 9999)}",
        f":r{rng.randint(1, 99)}:",
        f"id_{rng.getrandbits(24):06x}",
    ])


def _hash_classes(rng) -> list:
    return [f"css-{rng.getrandbits(24):06x}", f"sc-{rng.getrandbits(20):05x}"]


def _shuffle_changed(items: list, rng) -> None:
    if len(items) < 2:
        return
    before = [id(x) for x in items]
    for _ in range(20):
        rng.shuffle(items)
        if [id(x) for x in items] != before:
            return


def m_id_churn(pg, rng):
    for c in pg.controls():
        c.id = _dyn_id(rng, slug(c.label))


def m_class_churn(pg, rng):
    for c in pg.controls():
        c.classes = _hash_classes(rng)
        if rng.random() < 0.5:
            c.id = None


def m_label_shift(pg, rng):
    t = pg.target()
    t.label, t.id = rng.choice(t.alts), None
    if rng.random() < 0.5:
        for c in pg.controls():
            c.classes = _hash_classes(rng)


def m_dom_wrap(pg, rng):
    t = pg.target()
    t.wrap, t.id = rng.choice([1, 2]), None
    if rng.random() < 0.5:
        for c in pg.controls():
            c.wrap = max(c.wrap, rng.choice([0, 1]))


def m_reorder(pg, rng):
    for g in pg.groups:
        _shuffle_changed(g.controls, rng)
    _shuffle_changed(pg.groups, rng)
    m_id_churn(pg, rng)
    if rng.random() < 0.5:
        for c in pg.controls():
            c.classes = _hash_classes(rng)


def m_tag_change(pg, rng):
    t = pg.target()
    t.tag = rng.choice(["a", "div"])
    if rng.random() < 0.7:
        t.id = None


def m_restyle(pg, rng):
    t = pg.target()
    t.look = rng.choice(["secondary", "link"])
    rng.choice([c for c in pg.controls() if not c.target]).look = "primary"
    m_class_churn(pg, rng)


def m_removed(pg, rng):
    t = pg.target()
    if rng.random() < 0.5:
        t.hidden = True
    elif len(pg.groups) > 1:
        pg.groups = [g for g in pg.groups if not any(c is t for c in g.controls)]
    else:
        pg.groups[0].controls = [c for c in pg.groups[0].controls if c is not t]


MUTATIONS = {
    "id_churn": m_id_churn, "class_churn": m_class_churn, "label_shift": m_label_shift, "dom_wrap": m_dom_wrap,
    "reorder": m_reorder, "tag_change": m_tag_change, "restyle": m_restyle, "removed": m_removed,
}
SELECTOR_KIND = {
    "id_churn": "id", "class_churn": "class", "label_shift": "text", "dom_wrap": "path",
    "reorder": "id", "tag_change": "class", "restyle": "class", "removed": "id",
}


def old_selector(category: str, pg: Page) -> str:
    t, kind = pg.target(), SELECTOR_KIND[category]
    if kind == "id":
        return f"#{t.id}"
    if kind == "class":
        return f"button.js-{t.id}"
    if kind == "path":
        return f".actions > button.js-{t.id}"
    grp = next(g for g in pg.groups if any(c is t for c in g.controls))
    scope = f'.group:has-text("{grp.heading}") ' if grp.heading else ""
    return f'{scope}button:text-is("{t.label}")'


def make_expect(result_text: str):
    def expect(page) -> bool:
        loc = page.locator("#result")
        return loc.is_visible() and result_text in loc.inner_text()
    return expect


def build_case(name: str, category: str, seed) -> dict:
    rng = random.Random(f"{name}|{category}|{seed}")
    blind = rng.random() < 0.2
    base = instantiate(name, rng, blind)
    old = old_selector(category, base)
    mut = copy.deepcopy(base)
    mut.filler = max(0, base.filler + rng.choice([-1, 0, 1, 2]))
    MUTATIONS[category](mut, rng)
    t = TEMPLATES[name]
    return {
        "base_html": render(base),
        "mutated_html": render(mut),
        "old_selector": old,
        "intent": t["intent"],
        "result_text": t["result"],
        "oracle_blind": blind,
        "has_target": category != "removed",
    }


def write_case(out_dir, name: str, category: str, seed, cid: str | None = None) -> dict:
    out_dir = Path(out_dir)
    pages = out_dir / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    c = build_case(name, category, seed)
    cid = cid or f"{name}-{category}-{seed}"
    (pages / f"{cid}.base.html").write_text(c.pop("base_html"), encoding="utf-8")
    (pages / f"{cid}.mut.html").write_text(c.pop("mutated_html"), encoding="utf-8")
    return {
        "id": cid, "template": name, "category": category, **c,
        "base_page": f"pages/{cid}.base.html", "mutated_page": f"pages/{cid}.mut.html",
    }


def generate(out_dir, per_cell: int = 10, seed: int = 0) -> list:
    out_dir = Path(out_dir)
    recs = []
    for name, spec in TEMPLATES.items():
        for cat in CATEGORIES:
            for s in range(per_cell):
                r = write_case(out_dir, name, cat, s + 1000 * seed, cid=f"{name}-{cat}-{s:02d}")
                r["seed"] = s
                if spec["ood"]:
                    r["split"] = "test_ood"
                else:
                    r["split"] = "train" if s < 0.5 * per_cell else ("calib" if s < 0.7 * per_cell else "test")
                recs.append(r)
    with (out_dir / "manifest.jsonl").open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return recs