"""Semantic retrieval for Ask ARC.

Index: approved knowledge entries and the current version of each
deliverable, chunked and embedded per workspace. The index is refreshed
lazily by the worker right before it answers a question for that workspace
(bounded per pass), so new or edited content is found without a cron job.
Anything that stops qualifying (knowledge archived or left `proposed`,
deliverable deleted) is removed from the index on the next refresh.

Similarity is cosine over unit vectors stored as float32, computed in
Python: at one workspace's scale (hundreds to low thousands of chunks) that
is fast and works on SQLite and Postgres alike. pgvector is the upgrade path
if a workspace grows far beyond that.
"""

import hashlib
import json
import logging
import math
from array import array

from flask import current_app

from app.ai.embedding_adapter import get_embedding_provider
from app.extensions import db
from app.models.campaign import Campaign
from app.models.deliverable import Deliverable
from app.models.embedding import EmbeddingChunk
from app.models.platform import KnowledgeEntry

log = logging.getLogger(__name__)
CHUNK_CHARS = 1400
MAX_NEW_CHUNKS_PER_PASS = 200
MIN_SCORE = 0.35


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chunks(text: str) -> list[str]:
    text = text.strip()
    if len(text) <= CHUNK_CHARS:
        return [text] if text else []
    parts, cur = [], ""
    for para in text.replace("\r", "").split("\n"):
        if len(cur) + len(para) + 1 > CHUNK_CHARS and cur:
            parts.append(cur.strip())
            cur = ""
        while len(para) > CHUNK_CHARS:
            parts.append(para[:CHUNK_CHARS])
            para = para[CHUNK_CHARS:]
        cur += para + "\n"
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _flatten(value, prefix: str = "") -> list[str]:
    """Deliverable content -> readable lines ("Variants: Instagram · Built for…")."""

    if isinstance(value, dict):
        return [line for k, v in value.items() for line in _flatten(v, k.replace("_", " ").capitalize())]
    if isinstance(value, list):
        if all(isinstance(x, (str, int, float)) for x in value):
            return [f"{prefix}: " + "; ".join(str(x) for x in value)] if value else []
        return [line for x in value for line in _flatten(x, prefix)]
    if value in (None, ""):
        return []
    return [f"{prefix}: {value}" if prefix else str(value)]


def _sources(organization_id: str) -> list[dict]:
    """Every item that may be searched right now, with its full text."""

    out = []
    for k in KnowledgeEntry.query.filter_by(organization_id=organization_id, status="approved"):
        out.append({"kind": "knowledge", "id": k.id, "title": k.title, "link": "/app/knowledge",
                    "text": f"{k.title}\n{k.body}"})
    names = {c.id: c.name for c in Campaign.query.filter_by(organization_id=organization_id)}
    for d in Deliverable.query.filter_by(organization_id=organization_id):
        v = d.current_version
        if not v:
            continue
        title = f"{d.deliverable_type.replace('_', ' ').capitalize()} for {names.get(d.campaign_id, 'a campaign')}"
        lines = _flatten(json.loads(v.content_json))
        out.append({"kind": "deliverable", "id": d.id, "title": title,
                    "link": f"/app/campaigns/{d.campaign_id}/deliverables", "text": title + "\n" + "\n".join(lines)})
    return out


def _pack(vec: list[float]) -> bytes:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return array("f", (x / norm for x in vec)).tobytes()


def _unpack(blob: bytes) -> array:
    a = array("f")
    a.frombytes(blob)
    return a


def refresh_index(organization_id: str, provider=None) -> dict:
    """Bring this workspace's index in line with what may be searched.
    Returns counts; raises ProviderUnavailable when no embedding key is set."""

    provider = provider or get_embedding_provider(current_app.config)
    current = {(s["kind"], s["id"]): s for s in _sources(organization_id)}
    existing = {}
    for row in EmbeddingChunk.query.filter_by(organization_id=organization_id):
        existing.setdefault((row.source_kind, row.source_id), []).append(row)
    removed = 0
    # Drop sources that no longer qualify or were embedded with another model.
    for key, rows in existing.items():
        src = current.get(key)
        if src is None or rows[0].source_hash != _hash(src["text"]) or rows[0].model != provider.model:
            for r in rows:
                db.session.delete(r)
            removed += len(rows)
    stale = {k for k, rows in existing.items()
             if k not in current or rows[0].source_hash != _hash(current[k]["text"]) or rows[0].model != provider.model}
    todo = [s for k, s in current.items() if k not in existing or k in stale]
    pending, budget = [], MAX_NEW_CHUNKS_PER_PASS
    for s in todo:
        chunks = _chunks(s["text"])
        if len(chunks) > budget:
            break
        budget -= len(chunks)
        pending.extend((s, i, c) for i, c in enumerate(chunks))
    added = 0
    if pending:
        vectors = provider.embed([c for _, _, c in pending], task="document")
        for (s, i, c), vec in zip(pending, vectors):
            db.session.add(EmbeddingChunk(organization_id=organization_id, source_kind=s["kind"], source_id=s["id"],
                                          chunk_index=i, title=s["title"][:255], text=c, link=s["link"],
                                          source_hash=_hash(s["text"]), model=provider.model, dims=provider.dims,
                                          vector=_pack(vec)))
            added += 1
    db.session.commit()
    return {"added": added, "removed": removed, "sources": len(current)}


def search(organization_id: str, question: str, k: int = 6, provider=None) -> list[dict]:
    """Top-k chunks for this workspace by cosine similarity (unit vectors)."""

    provider = provider or get_embedding_provider(current_app.config)
    q = _unpack(_pack(provider.embed([question], task="query")[0]))
    scored = []
    for row in EmbeddingChunk.query.filter_by(organization_id=organization_id, model=provider.model):
        v = _unpack(row.vector)
        if len(v) != len(q):
            continue
        score = sum(a * b for a, b in zip(q, v))
        if score >= MIN_SCORE:
            scored.append((score, row))
    scored.sort(key=lambda x: -x[0])
    seen, out = set(), []
    for score, row in scored:
        key = (row.source_kind, row.source_id, row.chunk_index)
        if key in seen:
            continue
        seen.add(key)
        prefix = "k" if row.source_kind == "knowledge" else "d"
        out.append({"id": f"{prefix}:{row.source_id}:{row.chunk_index}", "kind": row.source_kind, "title": row.title,
                    "text": row.text, "link": row.link, "score": round(score, 3)})
        if len(out) >= k:
            break
    return out
