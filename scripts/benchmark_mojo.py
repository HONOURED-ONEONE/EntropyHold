import time
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.intel.fast_digits_wrapper import (
    only_digits, 
    format_indian_mobile, 
    _fallback_only_digits, 
    _fallback_format_indian_mobile, 
    MOJO_AVAILABLE
)

def run_benchmark():
    print("==================================================")
    print("Mojo Accelerator Benchmark: String & Digit Parsing")
    print("==================================================")
    print(f"Mojo accelerator available: {MOJO_AVAILABLE}")
    
    test_cases = [
        "+91-98765-43210",
        "0 98765 43210",
        "Just some text with 12345 in it",
        "(91) 987 654 3210",
        "abc123def456",
        "  +91 999 888 7777 ",
        "Contact: 08001234567 for more info",
    ] * 20000  # 140,000 iterations
    
    print(f"\nBenchmarking '{len(test_cases)}' iterations...")
    
    # 1. Measure Pure Python Fallback
    start_py = time.monotonic()
    for s in test_cases:
        _ = _fallback_format_indian_mobile(s)
    py_time = time.monotonic() - start_py
    print(f"Pure Python (re.sub): {py_time:.4f} seconds")
    
    # 2. Measure Active Implementation (Mojo if available, otherwise identical to Python)
    start_act = time.monotonic()
    for s in test_cases:
        _ = format_indian_mobile(s)
    act_time = time.monotonic() - start_act
    print(f"Active Wrapper:       {act_time:.4f} seconds")

    if MOJO_AVAILABLE:
        speedup = py_time / act_time if act_time > 0 else 0
        print(f"\n--> Mojo Speedup: {speedup:.2f}x")
    else:
        print("\n--> Mojo Speedup: N/A (Running Python Fallback)")

if __name__ == "__main__":
    run_benchmark()
