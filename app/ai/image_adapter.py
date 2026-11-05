"""Provider-neutral image generation. Gemini is called over its public REST
API (no SDK), so nothing here imports a vendor library. Without a configured
key the adapter raises ProviderUnavailable: no placeholder image is ever
returned as if it were real (CLAUDE.md rule 5)."""

import base64
import json
import socket
import urllib.error
import urllib.request

from app.ai.errors import AIRequestTimeout, InvalidOutput, ProviderUnavailable, RateLimited

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ASPECT_RATIOS = ("1:1", "4:5", "9:16", "16:9")


class ImageProvider:
    name = "base"

    def generate(self, prompt: str, aspect_ratio: str = "1:1") -> tuple[bytes, str]:
        """Returns (image bytes, mime type)."""
        raise NotImplementedError


class GeminiImageProvider(ImageProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: int = 90):
        self.api_key, self.model, self.timeout = api_key, model, timeout

    def generate(self, prompt: str, aspect_ratio: str = "1:1") -> tuple[bytes, str]:
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect_ratio}},
        }
        req = urllib.request.Request(
            GEMINI_ENDPOINT.format(model=self.model), data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - fixed Google host
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise RateLimited("Image provider rate limit reached.", retry_after_seconds=60) from exc
            if exc.code in (401, 403):
                raise ProviderUnavailable("Image generation key was rejected.") from exc
            raise ProviderUnavailable(f"Image provider returned HTTP {exc.code}.") from exc
        except (socket.timeout, TimeoutError) as exc:
            raise AIRequestTimeout("Image generation timed out.") from exc
        except urllib.error.URLError as exc:
            raise ProviderUnavailable("Image provider could not be reached.") from exc
        for cand in data.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"]), inline.get("mimeType") or inline.get("mime_type") or "image/png"
        reason = (data.get("promptFeedback") or {}).get("blockReason")
        raise InvalidOutput(f"No image returned{f' ({reason})' if reason else ''}.")


def get_image_provider(app_config) -> ImageProvider:
    key = (app_config.get("GEMINI_API_KEY") or "").strip()
    if not key:
        raise ProviderUnavailable("Image generation is not configured (set GEMINI_API_KEY).")
    return GeminiImageProvider(key, app_config.get("IMAGE_MODEL") or "gemini-2.5-flash-image",
                               timeout=int(app_config.get("IMAGE_TIMEOUT_SECONDS") or 90))
