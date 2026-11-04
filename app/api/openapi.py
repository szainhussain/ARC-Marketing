"""OpenAPI 3.1 document generated from the live Flask URL map, so it can't
drift from the routes that actually exist. Each operation's summary is the
first line of the view's docstring or its function name. Request/response
bodies are documented in docs/API.md; the shared envelopes are below."""

import re

TAGS = [
    ("auth", "Authentication and sessions"), ("public", "Public site"), ("organizations", "Workspaces"),
    ("members", "Memberships"), ("invitations", "Memberships"), ("business-profile", "Business profile"),
    ("knowledge", "Brand knowledge"), ("documents", "Brand assets"), ("campaigns", "Campaigns"),
    ("runs", "Campaign execution"), ("agents", "Agents"), ("tasks", "Tasks"), ("deliverables", "Deliverables"),
    ("approvals", "Approvals"), ("external-actions", "Approvals"), ("calendar", "Content calendar"),
    ("integrations", "Integrations"), ("dashboard", "Analytics"), ("analytics", "Analytics"),
    ("reports", "Analytics"), ("usage", "Usage"), ("billing", "Billing"), ("notifications", "Notifications"),
    ("audit-events", "Audit"), ("activity", "Audit"), ("operations", "Operations"), ("policies", "Automation"),
    ("webhooks", "Webhooks"), ("health", "Health"), ("export", "Data lifecycle"), ("deletion", "Data lifecycle"),
]

ERROR_SCHEMA = {
    "type": "object",
    "properties": {"error": {"type": "object", "properties": {
        "code": {"type": "string"}, "message": {"type": "string"},
        "details": {"type": "array", "items": {"type": "object", "properties": {
            "field": {"type": "string"}, "issue": {"type": "string"}}}},
        "request_id": {"type": "string"}}}},
}


def _tag(path: str) -> str:
    parts = [p for p in path.split("/") if p and not p.startswith("{")]
    for part in reversed(parts[2:] if parts[:2] == ["api", "v1"] else parts):
        for key, tag in TAGS:
            if part == key:
                return tag
    return "Workspaces" if "organizations" in parts else "Other"


def build_spec(app) -> dict:
    paths: dict = {}
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/v1"):
            continue
        path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", rule.rule)
        view = app.view_functions[rule.endpoint]
        doc = (view.__doc__ or "").strip().splitlines()
        summary = doc[0] if doc else rule.endpoint.split(".")[-1].replace("_route", "").replace("_", " ")
        params = [{"name": p, "in": "path", "required": True, "schema": {"type": "string"}}
                  for p in re.findall(r"{([^}]+)}", path)]
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            op = {
                "summary": summary, "tags": [_tag(path)], "operationId": f"{rule.endpoint}_{method.lower()}",
                "parameters": params,
                "responses": {"200": {"description": "Success"},
                              "4XX": {"description": "Error", "content": {"application/json": {
                                  "schema": {"$ref": "#/components/schemas/Error"}}}}},
            }
            if method != "GET" and not path.startswith(("/api/v1/public", "/api/v1/billing/webhook")):
                op["parameters"] = params + [{"name": "X-CSRFToken", "in": "header", "required": True,
                                              "schema": {"type": "string"}}]
            if path.endswith("/runs") and method == "POST":
                op["parameters"].append({"name": "Idempotency-Key", "in": "header", "required": True,
                                         "schema": {"type": "string"}})
            paths.setdefault(path, {})[method.lower()] = op
    return {
        "openapi": "3.1.0",
        "info": {"title": "ARC API", "version": "1.0.0",
                 "description": "Session-cookie authenticated REST API. Mutating requests need X-CSRFToken "
                                "(GET /api/v1/auth/csrf-token). Every response carries X-Request-Id for "
                                "correlation. List endpoints accept limit/offset where noted in docs/API.md."},
        "servers": [{"url": "/"}],
        "components": {"schemas": {"Error": ERROR_SCHEMA},
                       "securitySchemes": {"session": {"type": "apiKey", "in": "cookie", "name": "session"}}},
        "security": [{"session": []}],
        "paths": dict(sorted(paths.items())),
    }
