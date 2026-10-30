"""Optional Playwright import so unit tests run without a browser installed."""
try:
    from playwright.sync_api import Error as PlaywrightError
except Exception:

    class PlaywrightError(Exception):
        """Fallback exception when Playwright is unavailable."""