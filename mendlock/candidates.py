"""DOM candidate extraction, fingerprint recording, and readable selector synthesis."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

from . import vision
from ._compat import PlaywrightError

_JS_LIB = r"""
const SEL = 'button, a[href], input:not([type=hidden]), select, textarea, summary, [role=button], [role=link], [role=menuitem], [role=tab], [tabindex]:not([tabindex="-1"])';
const ATTRS = ['id', 'name', 'type', 'role', 'aria-label', 'title', 'placeholder', 'href', 'value', 'data-testid', 'data-test', 'data-qa'];
const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
const implicitRole = (el) => {
  const r = el.getAttribute('role');
  if (r) return r;
  const t = el.tagName.toLowerCase();
  if (t === 'button') return 'button';
  if (t === 'a' && el.hasAttribute('href')) return 'link';
  if (t === 'select') return 'combobox';
  if (t === 'textarea') return 'textbox';
  if (t === 'input') {
    const ty = (el.getAttribute('type') || 'text').toLowerCase();
    if (['submit', 'button', 'reset'].indexOf(ty) >= 0) return 'button';
    return (ty === 'checkbox' || ty === 'radio') ? ty : 'textbox';
  }
  return '';
};
const cssPath = (el) => {
  const parts = [];
  for (let n = el; n && n.nodeType === 1 && n !== document.documentElement; n = n.parentElement) {
    const tag = n.tagName.toLowerCase();
    if (tag === 'body') { parts.unshift('body'); break; }
    let i = 1;
    for (let s = n.previousElementSibling; s; s = s.previousElementSibling) { if (s.tagName === n.tagName) i++; }
    parts.unshift(tag + ':nth-of-type(' + i + ')');
  }
  return parts.join(' > ');
};
const ancestors = (el) => {
  const out = [];
  for (let n = el.parentElement; n && n !== document.documentElement && out.length < 8; n = n.parentElement) out.push(n.tagName.toLowerCase());
  return out.reverse();
};
const ownText = (el) => norm(el.innerText || el.value || '');
const contextText = (el) => {
  let n = el.parentElement;
  for (let up = 0; n && n !== document.body && up < 5; n = n.parentElement, up++) {
    if (n.getElementsByTagName('*').length > 400) break;
    const clone = n.cloneNode(true);
    clone.querySelectorAll(SEL + ', script, style, [role=status], [aria-live]').forEach((x) => x.remove());
    const t = norm(clone.textContent);
    if (t) return t.slice(0, 200);
  }
  return '';
};
const describe = (el) => {
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  const attrs = {};
  for (const a of ATTRS) { if (el.hasAttribute(a)) attrs[a] = el.getAttribute(a); }
  return {
    tag: el.tagName.toLowerCase(),
    id: el.id || '',
    classes: Array.from(el.classList),
    attrs: attrs,
    role: implicitRole(el),
    text: ownText(el).slice(0, 120),
    bbox: [r.left + window.scrollX, r.top + window.scrollY, r.width, r.height],
    visible: r.width > 2 && r.height > 2 && cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity) > 0.05,
    enabled: !el.disabled && el.getAttribute('aria-disabled') !== 'true',
    path: ancestors(el),
    css_path: cssPath(el),
    context: contextText(el),
    gt: el.hasAttribute('data-gt'),
  };
};
"""

EXTRACT_ALL = "() => {" + _JS_LIB + " return Array.from(document.querySelectorAll(SEL)).map(describe); }"
DESCRIBE_ONE = "(el) => {" + _JS_LIB + " return describe(el); }"
CSS_PATH_ONE = "(el) => {" + _JS_LIB + " return cssPath(el); }"
DOC_SIZE = (
    "() => [Math.max(document.documentElement.scrollWidth, window.innerWidth),"
    " Math.max(document.documentElement.scrollHeight, window.innerHeight)]"
)


@dataclass
class Candidate:
    tag: str
    id: str
    classes: list
    attrs: dict
    role: str
    text: str
    bbox: list
    visible: bool
    enabled: bool
    path: list
    css_path: str
    context: str
    gt: bool = False

    @classmethod
    def from_js(cls, d: dict) -> "Candidate":
        return cls(**d)

    @property
    def actionable(self) -> bool:
        return self.visible and self.enabled


@dataclass
class Fingerprint:
    selector: str
    page_key: str
    element: Candidate
    doc_size: list
    ref_png_b64: str | None = None

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, d: dict) -> "Fingerprint":
        d = dict(d)
        d["element"] = Candidate(**d["element"])
        return cls(**d)


@dataclass
class PageSnapshot:
    candidates: list
    screenshot: bytes
    doc_size: list


def page_key_of(url: str) -> str:
    return urlparse(url).path or "/"


def snapshot(page, only_actionable: bool = True) -> PageSnapshot:
    cands = [Candidate.from_js(d) for d in page.evaluate(EXTRACT_ALL)]
    if only_actionable:
        cands = [c for c in cands if c.actionable]
    return PageSnapshot(cands, page.screenshot(full_page=True), page.evaluate(DOC_SIZE))


def locator_ok(page, selector: str) -> bool:
    try:
        loc = page.locator(selector)
        return loc.count() == 1 and loc.is_visible() and loc.is_enabled()
    except PlaywrightError:
        return False


def make_fingerprint(page, selector: str, page_key: str | None = None) -> Fingerprint:
    loc = page.locator(selector)
    n = loc.count()
    if n != 1:
        raise ValueError(f"Cannot record {selector!r}: matches {n} elements (expected 1)")
    el = Candidate.from_js(loc.evaluate(DESCRIBE_ONE))
    ref = None
    crop = vision.crop_bbox(vision.decode_png(page.screenshot(full_page=True)), el.bbox)
    if crop is not None:
        ref = vision.encode_b64(crop)
    return Fingerprint(selector, page_key or page_key_of(page.url), el, page.evaluate(DOC_SIZE), ref)


_DYNAMIC_ID = re.compile(r"\d{3,}|(?=[a-f]*\d)[0-9a-f]{5,}|^:r|^ember|^react-|^radix-", re.I)


def _q(v: str) -> str:
    return v.replace("\\", "\\\\").replace('"', '\\"')


def stable_selector(page, c: Candidate) -> str:
    opts = []
    for k in ("data-testid", "data-test", "data-qa"):
        if c.attrs.get(k):
            opts.append(f'[{k}="{_q(c.attrs[k])}"]')
    if c.id and not _DYNAMIC_ID.search(c.id):
        opts.append(f"#{c.id}" if re.fullmatch(r"[A-Za-z][\w-]*", c.id) else f'[id="{_q(c.id)}"]')
    if c.attrs.get("aria-label"):
        opts.append(f'{c.tag}[aria-label="{_q(c.attrs["aria-label"])}"]')
    if c.text and len(c.text) <= 60:
        opts.append(f'{c.tag}:text-is("{_q(c.text)}")')
    for sel in opts:
        try:
            loc = page.locator(sel)
            if loc.count() == 1 and loc.evaluate(CSS_PATH_ONE) == c.css_path:
                return sel
        except PlaywrightError:
            continue
    return c.css_path