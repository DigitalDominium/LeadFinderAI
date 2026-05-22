from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import urlparse

import requests


def clean_html(text: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def ensure_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    return url


def scan_website(url: str) -> dict[str, Any]:
    url = ensure_url(url)
    if not url:
        raise ValueError("Website URL is empty.")

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DominiumLeadRadar/2.0; +https://digitaldominium.org)"
    }
    response = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
    response.raise_for_status()

    html = response.text[:200000]
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    desc_match = re.search(r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html)
    title = clean_html(title_match.group(1)) if title_match else ""
    description = unescape(desc_match.group(1)).strip() if desc_match else ""
    text = clean_html(html)
    summary = " ".join([title, description, text[:1200]]).strip()

    return {
        "url": response.url,
        "title": title,
        "description": description,
        "summary": summary[:1800],
        "status_code": response.status_code,
    }
