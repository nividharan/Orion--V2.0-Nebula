"""
🌌 Orion × Nebula Web Engine - Google Play Store Selectors
Role, aria-label, testid, and structural selectors for Google Play Store.
"""

# Search Bar on Google Play Store
PLAY_STORE_SEARCH_BAR = [
    {"role": "combobox", "name": "Search"},
    {"role": "searchbox"},
    {"css": "input[aria-label*='Search' i]"},
    {"css": "input[type='text'][jsname]"},
    {"css": "input.google-play-search"},
    {"xpath": "//input[@aria-label='Search' or contains(@placeholder, 'Search')]"}
]

# Search Submit / Trigger
PLAY_STORE_SEARCH_BUTTON = [
    {"role": "button", "name": "Search"},
    {"css": "button[aria-label*='Search' i]"},
    {"css": "button[jsname]"},
    {"xpath": "//button[@aria-label='Search']"}
]

# App Card Container & Elements in Results
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
