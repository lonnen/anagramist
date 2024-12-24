#!/usr/bin/env python3

from collections import Counter
import sys

usage = """Usage: ./unique_chars.py text_to_analyze.txt
"""

if __name__ == "__main__":
    if len(sys.argv) < 1:
        print(usage)
        exit(1)
    
    text_file = sys.argv[1]
    chars = Counter()
    line_count = 0
    with open(text_file) as tf:
        for line in tf:
            chars.update(line.strip())
            line_count += 1
    chars["\n"] = 0
    chars[" "] = 0
    uniq_chars = "".join(sorted(chars.keys()))
    print(f"Read {line_count} from {text_file}")
    print(f"{len(uniq_chars)} unique characters: {uniq_chars}")
    print("Character counts:")
    for c in uniq_chars:
        if chars[c] == 0:
            continue
        print(f"{c}: {chars[c]}")