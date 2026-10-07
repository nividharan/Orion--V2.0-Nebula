"""
🌌 Orion × Nebula Web Engine - YouTube Selectors Registry
Role, aria-label, and structural selectors for YouTube portal.
"""

YOUTUBE_SEARCH_BAR = [
    {"role": "combobox", "name": "Search"},
    {"css": "input#search"},
    {"css": "input[name='search_query']"},
    {"xpath": "//input[@id='search' or @name='search_query']"}
]

YOUTUBE_SEARCH_BUTTON = [
    {"role": "button", "name": "Search"},
    {"css": "button#search-icon-legacy"},
    {"xpath": "//button[@id='search-icon-legacy']"}
]

YOUTUBE_VIDEO_CARDS = [
    {"css": "ytd-video-renderer"},
    {"css": "ytd-rich-item-renderer"},
    {"xpath": "//ytd-video-renderer"}
]

YOUTUBE_VIDEO_TITLE = [
    {"css": "a#video-title"},
    {"xpath": ".//a[@id='video-title']"}
]

YOUTUBE_CHANNEL_NAME = [
    {"css": "ytd-channel-name a"},
    {"xpath": ".//ytd-channel-name//a"}
]
