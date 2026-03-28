import re
import logging

logger = logging.getLogger(__name__)

# Fallback implementations (Pure Python)
def _fallback_only_digits(s: str) -> str:
    return re.sub(r'\D+', '', s or '')

def _fallback_format_indian_mobile(s: str) -> str:
    d = _fallback_only_digits(s)
    if d.startswith('91') and len(d) >= 12:
        d = d[2:]
    if d.startswith('0') and len(d) >= 11:
        d = d[1:]
    return d

try:
    # Attempt to load Mojo compiled extension (e.g., via CPython extension or Mojo magic module)
    # This simulates the interop layer where Python calls the compiled Mojo binary.
    import fast_digits_mojo
    only_digits = fast_digits_mojo.only_digits
    format_indian_mobile = fast_digits_mojo.format_indian_mobile
    MOJO_AVAILABLE = True
    logger.info("Successfully loaded Mojo accelerator for fast_digits.")
except ImportError:
    logger.debug("Mojo accelerator 'fast_digits_mojo' not found. Using pure Python fallback.")
    only_digits = _fallback_only_digits
    format_indian_mobile = _fallback_format_indian_mobile
    MOJO_AVAILABLE = False
