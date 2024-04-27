# anagramist

[![PyPI](https://img.shields.io/pypi/v/anagramist.svg)](https://pypi.org/project/anagramist/)
[![Tests](https://github.com/lonnen/anagramist/actions/workflows/test.yml/badge.svg)](https://github.com/lonnen/anagramist/actions/workflows/test.yml)
[![Changelog](https://img.shields.io/github/v/release/lonnen/anagramist?include_prereleases&label=changelog)](https://github.com/lonnen/anagramist/releases)
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
