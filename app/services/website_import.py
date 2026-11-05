"""Read a business's public homepage and suggest business-profile fields.

No AI: it extracts what the page itself says (title, description, headings,
language). The fetch is SSRF-safe: only http(s) on default ports, every
resolved address must be public, the connection is pinned to the checked IP
(so DNS can't be swapped between check and connect), redirects are followed
manually and re-checked, and size and time are capped.
"""

import http.client
import ipaddress
import re
import socket
import ssl
import urllib.parse
from html.parser import HTMLParser

from app.services.errors import ValidationError

MAX_BYTES = 1_500_000
TIMEOUT = 8
MAX_REDIRECTS = 3
USER_AGENT = "ARC-Profile-Import/1.0 (+https://usearc.vercel.app)"


class ImportFailed(ValidationError):
    pass


def _fail(issue: str):
    raise ImportFailed("We couldn't read that website.", details=[{"field": "url", "issue": issue}])


def normalise_url(raw: str) -> str:
    url = (raw or "").strip()
    if not url:
        _fail("Enter your website address")
    if "://" not in url:
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        _fail("Use a web address like https://example.com")
    if parsed.username or parsed.password:
        _fail("Web addresses with a username or password aren't supported")
    if parsed.port not in (None, 80, 443):
        _fail("Only standard web ports are supported")
    return urllib.parse.urlunparse(parsed._replace(fragment="", path=parsed.path or "/"))


def _public_ip(host: str, port: int) -> str:
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        _fail("That address could not be found")
    ips = [info[4][0] for info in infos]
    for ip in ips:
        addr = ipaddress.ip_address(ip)
        if not addr.is_global or addr.is_multicast:
            _fail("That address points to a private or reserved network")
    return ips[0]


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, ip, **kw):
        super().__init__(host, **kw)
        self._ip = ip

    def connect(self):
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host, ip, **kw):
        super().__init__(host, **kw)
        self._ip = ip

    def connect(self):
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


def fetch_html(url: str) -> tuple[str, str]:
    """Returns (final_url, html)."""

    return _fetch(url, ("html",), "text/html,application/xhtml+xml")


