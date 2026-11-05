"""WordPress.com live publishing connector (pilot channel, docs/DECISIONS.md D17).

Uses the public WordPress.com REST API with a per-site OAuth2 token:
  authorize  https://public-api.wordpress.com/oauth2/authorize
  token      https://public-api.wordpress.com/oauth2/token
  posts      https://public-api.wordpress.com/rest/v1.1/sites/{site}/posts/new
  read back  https://public-api.wordpress.com/rest/v1.1/sites/{site}/posts/slug:{slug}
(https://developer.wordpress.com/docs/oauth2/, https://developer.wordpress.com/docs/api/)

Every post gets a deterministic slug, so a retry after a crash or timeout
first looks the slug up and never creates a second copy."""

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from app.integrations.base import Connector

API = "https://public-api.wordpress.com"
TIMEOUT = 20


class WordPressError(Exception):
    def __init__(self, message: str, status: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status, self.retryable = status, retryable


def _http(method: str, url: str, data: dict | None = None, token: str | None = None) -> dict:
    """The only place this module touches the network (patched in tests)."""
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("User-Agent", "ARC-Publisher/1")
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 - fixed WordPress.com host
            raw = resp.read()
            return json.loads(raw.decode() or "{}")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = json.loads(exc.read().decode()).get("message", "")
        except Exception:  # noqa: BLE001
            pass
        raise WordPressError(f"WordPress.com returned {exc.code}{': ' + detail if detail else ''}",
                             status=exc.code, retryable=exc.code in (408, 429) or exc.code >= 500) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WordPressError(f"Could not reach WordPress.com ({type(exc).__name__})", retryable=True) from exc


def authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    q = urllib.parse.urlencode({"client_id": client_id, "redirect_uri": redirect_uri,
                                "response_type": "code", "state": state})
    return f"{API}/oauth2/authorize?{q}"


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> dict:
    """Returns {access_token, blog_id, blog_url, scope}."""
    data = _http("POST", f"{API}/oauth2/token", {"client_id": client_id, "client_secret": client_secret,
                                                 "redirect_uri": redirect_uri, "code": code,
                                                 "grant_type": "authorization_code"})
    if not data.get("access_token") or not data.get("blog_id"):
        raise WordPressError("WordPress.com did not return a site token.")
    return data


# ---- article formatting -------------------------------------------------
def _inline(text: str) -> str:
    out = html.escape(text, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)


def markdown_to_html(md: str) -> str:
    """Small, safe converter for the agent's markdown subset. Everything is
    HTML-escaped first, so model output can never inject markup or scripts."""
    blocks, bullets, para = [], [], []

    def flush_para():
        if para:
            blocks.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()

    def flush_bullets():
        if bullets:
            blocks.append("<ul>" + "".join(f"<li>{_inline(b)}</li>" for b in bullets) + "</ul>")
            bullets.clear()

    for raw in (md or "").replace("\r", "").split("\n"):
        line = raw.strip()
        m_head = re.match(r"^(#{2,4})\s+(.*)$", line)
        m_bullet = re.match(r"^(?:[-*•]|\d+[.)])\s+(.*)$", line)
        if not line:
            flush_para(); flush_bullets()
        elif m_head:
            flush_para(); flush_bullets()
            level = min(4, len(m_head.group(1)))
            blocks.append(f"<h{level}>{_inline(m_head.group(2))}</h{level}>")
        elif line.startswith("# "):
            flush_para(); flush_bullets()
            blocks.append(f"<h2>{_inline(line[2:])}</h2>")
        elif m_bullet:
            flush_para()
            bullets.append(m_bullet.group(1))
        else:
            flush_bullets()
            para.append(line)
    flush_para(); flush_bullets()
    return "\n".join(blocks)


def slug_for(title: str, action_id: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (title or "post").lower()).strip("-")[:60].strip("-") or "post"
    return f"{base}-{action_id.replace('-', '')[:6]}"


class WordPressComConnector(Connector):
    name = "wordpress_com"

    def __init__(self, token: str, site_id: str):
        self.token, self.site = token, str(site_id)

    def get_capabilities(self) -> dict:
        return {"supports_verification": True, "requires_manual_publication_confirmation": False,
                "content_types": ["blog_article"]}

    def health_check(self) -> dict:
        try:
            info = _http("GET", f"{API}/rest/v1.1/sites/{self.site}", token=self.token)
            return {"state": "connected", "site": info.get("URL")}
        except WordPressError as exc:
            return {"state": "reauth_required" if exc.status in (401, 403) else "degraded", "error": str(exc)}

    def validate_action(self, payload: dict) -> None:
        if not (payload.get("title") or "").strip():
            raise ValueError("The article has no title.")
        if len((payload.get("body_markdown") or "").strip()) < 50:
            raise ValueError("The article body is too short to publish.")
        if payload.get("status") not in ("publish", "draft"):
            raise ValueError("Unknown publish mode.")

    def find_by_slug(self, slug: str) -> dict | None:
        try:
            return _http("GET", f"{API}/rest/v1.1/sites/{self.site}/posts/slug:{urllib.parse.quote(slug)}",
                         token=self.token)
        except WordPressError as exc:
            if exc.status == 404:
                return None
            raise

    def execute_action(self, payload: dict, idempotency_key: str) -> dict:
        """Create the post once. idempotency_key is the deterministic slug."""
        self.validate_action(payload)
        existing = self.find_by_slug(idempotency_key)
        if existing and existing.get("ID"):
            return {"post_id": str(existing["ID"]), "url": existing.get("URL"), "status": existing.get("status"),
                    "reused_existing": True}
        data = {"title": payload["title"][:200], "content": markdown_to_html(payload["body_markdown"]),
                "excerpt": (payload.get("excerpt") or "")[:500], "status": payload["status"],
                "slug": idempotency_key, "tags": ",".join(t[:40] for t in (payload.get("tags") or [])[:10]),
                "format": "standard"}
        post = _http("POST", f"{API}/rest/v1.1/sites/{self.site}/posts/new", data, token=self.token)
        if not post.get("ID"):
            raise WordPressError("WordPress.com accepted the request but returned no post.", retryable=True)
        return {"post_id": str(post["ID"]), "url": post.get("URL"), "status": post.get("status"),
                "reused_existing": False}

    def verify_action(self, action_reference: str) -> dict:
        post = _http("GET", f"{API}/rest/v1.1/sites/{self.site}/posts/{urllib.parse.quote(action_reference)}",
                     token=self.token)
        return {"verification_supported": True, "status": post.get("status"), "url": post.get("URL")}

    def unpublish(self, action_reference: str) -> dict:
        """Moves the post to the site's trash (WordPress keeps it 30 days,
        so it can be restored from WordPress). A trashed post isn't public."""
        post = _http("POST", f"{API}/rest/v1.1/sites/{self.site}/posts/{urllib.parse.quote(action_reference)}/delete",
                     {}, token=self.token)
        return {"status": post.get("status")}

    def disconnect(self) -> None:
        return None
