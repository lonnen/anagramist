# anagramist

[![Tests](https://github.com/lonnen/anagramist/actions/workflows/test.yml/badge.svg)](https://github.com/lonnen/anagramist/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/lonnen/anagramist/blob/main/LICENSE)

a solver for [dinocomics 1663](https://qwantz.com/index.php?comic=1663)-style cryptoanagrams

## Installation

Install this library using `pip`:
```bash
pip install anagramist
```
## Usage

```bash
python -m anagramist solve --c1663 "ttttttttttttooooooooooeeeeeeeeaaaaaaallllllnnnnnnuuuuuuiiiiisssssdddddhhhhhyyyyyIIrrrfffbbwwkcmvg:,\!\!"
```

```bash
python -m anagramist trim I\ cannot # delete all children of "I cannot" and set its status to 7, so it will be ignored in future searches
python -m anagramist trim -s 0 I\ cannot # delete all chidlren of "I cannot" and set its status to 0 so it will be a candidate for future searches again
python -m anagramist prune doppleganger\ abce\ tipo # for each word, find all entries containing that word and trim them at the occurance of that word
```

```bash
python -m anagramist show I\ cannot # -> 
# Showing: 'I cannot'
# Child node demographics: (6011.0 children)
# -----------------------
# ('0',):   13 (0.2%)
# ('1',):    3 (0.0%)
# ('7',):    0 (0.0%)
# ('U',): 5995 (99.7%)

# Top next candidates:
# --------------------
# -14.30: I cannot show
# -17.10: I cannot readers
# -17.58: I cannot sudden
# -17.60: I cannot liable
# -18.36: I cannot void

# Top descendents: (mean score)
# ---------------
# -14.04: I cannot show some
# -14.30: I cannot show
# -16.61: I cannot show shall
# -16.73: I cannot show released
# -17.01: I cannot show some god
```

## Development

To contribute to this library, first checkout the code. Then create a new virtual environment:
```bash
cd anagramist
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
To run the tests:
```bash
pytest
```