def _fetch(url: str, kinds: tuple[str, ...], accept: str, user_agent: str = USER_AGENT) -> tuple[str, str]:

    for _ in range(MAX_REDIRECTS + 1):
        parsed = urllib.parse.urlparse(url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        ip = _public_ip(parsed.hostname, port)
        if parsed.scheme == "https":
            conn = _PinnedHTTPSConnection(parsed.hostname, ip, port=port, timeout=TIMEOUT, context=ssl.create_default_context())
        else:
            conn = _PinnedHTTPConnection(parsed.hostname, ip, port=port, timeout=TIMEOUT)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        try:
            conn.request("GET", path, headers={"User-Agent": user_agent, "Accept": accept,
                                               "Accept-Language": "en;q=0.9,*;q=0.5"})
            resp = conn.getresponse()
            if resp.status in (301, 302, 303, 307, 308):
                location = resp.getheader("Location")
                if not location:
                    _fail("The website redirected without a destination")
                url = normalise_url(urllib.parse.urljoin(url, location))
                continue
            if resp.status >= 400:
                _fail(f"The website answered with an error ({resp.status})")
            ctype = (resp.getheader("Content-Type") or "").lower()
            if not any(k in ctype for k in kinds):
                _fail("That address doesn't return a web page")
            body = resp.read(MAX_BYTES + 1)[:MAX_BYTES]
            charset = "utf-8"
            m = re.search(r"charset=([\w-]+)", ctype)
            if m:
                charset = m.group(1)
            try:
                return url, body.decode(charset, errors="replace")
            except LookupError:
                return url, body.decode("utf-8", errors="replace")
        except (OSError, http.client.HTTPException, ssl.SSLError):
            _fail("The website could not be reached")
        finally:
            conn.close()
    _fail("The website redirected too many times")


class _Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title = ""
        self.lang = ""
        self.headings: list[str] = []
        self.paragraphs: list[str] = []
        self._stack: list[str] = []
        self._buf: list[str] = []
        self._skip = 0
        self.max_paragraphs = 3

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "html" and a.get("lang"):
            self.lang = a["lang"]
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key and a.get("content"):
                self.meta.setdefault(key, a["content"].strip())
        if tag in ("script", "style", "noscript", "svg", "nav", "footer"):
            self._skip += 1
        if tag in ("title", "h1", "h2", "p"):
            self._stack.append(tag)
            self._buf = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg", "nav", "footer") and self._skip:
            self._skip -= 1
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if tag == "title" and not self.title:
                self.title = text
            elif tag in ("h1", "h2") and text and len(self.headings) < 8 and text not in self.headings:
                self.headings.append(text[:160])
            elif tag == "p" and len(text) >= 60 and len(self.paragraphs) < self.max_paragraphs:
                self.paragraphs.append(text[:400])

    def handle_data(self, data):
        if self._stack and not self._skip:
            self._buf.append(data)


_LANGS = {"en": "English", "ar": "Arabic", "ur": "Urdu", "hi": "Hindi", "fr": "French", "de": "German", "es": "Spanish",
          "pt": "Portuguese", "it": "Italian", "nl": "Dutch", "tr": "Turkish", "zh": "Chinese", "ja": "Japanese", "ko": "Korean"}


def extract_profile(html: str, final_url: str) -> dict:
    p = _Extractor()
    try:
        p.feed(html)
    except Exception:  # noqa: BLE001 - broken HTML still yields whatever was parsed
        pass
    title = p.meta.get("og:title") or p.title
    name = p.meta.get("og:site_name") or re.split(r"\s+[|–—·:-]\s+", title or "")[0].strip()
    description = p.meta.get("description") or p.meta.get("og:description") or (p.paragraphs[0] if p.paragraphs else "")
    lang_code = (p.lang or "").split("-")[0].lower()
    parsed = urllib.parse.urlparse(final_url)
    return {
        "suggested": {
            "business_name": name[:255] or None,
            "website": f"{parsed.scheme}://{parsed.hostname}",
            "business_description": description[:1000] or None,
            "language": _LANGS.get(lang_code),
        },
        "found": {"title": title or None, "headings": p.headings, "paragraphs": p.paragraphs},
        "source_url": final_url,
    }


def import_from_website(raw_url: str) -> dict:
    final_url, html = fetch_html(normalise_url(raw_url))
    return extract_profile(html, final_url)


# ---- Research: readable text from public pages, respecting robots.txt -------

RESEARCH_AGENT = "ARC-Research/1.0 (+https://usearc.vercel.app)"
RESEARCH_TEXT_LIMIT = 4000


def robots_allows(url: str) -> bool:
    """False only when the site's robots.txt disallows our agent for this path."""

    import urllib.robotparser

    parsed = urllib.parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        _, text = _fetch(robots_url, ("text", "octet-stream"), "text/plain", RESEARCH_AGENT)
    except ImportFailed:
        return True  # no robots.txt (or unreachable): nothing forbids it
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(text.splitlines())
    return rp.can_fetch(RESEARCH_AGENT, url)


def fetch_page_text(raw_url: str) -> dict:
    """{url, title, text} for one public page, or {url, error}. Never raises."""

    try:
        url = normalise_url(raw_url)
        if not robots_allows(url):
            return {"url": url, "error": "The site's robots.txt asks automated tools not to read this page."}
        final_url, html = _fetch(url, ("html",), "text/html,application/xhtml+xml", RESEARCH_AGENT)
    except ImportFailed as exc:
        return {"url": raw_url, "error": exc.details[0]["issue"] if exc.details else str(exc)}
    p = _Extractor()
    p.max_paragraphs = 25
    try:
        p.feed(html)
    except Exception:  # noqa: BLE001
        pass
    parts = [p.meta.get("description") or ""] + p.headings + p.paragraphs
    text = re.sub(r"\s+", " ", " \n".join(x for x in parts if x)).strip()[:RESEARCH_TEXT_LIMIT]
    return {"url": final_url, "title": p.meta.get("og:title") or p.title or None, "text": text}
