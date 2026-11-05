"""Provider-neutral text embeddings. Gemini is called over its REST API (no
SDK). Without a key, ProviderUnavailable is raised and callers fall back to
keyword search; no fake vectors are ever produced."""

import json
import socket
import urllib.error
import urllib.request

from app.ai.errors import AIRequestTimeout, ProviderUnavailable, RateLimited

BATCH_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
MAX_BATCH = 100


class EmbeddingProvider:
    name = "base"
    model = "base"
    dims = 0

    def embed(self, texts: list[str], task: str = "document") -> list[list[float]]:
        raise NotImplementedError


class GeminiEmbeddingProvider(EmbeddingProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, dims: int, timeout: int = 30):
        self.api_key, self.model, self.dims, self.timeout = api_key, model, dims, timeout

    def embed(self, texts: list[str], task: str = "document") -> list[list[float]]:
        task_type = "RETRIEVAL_QUERY" if task == "query" else "RETRIEVAL_DOCUMENT"
        out: list[list[float]] = []
        for start in range(0, len(texts), MAX_BATCH):
            batch = texts[start:start + MAX_BATCH]
            body = {"requests": [{"model": f"models/{self.model}", "content": {"parts": [{"text": t[:8000]}]},
                                  "taskType": task_type, "outputDimensionality": self.dims} for t in batch]}
            req = urllib.request.Request(BATCH_URL.format(model=self.model), data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - fixed Google host
                    data = json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    raise RateLimited("Embedding rate limit reached.", retry_after_seconds=60) from exc
                raise ProviderUnavailable(f"Embedding provider returned HTTP {exc.code}.") from exc
            except (socket.timeout, TimeoutError) as exc:
                raise AIRequestTimeout("Embedding request timed out.") from exc
            except urllib.error.URLError as exc:
                raise ProviderUnavailable("Embedding provider could not be reached.") from exc
            vectors = [e.get("values") or [] for e in data.get("embeddings") or []]
            if len(vectors) != len(batch) or any(len(v) != self.dims for v in vectors):
                raise ProviderUnavailable("Embedding provider returned an unexpected shape.")
            out.extend(vectors)
        return out


def get_embedding_provider(app_config) -> EmbeddingProvider:
    key = (app_config.get("GEMINI_API_KEY") or "").strip()
    if not key:
        raise ProviderUnavailable("Semantic search is not configured (set GEMINI_API_KEY).")
    return GeminiEmbeddingProvider(key, app_config.get("EMBEDDING_MODEL") or "gemini-embedding-001",
                                   int(app_config.get("EMBEDDING_DIMS") or 768))
