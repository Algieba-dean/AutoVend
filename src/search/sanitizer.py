"""
Search Query and Result Sanitizer (src/search/sanitizer.py).

Guards the market intelligence pipeline against prompt injection, XSS payloads,
SQL injection vectors, and commercial advertisement noise.
"""

import re
from typing import List


class SearchSanitizer:
    """Sanitizes search queries and search result snippets."""

    # Malicious injection patterns
    _HTML_TAG_RE = re.compile(r"<[^>]+>", re.IGNORECASE)
    _JS_PAYLOAD_RE = re.compile(r"javascript:\s*", re.IGNORECASE)
    _ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
    _CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    _UNICODE_INVISIBLE_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")
    _SQLI_RE = re.compile(
        r"(\b(SELECT|INSERT|DELETE|UPDATE|DROP|UNION|ALTER|EXEC|EXECUTE)\b|--|\/\*|\*\/)",
        re.IGNORECASE,
    )
    _BOOLEAN_SQLI_RE = re.compile(
        r"(\b(OR|AND)\s+['\"0-9a-zA-Z_]+\s*=\s*['\"0-9a-zA-Z_]+|'\s*OR\s*'1'='1|1=1)",
        re.IGNORECASE,
    )
    _SHELL_META_RE = re.compile(r"[;`$\|&><]")

    # Commercial advertising noise filter patterns
    _AD_PATTERNS = [
        re.compile(r"加微信[：:\s]*[a-zA-Z0-9_\-]+", re.IGNORECASE),
        re.compile(r"招募代理|兼职赚钱|点击立即购买|博彩|真人百家乐", re.IGNORECASE),
        re.compile(r"广告合作[：:\s]*\S+", re.IGNORECASE),
    ]

    @classmethod
    def sanitize_query(cls, query: str, max_length: int = 200) -> str:
        """
        Sanitize an incoming search query string.

        Args:
            query: Raw user query or model query string.
            max_length: Maximum allowed character count.

        Returns:
            Clean, safe query string.
        """
        if not query:
            return ""

        # 1. Truncate
        cleaned = query.strip()[:max_length]

        # 2. Strip ANSI escape sequences and non-printable control characters
        cleaned = cls._ANSI_ESCAPE_RE.sub(" ", cleaned)
        cleaned = cls._CONTROL_CHAR_RE.sub(" ", cleaned)
        cleaned = cls._UNICODE_INVISIBLE_RE.sub("", cleaned)

        # 3. Strip HTML tags
        cleaned = cls._HTML_TAG_RE.sub(" ", cleaned)

        # 4. Strip JS URI schemes
        cleaned = cls._JS_PAYLOAD_RE.sub(" ", cleaned)

        # 5. Strip SQL injection keywords & boolean patterns
        cleaned = cls._SQLI_RE.sub(" ", cleaned)
        cleaned = cls._BOOLEAN_SQLI_RE.sub(" ", cleaned)

        # 6. Strip shell meta-characters
        cleaned = cls._SHELL_META_RE.sub(" ", cleaned)

        # 7. Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    @classmethod
    def sanitize_snippet(cls, text: str, max_length: int = 1000) -> str:
        """
        Sanitize an extracted snippet or article summary from external sources.

        Args:
            text: Raw extracted summary or snippet text.
            max_length: Maximum allowed character count.

        Returns:
            Clean, sanitized snippet without malicious tags or ad spam.
        """
        if not text:
            return ""

        cleaned = text.strip()[:max_length]

        # Strip ANSI escape sequences and non-printable control characters
        cleaned = cls._ANSI_ESCAPE_RE.sub(" ", cleaned)
        cleaned = cls._CONTROL_CHAR_RE.sub(" ", cleaned)
        cleaned = cls._UNICODE_INVISIBLE_RE.sub("", cleaned)

        # Strip HTML and JS
        cleaned = cls._HTML_TAG_RE.sub(" ", cleaned)
        cleaned = cls._JS_PAYLOAD_RE.sub(" ", cleaned)

        # Remove spam advertisement patterns
        for ad_re in cls._AD_PATTERNS:
            cleaned = ad_re.sub("[推广内容已过滤]", cleaned)

        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    @classmethod
    def sanitize_url(cls, url: str) -> str:
        """Validate and sanitize URL to prevent javascript: or file: attacks."""
        if not url:
            return ""
        clean_url = url.strip()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            return ""
        if cls._JS_PAYLOAD_RE.search(clean_url):
            return ""
        return clean_url
