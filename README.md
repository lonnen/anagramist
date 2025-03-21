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

Note that your scores may vary from the examples. Exact scores should be deterministic within the same version of the program, but may vary slightly between versions, depending on what source code was modified.

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

## How to (try) to solve a Cryptoanagram

In [Dinocomics 1663](https://qwantz.com/index.php?comic=1663), [Ryan North](https://www.ryannorth.ca/about/) describes a puzzle by presenting a bag of letters and asking the player to reconstruct some original text by arranging the letters and adding spaces as needed.

We call this kind of probelm an anacryptogram. We call the specific anacryptogram defined in Comic 1663 "c1663" or the "Qwantzle". In addition to the letters, Ryan North confirmed all words in the solution are in [Jadrian's Qwantz Corpus](http://www.afifthofnothing.com/qwantzstuff/qwantzcorpus), among other useful constraining hints.

This tool searches for the original sentence by constructing a tree with the following properties:

* Every node is an arrangement of some of the characters into words from the corpus separated by spaces
* The tree is rooted in an empty sentence
* Every node has a child node for each word in the corpus that can be spelled with the remaining letters in the pool
* Apostraphes are considered part of the containing word
* All other punctuation is considered a word itself (e.g. "I can't, you must!" is the node `["I", "can't", ",", "you", "must", "!"]`).

This greatly reduces the search space versus arranging individual letters, but it's still quite inefficient. The majority of the branches will be nonsensical, and the size of the tree grows rapidly with larger pools of letters derived from longer chunks of text.

To constrain the search space further and focus on more fruitful branches, this program explores this tree using two heuristics:

1. Placed letters are sent `Oracle` that outputs a score between 0 and 1 indicating, roughly, is it a valid english sentence that someone might write.
2. A set of easily computable constraints are evaluated, and violations reducing the score of a candidate to 0.

In earlier versions of this program there were many `Oracle`s that used word length, letter frequency, or other attributes. The current version of `anagramist` has replaced all these with a single `TransformerOracle` wrapping a locally-runable LLM. Candidates are fed to the model, and the model is interrogated to get a score that has useful properties similar to, but which is wholly distinct from, the probability that the LLM would generate that specific sequence of tokens using BEAM search. These token level probabilities are consolidated into word-level probabilities and then combined to create a single candidate score.

The tree, including candidate scores, are stored in a SQL lite database for local persistence between runs.

The program searches in three steps:

1. Selection - sample from the stored tree (weighted by oracle score) to select a node that is both already explored and the parent of unexplored child nodes
2. Expansion - starting from the selected node, take a deep uniform random walk by adding words until a node fails soft validation, indicating that no placement of additional letters could produce a valid solution
3. Backpropogation - hard validate the candidate and, if it meets all the criteria that can be computationally verified, record the answer as a solution and halt. If not, score each node along the explored path. Record the scores. Repeat starting from 1.

This algorithm was inspired by the Monte Carlo Tree Search algorithm and Upper Confidence Bounds Applied to Trees algorithm. In practice it could also be said to resemble a version of stochastic beam search that stores all states in a database. 

Solving Comic 1663 is the main goal, but it is interesting to have a generic method that can be evaluated against other texts.

A note on the specifics of Comic 1663. It has 97 letters and 4 characters of punctuation. Given the size of words in the corpus it's not unreasonable that a valid answer could have between 16 and 24 words. Jadrian's corpus is known to contain all the words in the original sentence, and has more than 15,000 words. This puts a naive upper bound of 1.6e100 candidates to check. By applying hints given by the puzzle creator we can reduce the vocabulary to some ~13,500 unique words, which is only a modest improvement on this loose upper bound. Since the first word is known to be "I" a manual inspection and annotation of all 13,500 possible second words has restricted the space of possible second words to 1,422 possible entries.

These intermediate results and annotations are not yet stored in this repository.

# Data Sources

Because this has been going on a long time, some of the original data sources have decayed and fallen off the internet. Backup copies have been archived in the [Cryptoanagram](https://github.com/lonnen/cryptoanagram/) repo, along with any tools that were used to clean those data sets.

## Hints and Clues

Ryan North has given several constraints in the news post accompanying [Comic 1665](http://qwantz.com/index.php?comic=1665):

- All words in the solution are dictionary words.
- What's more, all words in the solution are in the Jadrian's awesome [Qwantz Corpus](http://cs.brown.edu/~jadrian/docs/etc/qwantzcorpus)[link has been 404 since at least 2020]!
- The solution is natural-sounding, reasonably-grammatical dialogue that T-Rex would say, using phrasing that T-Rex would use.
- The punctuation :,!! is in the solution, in that order!
- The longest word in the solution is 11 characters long.
- The solution does not refer to anagrams or puzzles or winning t-shirts.
- However, what T-Rex is saying is directly related to the content of the comic the puzzle appears in.
- The letters given are case-sensitive!
- The first word of the solution is "I".
- I tested out [Joel's puzzle-solving tool](http://afifthofnothing.com/anacryptogram.html) and it does let you know that the correct answer works!
- The solution is long enough to make pure brute force not really feasible. You'll have to use your head.

Ryan North followed up with additional clues accompanying [Comic 1666](http://qwantz.com/index.php?comic=1666):

- Paul Stansifer has released [Qwantzle Data](http://github.com/paulstansifer/qwantzle_data), which scraped [the OhNoRobot search engine](http://www.ohnorobot.com/index.pl?comic=23) to gather Dinosaur Comics text
- Ryan [released the Dinosaur Comics text as XML](http://www.qwantz.com/everywordindinosaurcomicsOHGOD.xml) which is redundant with Paul's work (above)
- The longest word is 11 characters long, the second longest is 8 characters long, and they're side-by-side in the solution

Additionally at TCAF in 2012 Ryan said to me personally that the solution would make a good epitaph. He also told me that several people had come up with valid sentences that passed all the hints and constraints but which were not the original sentence and so did not win the prize.

In 2023 Ryan provided [one more Qwantzle clue](https://www.qwantz.com/index.php?comic=4005#blogpost): The final letter is "w".

Combined with earlier clues this means the sentence ends in "w!!". Presumably this will rule out all the current false-positives that have been submitted.