"""
🌌 Orion × Nebula Web Engine - Base Locators Registry
Renamed from selectors to locators to avoid shadowing Python stdlib 'selectors'.
Contains safe cookie rejection, modal dismissers, and generic search inputs.
"""

# Cookie consent banners: Safely prioritize "Reject all" / "Necessary only" first!
# Scoped to dialog/modal containers to avoid clicking background buttons.
COOKIE_CONSENT_LOCATORS = [
    # 1. Prefer Reject / Necessary Only
    {"role": "button", "name": "Reject all"},
    {"role": "button", "name": "Reject all cookies"},
    {"role": "button", "name": "Only necessary"},
    {"role": "button", "name": "Reject"},
    {"role": "button", "name": "Decline"},
    {"css": "[role='dialog'] button[id*='reject']"},
    {"css": "div[aria-modal='true'] button[id*='reject']"},
    {"css": "#onetrust-reject-all-handler"},
    
    # 2. Accept if no reject available
    {"role": "button", "name": "Accept all"},
    {"role": "button", "name": "Accept all cookies"},
    {"role": "button", "name": "I agree"},
    {"css": "[role='dialog'] button[id*='accept']"},
    {"css": "#onetrust-accept-btn-handler"},
    {"css": "button.cookie-accept"}
]

# Modal close buttons scoped to dialog containers
MODAL_CLOSE_LOCATORS = [
    {"role": "button", "name": "Close"},
    {"role": "button", "name": "Dismiss"},
    {"role": "button", "name": "Not now"},
    {"css": "[role='dialog'] button[aria-label='Close']"},
    {"css": "div[aria-modal='true'] button[aria-label='Close']"},
    {"css": "button[data-testid='close-modal']"}
]

# Generic search input fields (always include name / placeholder to avoid matching multiple elements)
GENERIC_SEARCH_LOCATORS = [
    {"role": "searchbox", "name": "Search"},
    {"role": "combobox", "name": "Search"},
    {"css": "input[type='search']"},
    {"css": "input[name='q']"},
    {"css": "input[name='query']"},
    {"css": "input[placeholder*='Search' i]"}
]
