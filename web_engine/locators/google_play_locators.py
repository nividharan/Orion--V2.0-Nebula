"""
🌌 Orion × Nebula Web Engine - Google Play Store Locators
Role, aria-label, and structural locators with explicit names for Google Play Store.
"""

PLAY_STORE_SEARCH_BAR = [
    {"role": "combobox", "name": "Search"},
    {"role": "searchbox", "name": "Search"},
    {"css": "input[aria-label*='Search' i]"},
    {"css": "input.google-play-search"},
    {"css": "input[type='text'][jsname]"}
]

PLAY_STORE_SEARCH_BUTTON = [
    {"role": "button", "name": "Search"},
    {"css": "button[aria-label*='Search' i]"},
    {"css": "button[jsname]"}
]

PLAY_STORE_APP_CARDS = [
    {"css": "div[jscontroller] a[href*='/store/apps/details']"},
    {"css": "div.VfPpkd-EScbFb-JIbuQc a"},
    {"xpath": "//a[contains(@href, '/store/apps/details')]"}
]

PLAY_STORE_APP_TITLE = [
    {"css": "span.DdYX5"},
    {"css": "div.vWMdp"},
    {"xpath": ".//span[contains(@class, 'DdYX5') or contains(@class, 'vWMdp') or @role='text']"}
]

PLAY_STORE_APP_DEVELOPER = [
    {"css": "span.w2kb0b"},
    {"xpath": ".//span[contains(@class, 'w2kb0b')]"}
]

PLAY_STORE_APP_RATING = [
    {"css": "span.mUIrbf"},
    {"css": "div[aria-label*='stars']"},
    {"xpath": ".//span[contains(@class, 'mUIrbf') or contains(@aria-label, 'stars')]"}
]
