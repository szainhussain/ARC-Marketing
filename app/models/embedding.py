"""Semantic search index for Ask ARC: one row per text chunk of a workspace
source (approved knowledge entry or deliverable section)."""

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class EmbeddingChunk(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "embedding_chunks"
    __table_args__ = (db.Index("ix_embedding_chunks_source", "organization_id", "source_kind", "source_id"),)

    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True)
    source_kind = db.Column(db.String(16), nullable=False)  # knowledge | deliverable
    source_id = db.Column(db.String(36), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False, default=0)
    title = db.Column(db.String(255), nullable=False)
    text = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=False)
    # sha256 of the source text this chunk set was built from; a change re-embeds it.
    source_hash = db.Column(db.String(64), nullable=False)
    model = db.Column(db.String(64), nullable=False)
    dims = db.Column(db.Integer, nullable=False)
    vector = db.Column(db.LargeBinary, nullable=False)  # float32, unit-normalised
