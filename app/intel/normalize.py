import re
import unicodedata

# ---------------------------
# Normalization utilities
# ---------------------------

ZERO_WIDTH = dict.fromkeys(map(ord, [
    '\u200B', # ZERO WIDTH SPACE
    '\u200C', # ZERO WIDTH NON-JOINER
    '\u200D', # ZERO WIDTH JOINER
    '\u2060', # WORD JOINER
    '\uFEFF', # ZERO WIDTH NO-BREAK SPACE
]), None)

# Map common Indic digit ranges to ASCII 0-9
_INDIC_DIGIT_RANGES = [
    ('\u0966', '\u096F'),  # Devanagari 0-9
    ('\u0BE6', '\u0BEF'),  # Tamil 0-9
    ('\u0DE6', '\u0DEF'),  # Sinhala 0-9 (occasionally appears)
    ('\u0CE6', '\u0CEF'),  # Kannada 0-9
    ('\u0C66', '\u0C6F'),  # Telugu 0-9
    ('\u0D66', '\u0D6F'),  # Malayalam 0-9
    ('\u0AE6', '\u0AEF'),  # Gujarati 0-9
    ('\u0A66', '\u0A6F'),  # Gurmukhi 0-9
]

_digit_map = {}
for start, end in _INDIC_DIGIT_RANGES:
    for i, cp in enumerate(range(ord(start), ord(end) + 1)):
        _digit_map[cp] = ord('0') + i

def normalize_text(s: str) -> str:
    """
    - NFC normalize
    - strip zero width chars
    - convert Indic digits to ASCII
    - collapse repeated whitespace & separators
    """
    if not s:
        return s
    s = unicodedata.normalize('NFC', s)
    s = s.translate(ZERO_WIDTH)
    s = s.translate(_digit_map)
    # unify weird hyphens/dots that scammers insert between digits/handles
    s = s.replace('·', '.').replace('•', '.').replace('．', '.').replace('–', '-').replace('—', '-')
    # ✅ Conservative deobfuscation for common scams:
    # Only replace bracketed (at)/(dot) forms to avoid breaking normal text.
    s = re.sub(r"\s*(\(|\[)\s*at\s*(\)|\])\s*", " @", s, flags=re.I)
    s = re.sub(r"\s*(\(|\[)\s*dot\s*(\)|\])\s*", ".", s, flags=re.I)
    # collapse spaces around typical separators to help regexes
    s = re.sub(r'\s+', ' ', s)
    return s

def digits_only(s: str) -> str:
    return re.sub(r'\D+', '', s or '')
