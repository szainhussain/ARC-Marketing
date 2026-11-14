"""Per-platform formatting for manual copy-paste handoff.

No platform here has a live API connector (see docs/DECISIONS.md D5/D9,
none of Meta, Google Ads, or TikTok Ads have verified API access/app
review in this build). This module only reformats already-generated,
already-approved content_pack copy to match each platform's *composer*
constraints, so pasting into Meta Business Suite / Google Ads Editor /
TikTok Ads Manager needs less manual cleanup. It never calls any external
API and never schedules or publishes anything itself.

Every numeric limit below is either sourced from an official page (cited
in the comment) or explicitly marked UNCONFIRMED. Never upgrade an
UNCONFIRMED value to look authoritative without a real citation, that
would violate this project's own "never fabricate a source" rule
(docs/SECURITY_AND_GOVERNANCE.md) just as much as AI-fabricated content
would.
"""

from dataclasses import dataclass, field


@dataclass
class FieldCheck:
    label: str
    text: str
    limit: int | None  # None = no confirmed limit
    limit_confirmed: bool
    note: str = ""

    @property
    def length(self) -> int:
        return len(self.text)

    @property
    def fits(self) -> bool | None:
        if self.limit is None:
            return None
        return self.length <= self.limit

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "text": self.text,
            "length": self.length,
            "limit": self.limit,
            "limit_confirmed": self.limit_confirmed,
            "fits": self.fits,
            "note": self.note,
        }


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"


def format_for_meta_instagram(variant: dict) -> dict:
    """Source: Meta's own ad-creative specs (facebook.com/business/ads-guide),
    read 2026-11-03. These are the ad-composer limits Meta itself
    publishes; organic Instagram's caption limit is NOT published by Meta
    anywhere findable in this session, left unconfirmed rather than
    using the commonly-repeated-but-unofficial "2200 characters" figure.
    """
    headline = variant.get("headline", "") or ""
    body = variant.get("body", "") or ""

    fields = [
        FieldCheck(
            "Instagram feed primary text", body, 125, True,
            "Meta's recommended length for Instagram feed ad primary text.",
        ),
        FieldCheck(
            "Instagram feed headline", headline, 40, True,
            "Meta's recommended length for Instagram feed ad headline.",
        ),
        FieldCheck(
            "Facebook feed primary text", body, 150, True,
            "Upper end of Meta's 50–150 character recommendation for Facebook feed primary text.",
        ),
        FieldCheck(
            "Facebook feed headline", headline, 27, True,
            "Meta's recommended length for Facebook feed ad headline.",
        ),
        FieldCheck(
            "Organic Instagram caption", body, None, False,
            "No official Meta page confirming a caption character limit was found in this "
            "session. Paste and check the composer directly.",
        ),
    ]

    return {
        "platform": "meta_instagram",
        "platform_label": "Meta / Instagram",
        "fields": [f.to_dict() for f in fields],
        "cta": variant.get("cta", ""),
        "asset_checklist": [
            "Image: 4:5 ratio, 1440×1800px recommended, JPG or PNG, max 30MB "
            "(source: Meta ads guide, Instagram feed image spec).",
            "Hashtags: Meta's ad-creative guidance lists a maximum of 30 per post.",
            "This export does not generate or validate images/video, prepare those "
            "assets separately and attach them in Meta Business Suite.",
        ],
        "source_note": (
            "Character limits above marked as confirmed come from Meta's published ad "
            "specs. Hard enforcement may still differ in the live composer, treat these "
            "as strong guidance, not a guarantee."
        ),
    }


