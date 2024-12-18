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
python -m anagramist candidates --trim I\ cannot # delete all children of "I cannot" but leave the status untouched
python -m anagramist candidates --trim -status 7 I\ cannot # delete all children of "I cannot" and set its status to 7 so it will be ignored
```

```bash
python -m anagramist candidates I\ cannot # -> 
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

```bash
python -m anagramist check I cannot know a wrong answer   
# ...
# Status | Score | Sentence
# -------------------------
#    1   | - inf | I cannot know a wrong answer
#    1   | - inf | I cannot know a wrong
#    0   | -40.2 | I cannot know a
#    0   | -31.7 | I cannot know
#    0   | -19.2 | I cannot
#    0   | - 9.1 | I

python -m anagramist check --candidate-only I cannot know a wrong answer
# Status | Score | Sentence
# -------------------------
#    1   | - inf | I cannot know a wrong answer

# output answers for other tools with --json
python -m anagramist check --candidate-only --json I cannot know a wrong answer > output.json
# less output.json
# [["I cannot know a wrong answer", 0, 0, 0, 0, -Infinity, 1]]

# fill in a candidate walk, setting the terminal node artifically to 7 (Manual Intervention)
python -m anagramist check I merged billion bit national sonnets cares vessel darned tile hold yuo
python -m anagramist candidated -status 7 I merged billion bit national sonnets cares vessel darned tile hold yuo
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

## General approach

Someone reduces a sentence to a scrabble-style bag of letters (and punctuation), and asks you to derive the original sentence. You can place as many spaces as you need. All valid words that may be played are already defined.

We define a search tree rooted in `<start-of-sentence>` with nodes extending from there defined by the set of words that can be formed with the remaining letters. We treat apostraphes as part of the containing word, and other punctuation as words unto themselves (e.g. "I can't, you must!" is `["I", "can't", ",", "you", "must", "!"]`).

The majority of the branches in this tree will be nonsensical, and therefor could not ever be the original solution (assuming the original is a reasonably well formed english sentence such as the ones coming from existing Dinosaur Comics). There are many heuristic metrics that could be used to evaluate these candidates during the tree search - we use two types: first we pass the string to an `Oracle` that returns a float. Second are a set of easily computable constraints that can reduce the score of a candidate (generally to 0).

`Oracle` scores may be based on word length, letter frequency, or any other attribute. In practice, we only use a TransformerOracle that consults Microsoft's Phi-1.5 LLM model to get score that has useful properties similar to, but which is wholly distinct from, the probability that the LLM would generate that sequence of tokens. Then those are consolidated into word-level probabilities and combined to create a single candidate score.

Generally the algorithm proceeds in three steps:

1. Selection - take a random walk over the tree until an unexpanded node is reach. The randomness is weighted by the score of each node with a default score used for unexpanded nodes
2. Expansion (& Simulation) - starting from the selected node, take a deep uniform random walk across the solution space until a candidate fails soft validation, which indicates that no placement of additional letters could produce the solution
3. Backpropogation - if the candidate meets all the criteria that can be computationally verified (called hard validation) record the answer and halt. If not, score the candidate and work backwards to the selected node, recording scores for each intermediary node along the way

This algorithm is a Monte Carlo Tree Search process loosly adapted from the Upper Confidence Bounds applied to Trees algorithm for use in a non-game context, with the TransformerOracle heuristic (constrained by other simple to compute heuristics) standing in for the ratio of wins and losses.

Solving Comic 1663 is the main goal, but it is useful to have a generic method that can be evaluated against shorter sentences.

Comic 1663 has 97 letters and 4 characters of punctuation, and it's not unreasonable that a valid answer could have between 16 and 24 words. Jadrian's corpus is known to contain all the words in the original sentence, and has more than 15,000 words. This puts a conservative upper bound of 1.6e100 on things. By applying hints given by the puzzle creator for C1663 we can reduce the vocabulary to some ~13,500 unique words, which is modest improvement on this loose upper bound. Since the first word is known to be "I" a manual inspection and annotation of all 13,500 possible second words has restricted the space of possible second words to 1,422 possible entries. 

These intermediate results and annotations are not yet stored in this repository.