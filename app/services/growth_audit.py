"""The free Growth Audit: reads one public page and reports what it finds
(docs/DECISIONS.md D22).

No AI. Every finding is a check a person can repeat by viewing the page
source, so the report is the same every time and nothing is invented.
Impact and effort are ARC's fixed editorial labels per check, not a
forecast of revenue. The fetch reuses the SSRF-safe reader in
website_import.py.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from flask import current_app

from app.services.website_import import fetch_html, normalise_url

_CTA = re.compile(r"\b(book|call|whatsapp|buy|order now|order online|shop|get a quote|quote|enquire|inquire|contact|schedule|"
                  r"reserve|sign up|subscribe|free trial|get started|apply|register|add to cart)\b", re.I)
_ANALYTICS = (("Google Analytics / Tag Manager", ("googletagmanager.com", "google-analytics.com", "gtag(")),
              ("Meta Pixel", ("connect.facebook.net", "fbq(")),
              ("TikTok Pixel", ("analytics.tiktok.com",)),
              ("Snap Pixel", ("sc-static.net/scevent",)))
_SOCIAL = ("instagram.com", "facebook.com", "tiktok.com", "linkedin.com", "youtube.com", "x.com", "twitter.com",
           "snapchat.com")
_RANK = {"high": 0, "medium": 1, "low": 2}


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta: dict[str, str] = {}
        self.h1: list[str] = []
        self.links: list[str] = []
        self.link_texts: list[str] = []
        self.images = self.images_with_alt = self.forms = self.json_ld = 0
        self.lang = ""
        self.canonical = False
        self.hreflang: set[str] = set()
        self.words = 0
        self._stack: list[str] = []
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key:
                self.meta[key] = a.get("content", "").strip()
        elif tag == "link":
            rel = a.get("rel", "").lower()
            if "canonical" in rel:
                self.canonical = True
            if "alternate" in rel and a.get("hreflang"):
                self.hreflang.add(a["hreflang"].lower()[:2])
        elif tag == "img":
            self.images += 1
            self.images_with_alt += 1 if a.get("alt", "").strip() else 0
        elif tag == "form":
            self.forms += 1
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"].strip())
        elif tag == "script" and "ld+json" in a.get("type", "").lower():
            self.json_ld += 1
        if tag in ("title", "h1", "a", "button", "script", "style"):
            self._stack.append(tag)
            self._buf = []

    def handle_endtag(self, tag):
        if self._stack and self._stack[-1] == tag:
            text = " ".join("".join(self._buf).split())
            if tag == "title":
                # Only the first <title>: inline SVG icons carry their own.
                self.title = self.title or text
            elif tag == "h1" and text:
                self.h1.append(text)
            elif tag in ("a", "button") and text:
                self.link_texts.append(text)
            self._stack.pop()
            self._buf = []

    def handle_data(self, data):
        if self._stack:
            self._buf.append(data)
        if not self._stack or self._stack[-1] not in ("script", "style"):
            self.words += len(data.split())


def _finding(area, check, passed, impact, effort, found, fix):
    return {"area": area, "check": check, "passed": bool(passed), "impact": impact, "effort": effort,
            "found": found, "fix": None if passed else fix}


def audit_html(html: str, final_url: str) -> dict:
    """Pure function over page source, so it is unit-testable without a network."""

    p = _Page()
    try:
        p.feed(html)
    except Exception:  # noqa: BLE001 - malformed markup: report what was parsed so far
        pass
    lower = html.lower()
    title, desc = p.title, p.meta.get("description", "")
    ctas = sorted({t for t in p.link_texts if _CTA.search(t) and len(t) <= 40})[:5]
    direct = [h for h in p.links if h.lower().startswith(("tel:", "mailto:")) or "wa.me/" in h.lower()
              or "api.whatsapp.com" in h.lower()]
    trackers = [name for name, needles in _ANALYTICS if any(n in lower for n in needles)]
    socials = sorted({s.split(".")[0] for s in _SOCIAL for h in p.links if s in h.lower()})
    alt_pct = round(p.images_with_alt / p.images * 100) if p.images else None

    findings = [
        _finding("Positioning", "One clear main headline", len(p.h1) == 1, "high", "low",
                 f"{len(p.h1)} main headline(s) found" + (f": “{p.h1[0][:90]}”" if p.h1 else "."),
                 "Use exactly one main headline (H1) that says what you sell and who it is for."),
        _finding("Positioning", "Page description for search and sharing", 50 <= len(desc) <= 160, "high", "low",
                 f"Description is {len(desc)} characters." if desc else "No meta description.",
                 "Write a 50–160 character description of your offer, location and main benefit."),
        _finding("SEO", "Page title of a useful length", 15 <= len(title) <= 65, "high", "low",
                 f"Title is {len(title)} characters: “{title[:80]}”." if title else "No page title.",
                 "Write a 15–65 character title with your main service and your city or area."),
        _finding("SEO", "Secure address (HTTPS)", final_url.startswith("https://"), "high", "medium",
                 "Served over HTTPS." if final_url.startswith("https://") else "Served over plain HTTP.",
                 "Turn on HTTPS with your host; browsers warn visitors about pages that are not secure."),
        _finding("SEO", "Structured data for search engines", p.json_ld > 0, "medium", "medium",
                 f"{p.json_ld} structured-data block(s) found.",
                 "Add LocalBusiness structured data (name, address, hours, phone) so search engines can show it."),
        _finding("SEO", "Canonical address set", p.canonical, "low", "low",
                 "Canonical link found." if p.canonical else "No canonical link.",
                 "Add a canonical link so duplicate addresses do not split your search ranking."),
        _finding("SEO", "Images described for search and accessibility", alt_pct is None or alt_pct >= 80, "medium", "medium",
                 "No images on the page." if alt_pct is None else f"{alt_pct}% of {p.images} images have a description.",
                 "Add a short description (alt text) to every meaningful image."),
        _finding("Website conversion", "Works on phones", "viewport" in p.meta, "high", "medium",
                 "Mobile viewport is set." if "viewport" in p.meta else "No mobile viewport tag.",
                 "Add a mobile viewport tag and check the page on a phone."),
        _finding("Website conversion", "A clear next step", bool(ctas), "high", "low",
                 "Calls to action found: " + ", ".join(f"“{c}”" for c in ctas) + "." if ctas
                 else "No button or link asking the visitor to book, call, buy or enquire.",
                 "Add one obvious action near the top: Book, Call, WhatsApp or Get a quote."),
        _finding("Lead generation", "One-tap contact (call, WhatsApp or email)", bool(direct), "high", "low",
                 f"{len(direct)} direct contact link(s) found." if direct else "No tel:, WhatsApp or mailto: link.",
                 "Add a tap-to-call link and a WhatsApp link so a visitor can reach you in one tap."),
        _finding("Lead generation", "An enquiry or booking form", p.forms > 0, "medium", "medium",
                 f"{p.forms} form(s) found." if p.forms else "No form on this page.",
                 "Add a short enquiry form (name, phone, what they need) for people not ready to call."),
        _finding("Advertising", "Visitor tracking installed", bool(trackers), "high", "medium",
                 "Found: " + ", ".join(trackers) + "." if trackers else "No analytics or ad pixel detected in the page source.",
                 "Install Google Analytics and the Meta Pixel before spending on ads, or you cannot tell what worked."),
        _finding("Advertising", "Link preview for shared links and ads", "og:title" in p.meta and "og:image" in p.meta, "medium", "low",
                 "Preview title and image are set." if "og:title" in p.meta and "og:image" in p.meta
                 else "Missing preview title or image.",
                 "Add Open Graph title, description and image so shared links and ads show a proper preview."),
        _finding("Content", "Enough written content to explain the offer", p.words >= 250, "medium", "medium",
                 f"About {p.words} words of visible text.",
                 "Add plain text covering services, prices or ranges, areas served and common questions."),
        _finding("Content", "Links to active social profiles", bool(socials), "low", "low",
                 "Links to: " + ", ".join(socials) + "." if socials else "No social profile links.",
                 "Link the social profiles you actually keep up to date."),
    ]
    failed = sorted((f for f in findings if not f["passed"]), key=lambda f: (_RANK[f["impact"]], _RANK[f["effort"]]))
    areas = {}
    for f in findings:
        a = areas.setdefault(f["area"], {"area": f["area"], "passed": 0, "total": 0})
        a["total"] += 1
        a["passed"] += 1 if f["passed"] else 0
    return {
        "url": final_url,
        "checks_passed": sum(1 for f in findings if f["passed"]),
        "checks_total": len(findings),
        "areas": list(areas.values()),
        "priorities": failed,
        "passed": [f for f in findings if f["passed"]],
        "languages": sorted(p.hreflang | ({p.lang.lower()[:2]} if p.lang else set())),
        "method": "ARC read the public source of this one page. Each item is a check you can repeat yourself. "
                  "Impact and effort are ARC's standard labels for each check, not a forecast for your business. "
                  "Content loaded by scripts after the page opens may not be seen.",
    }


def run_audit(raw_url: str) -> dict:
    final_url, html = fetch_html(normalise_url(raw_url))
    return audit_html(html, final_url)


# ---- Page speed (Google PageSpeed Insights API v5) ---------------------------

class SpeedUnavailable(Exception):
    pass


def _psi_http(url: str) -> dict:
    """The only network call for page speed (patched in tests)."""
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ARC-Growth-Audit/1"})
    with urllib.request.urlopen(req, timeout=45) as resp:  # noqa: S310 - fixed Google host
        return json.loads(resp.read().decode())


def page_speed(raw_url: str) -> dict:
    """Mobile performance from Google's own test. Needs PAGESPEED_API_KEY (the
    keyless quota is shared and is normally exhausted). Raises SpeedUnavailable
    rather than returning a made-up number."""

    key = current_app.config.get("PAGESPEED_API_KEY")
    if not key:
        raise SpeedUnavailable("Page speed testing is not connected.")
    target = normalise_url(raw_url)
    query = urllib.parse.urlencode({"url": target, "strategy": "mobile", "category": "performance", "key": key})
    try:
        data = _psi_http(f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?{query}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise SpeedUnavailable(f"Google's speed test did not answer ({type(exc).__name__}).") from exc
    lighthouse = data.get("lighthouseResult") or {}
    score = ((lighthouse.get("categories") or {}).get("performance") or {}).get("score")
    if score is None:
        raise SpeedUnavailable("Google's speed test returned no score for this page.")
    audits = lighthouse.get("audits") or {}
    labels = (("largest-contentful-paint", "Main content visible"), ("total-blocking-time", "Time the page is frozen"),
              ("cumulative-layout-shift", "Layout movement while loading"), ("speed-index", "Speed index"))
    return {
        "url": target,
        "performance_score": round(score * 100),
        "metrics": [{"label": label, "value": audits[k].get("displayValue")} for k, label in labels
                    if audits.get(k, {}).get("displayValue")],
        "source": "Google PageSpeed Insights, mobile test",
    }
