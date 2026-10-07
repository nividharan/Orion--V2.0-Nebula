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

# Multi-step CMP locators (e.g., OneTrust, Cookiebot, Didomi)
# When direct 'Reject all' is hidden behind a 'Manage preferences' / 'Settings' step:
CMP_MANAGE_PREFERENCES_LOCATORS = [
    {"role": "button", "name": "Manage preferences"},
    {"role": "button", "name": "Cookie Settings"},
    {"role": "button", "name": "Preferences"},
    {"role": "button", "name": "Customize"},
    {"role": "button", "name": "Manage Choices"},
    {"css": "#onetrust-pc-btn-handler"},
    {"css": "button.cookie-settings"},
    {"css": "button.cmp-preferences"}
]

CMP_CONFIRM_OR_REJECT_LOCATORS = [
    {"role": "button", "name": "Reject all"},
    {"role": "button", "name": "Reject All"},
    {"role": "button", "name": "Disable all"},
    {"role": "button", "name": "Confirm my choices"},
    {"role": "button", "name": "Save preferences"},
    {"css": "button.ot-pc-refuse-all-handler"},
    {"css": "#save-preference-btn-handler"},
    {"css": "button.cmp-save"}
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
