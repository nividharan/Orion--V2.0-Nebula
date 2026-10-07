"""
🌌 Orion × Nebula Web Engine - Base Selectors & Modals Registry
Contains multi-lingual cookie banners, dialog dismissers, and common UI controls.
Rule: Prioritize role, aria-label, data-testid, and visible text before CSS/XPath.
"""

# Cookie consent banners & privacy modals (Multi-lingual)
COOKIE_CONSENT_BUTTONS = [
    {"role": "button", "name": "Accept all"},
    {"role": "button", "name": "Accept all cookies"},
    {"role": "button", "name": "I agree"},
    {"role": "button", "name": "Agree"},
    {"role": "button", "name": "Allow all"},
    {"role": "button", "name": "Accept"},
    {"role": "button", "name": "OK"},
    {"css": "button[id*='accept']"},
    {"css": "button[class*='accept']"},
    {"css": "button[data-testid*='cookie-accept']"},
    {"xpath": "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]"}
]

# Generic modal close buttons
MODAL_CLOSE_BUTTONS = [
    {"role": "button", "name": "Close"},
    {"role": "button", "name": "Dismiss"},
    {"role": "button", "name": "Not now"},
    {"role": "button", "name": "Cancel"},
    {"css": "button[aria-label='Close']"},
    {"css": "button[aria-label='Dismiss']"},
    {"css": "button.close"},
    {"css": "button[data-testid*='close']"},
    {"css": "svg[data-testid*='close']"}
]

# Generic search input fields
GENERIC_SEARCH_INPUTS = [
    {"role": "searchbox"},
    {"role": "combobox"},
    {"css": "input[type='search']"},
    {"css": "input[name='q']"},
    {"css": "input[name='query']"},
    {"css": "input[name='search']"},
    {"css": "input[placeholder*='Search' i]"},
    {"xpath": "//input[contains(translate(@placeholder, 'SEARCH', 'search'), 'search')]"}
]
