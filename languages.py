"""Gemini 3.5 Live Translate & Transcribe supported languages.

Compiled from the official GCP documentation:
    https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-5-live-translate#supported-languages

Each entry is (display_name, bcp47_code, is_preview).
"""

from typing import List, Dict

GEMINI_35_LIVE_LANGUAGES = [
    ("Afrikaans", "af", False),
    ("Akan", "ak", False),
    ("Albanian", "sq", False),
    ("Amharic", "am", False),
    ("Arabic", "ar", False),
    ("Armenian", "hy", False),
    ("Azerbaijani", "az", False),
    ("Basque", "eu", False),
    ("Belarusian", "be", False),
    ("Bengali", "bn", False),
    ("Bulgarian", "bg", False),
    ("Burmese (Myanmar)", "my", False),
    ("Catalan", "ca", False),
    ("Chinese (Simplified)", "zh-Hans", False),
    ("Chinese (Traditional)", "zh-Hant", False),
    ("Croatian", "hr", False),
    ("Czech", "cs", False),
    ("Danish", "da", False),
    ("Dutch", "nl", False),
    ("English", "en", False),
    ("Estonian", "et", False),
    ("Filipino", "fil", False),
    ("Finnish", "fi", False),
    ("French", "fr", False),
    ("Galician", "gl", False),
    ("Georgian", "ka", False),
    ("German", "de", False),
    ("Greek", "el", False),
    ("Gujarati", "gu", False),
    ("Hausa", "ha", False),
    ("Hebrew", "he", False),
    ("Hindi", "hi", False),
    ("Hungarian", "hu", False),
    ("Icelandic", "is", False),
    ("Indonesian", "id", False),
    ("Italian", "it", False),
    ("Japanese", "ja", False),
    ("Javanese", "jv", False),
    ("Kannada", "kn", False),
    ("Kazakh", "kk", False),
    ("Khmer", "km", False),
    ("Kinyarwanda", "rw", False),
    ("Korean", "ko", False),
    ("Lao", "lo", False),
    ("Latvian", "lv", False),
    ("Lithuanian", "lt", False),
    ("Macedonian", "mk", False),
    ("Malay", "ms", False),
    ("Malayalam", "ml", False),
    ("Marathi", "mr", False),
    ("Mongolian", "mn", False),
    ("Nepali", "ne", False),
    ("Norwegian", "no", False),
    ("Persian", "fa", False),
    ("Polish", "pl", False),
    ("Portuguese (Brazil)", "pt-BR", False),
    ("Portuguese (Portugal)", "pt-PT", False),
    ("Punjabi", "pa", False),
    ("Romanian", "ro", False),
    ("Russian", "ru", False),
    ("Serbian", "sr", False),
    ("Sindhi", "sd", False),
    ("Sinhala", "si", False),
    ("Slovak", "sk", False),
    ("Slovenian", "sl", False),
    ("Spanish", "es", False),
    ("Sundanese", "su", False),
    ("Swahili", "sw", False),
    ("Swedish", "sv", False),
    ("Tamil", "ta", False),
    ("Telugu", "te", False),
    ("Thai", "th", False),
    ("Turkish", "tr", False),
    ("Ukrainian", "uk", False),
    ("Urdu", "ur", False),
    ("Uzbek", "uz", False),
    ("Vietnamese", "vi", False),
    ("Zulu", "zu", False),
]

# Backwards compatibility alias
CHIRP3_HD_LANGUAGES = GEMINI_35_LIVE_LANGUAGES


def languages_json() -> List[Dict[str, object]]:
    """Return the language list as JSON-serialisable dicts for the frontend."""
    return [
        {"name": name, "code": code, "preview": preview}
        for (name, code, preview) in GEMINI_35_LIVE_LANGUAGES
    ]


def name_for_code(code: str) -> str:
    """Look up the display name for a BCP-47 code (falls back to the code)."""
    if code in ("cmn-CN", "zh-CN"):
        code = "zh-Hans"
    elif code in ("yue-HK", "zh-TW"):
        code = "zh-Hant"
    elif code.startswith("en-"):
        code = "en"

    for name, c, _ in GEMINI_35_LIVE_LANGUAGES:
        if c == code:
            return name
    return code