def format_for_google_ads(variant: dict) -> dict:
    """Source: Google Ads Help, "About responsive search ads"
    (support.google.com/google-ads/answer/7684791), read 2026-11-03.
    RSA requires 3-15 headlines (<=30 chars each) and 2-4 descriptions
    (<=90 chars each). This content_pack variant only has one headline
    and one body, so this produces ONE validated headline/description
    pair plus a clear reminder of the minimum count, it does not
    fabricate extra headline variants by chopping up unrelated sentences,
    since those wouldn't have been reviewed as real ad copy.
    """
    headline = variant.get("headline", "") or ""
    body = variant.get("body", "") or ""

    headline_fit = _truncate(headline, 30)
    description_fit = _truncate(body, 90)

    fields = [
        FieldCheck(
            "Headline 1", headline_fit, 30, True,
            "Truncated from the generated headline if it exceeded 30 characters."
            if len(headline) > 30 else "",
        ),
        FieldCheck(
            "Description 1", description_fit, 90, True,
            "Truncated from the generated body copy if it exceeded 90 characters."
            if len(body) > 90 else "",
        ),
    ]

    return {
        "platform": "google_ads",
        "platform_label": "Google Ads (Responsive Search Ads)",
        "fields": [f.to_dict() for f in fields],
        "cta": variant.get("cta", ""),
        "requirements": [
            "RSAs require a MINIMUM of 3 headlines (≤30 chars each) and 2 descriptions "
            "(≤90 chars each) to serve, up to 15 headlines / 4 descriptions are allowed.",
            "This export gives you one validated headline and description as a starting "
            "point. Write 2+ more headline variants and 1+ more description directly in "
            "Google Ads Editor, don't just repeat this one.",
            "Path fields (optional, shown after your domain) are limited to 15 characters "
            "each.",
        ],
        "asset_checklist": [
            "No image/video required for a standard RSA text ad.",
            "Have your Final URL ready, this export does not generate or validate one.",
        ],
        "source_note": (
            "Character and count limits above are from Google's official RSA help page, "
            "not guessed."
        ),
    }


def format_for_tiktok_ads(variant: dict) -> dict:
    """Source: TikTok for Business Help, "TikTok Auction In-Feed Ads"
    (ads.tiktok.com/help, last updated per the page: June 2026), read
    2026-11-03, for video specs. TikTok's official ad-text character
    limit and CTA button list were NOT found on any page reachable in
    this session (TikTok's ad-creation help content did not surface them)
   , left unconfirmed rather than guessed.
    """
    body = variant.get("body", "") or ""
    cta = variant.get("cta", "") or ""

    fields = [
        FieldCheck(
            "Ad text", body, None, False,
            "No official TikTok character limit was found in this session, paste into "
            "TikTok Ads Manager and check the live counter there.",
        ),
    ]

    return {
        "platform": "tiktok_ads",
        "platform_label": "TikTok Ads",
        "fields": [f.to_dict() for f in fields],
        "cta": cta,
        "cta_note": (
            "TikTok Ads Manager uses a fixed CTA button dropdown (not free text in most "
            "placements). The exact option list wasn't confirmed from an official source "
            "this session, pick the closest match to this suggested CTA "
            f"(“{cta}”) in Ads Manager."
            if cta
            else "TikTok Ads Manager uses a CTA button dropdown, pick one in Ads Manager."
        ),
        "asset_checklist": [
            "Video: 9:16 vertical recommended, minimum 540×960px (1080×1920 "
            "recommended), up to 10 minutes, max 500MB, .mp4/.mov/.mpeg/.3gp/.avi "
            "(source: TikTok Auction In-Feed Ads spec page).",
            "Minimum recommended resolution 720p per TikTok's creative best-practices page.",
            "This export does not generate or validate video, prepare it separately.",
        ],
        "source_note": (
            "Video specs above are from TikTok's official ad-spec page. Ad text limit and "
            "CTA list are flagged unconfirmed on purpose, verify directly in TikTok Ads "
            "Manager."
        ),
    }


PLATFORM_FORMATTERS = {
    "meta_instagram": format_for_meta_instagram,
    "google_ads": format_for_google_ads,
    "tiktok_ads": format_for_tiktok_ads,
}


def format_content_pack_for_platform(content: dict, platform: str) -> dict:
    """content is a content_pack deliverable's content dict
    (creative_brief, variants, calendar_notes). Returns one formatted
    export per variant. Raises KeyError for an unknown platform, callers
    should validate against PLATFORM_FORMATTERS.keys() first."""

    formatter = PLATFORM_FORMATTERS[platform]
    variants = content.get("variants") or []
    return {
        "platform": platform,
        "creative_brief": content.get("creative_brief", ""),
        "variant_exports": [formatter(v) for v in variants],
    }
