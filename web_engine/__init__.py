"""
🌌 Orion × Nebula Web Engine Package
Production-grade Playwright automation substrate with Page Object Model,
stealth anti-bot evasions, session state persistence, and in-memory CDP perception.
"""

from .config import BrowserConfig, DEFAULT_CONFIG
from .exceptions import WebEngineError, SelectorNotFoundError, SessionExpiredError, BotDetectionTriggeredError
from .browser_manager import BrowserManager
from .data_handler import DataHandler
from .pages.base_page import BasePage
from .pages.portal_search_page import PortalSearchPage
from .pages.catalog_scraper_page import CatalogScraperPage

__all__ = [
    "BrowserConfig",
    "DEFAULT_CONFIG",
    "BrowserManager",
    "DataHandler",
    "BasePage",
    "PortalSearchPage",
    "CatalogScraperPage",
    "WebEngineError",
    "SelectorNotFoundError",
    "SessionExpiredError",
    "BotDetectionTriggeredError"
]
