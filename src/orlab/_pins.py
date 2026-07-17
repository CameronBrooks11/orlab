"""sha256 pins for OpenRocket release jars.

The single source of truth for which jar bytes orlab trusts: ``fetch_jar``
verifies downloads against these, the cached-jar resolution step re-verifies
against them, and the integration suite consumes them for its matrix. CI keys
its jar caches on this file's hash, so pin changes invalidate stale caches
while refactors elsewhere leave ~250 MB of cached jars intact.

DEFAULT_VERSION is deliberately an explicit constant, not ``max(pins)``:
pinning a future release must never silently change every user's default.
"""

PINNED_SHA256 = {
    "15.03": "2bbc4b1b57d99fd169f4119e221b934f007b88c437295f388a81cd3df5da84e3",
    "22.02": "1e26b83abb6d846e63bcc560f6bf16afe9c370378b614c0aacbfc6ece4ae07c8",
    "23.09": "65cc0ab68a536fc33fc02a84c416725523a82745e100356efd9ff890b43bfcd0",
    "24.12": "4959b72f52f5f607941e9722abbb7b7f0c4a38ebbbf84204a329db9f31c4f897",
}

DEFAULT_VERSION = "24.12"
