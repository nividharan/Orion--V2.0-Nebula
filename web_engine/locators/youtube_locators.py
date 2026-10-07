"""
🌌 Orion × Nebula Web Engine - YouTube Locators Registry
Role, aria-label, and structural locators for YouTube portal.
"""

YOUTUBE_SEARCH_BAR = [
    {"role": "combobox", "name": "Search"},
    {"css": "input#search"},
    {"css": "input[name='search_query']"}
]

YOUTUBE_SEARCH_BUTTON = [
    {"role": "button", "name": "Search"},
    {"css": "button#search-icon-legacy"}
]

YOUTUBE_VIDEO_CARDS = [
    {"css": "ytd-video-renderer"},
    {"css": "ytd-rich-item-renderer"}
]

YOUTUBE_VIDEO_TITLE = [
    {"css": "a#video-title"},
    {"xpath": ".//a[@id='video-title']"}
]

YOUTUBE_CHANNEL_NAME = [
    {"css": "ytd-channel-name a"},
    {"xpath": ".//ytd-channel-name//a"}
]
