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

## General approach

In [Dinocomics 1663](https://qwantz.com/index.php?comic=1663), [Ryan North](https://www.ryannorth.ca/about/) describes a puzzle that asks you to reconstruct some original text given the characters and punctuation by arranging them and adding whitespace as needed. We call this kind of problem an anacryptogram and the specific problem set forth in Comic 1663 we call c1663 or the Qwantzle. Ryan has also provided a dictionary of valid words and several other constraining hints to make the Qwantzle, specifically, more tractable. 

In order to find the original sentence, we define a tree with the following properties:

* Every node is addressed by the string containing the arrangement of characters and spaces up to that point
* Every node has a child node for each word that can be spelled from the remaining pool of characters at that point
* The root of the tree is an empty sentence
* Apostraphes are part of the containing word
* All other punctuation is considered a word itself (e.g. "I can't, you must!" is the node `["I", "can't", ",", "you", "must", "!"]`).

With this definition the majority of the branches will be nonsensical, and the size of the tree will grow super-linearly with longer sentences and the larger pools of letters that come with them. To constrain exploration towards more fruitful branches, this program exploys two different heuristics:

First, the placed string is sent to an `Oracle` that returns a float. Second, a set of easily computable constraints are evaluated with violations reducing the score of a candidate (generally to 0).

In earlier versions of this approach `Oracle` scores were or be based on word length, letter frequency, or other attributes and multiple could be applied and combied together. `anagramist` simplifies this architecture to a single TransformerOracle wrapping an LLM model. Microsoft's Phi-1.5 LLM, by default, but any `transformers.py`compatible model could work. This model is interrogated to get score that has useful properties similar to, but which is wholly distinct from, the probability that the LLM would generate that specific sequence of tokens using beam search. These token level probabilities are consolidated into word-level probabilities and then combined to create a single candidate score.

Generally the algorithm proceeds in three steps:

1. Selection - randomly sample the tree, weighted by oracle score, to select a node that is both already explored and the parent of unexplored child nodes
2. Expansion - starting from the selected node, take a deep uniform random walk down the descendent nodes until a node fails soft validation, indicating that no placement of additional letters could produce the solution
3. Backpropogation - if the candidate meets all the criteria that can be computationally verified (called hard validation) record the answer and halt. If not, score each node along the explored path. Record the scores and start over.

This algorithm was inspired by the Monte Carlo Tree Search algoirhtm and loosly adapted from the Upper Confidence Bounds Applied to Trees algorithm for use in a non-game context, with the TransformerOracle heuristic and the more boolean hard constraint checks standing in for the ratio of wins and losses.

Solving Comic 1663 is the main goal, but it is interesting to have a generic method that can be evaluated against other sentences.

A note on the specifics of Comic 1663. It has 97 letters and 4 characters of punctuation, and given some summary stats of the size of words in the vocabulary it's not unreasonable that a valid answer could have between 16 and 24 words. Jadrian's corpus is known to contain all the words in the original sentence, and has more than 15,000 words. This puts a conservative upper bound of 1.6e100 on things. By applying hints given by the puzzle creator for c1663 we can reduce the vocabulary to some ~13,500 unique words, which is modest improvement on this loose upper bound. Since the first word is known to be "I" a manual inspection and annotation of all 13,500 possible second words has restricted the space of possible second words to 1,422 possible entries. 

These intermediate results and annotations are not yet stored in this repository.

## Hints and Clues

Ryan North has given several constraints in the news post accompanying [Comic 1665](http://qwantz.com/index.php?comic=1665):

- All words in the solution are dictionary words.
- What's more, all words in the solution are in the Jadrian's awesome [Qwantz Corpus](http://cs.brown.edu/~jadrian/docs/etc/qwantzcorpus>)!
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

Additionally at TCAF in 2012 Ryan said to me personally that the solution would make a good epitaph.

In 2023 Ryan provided [one more Qwantzle clue](https://www.qwantz.com/index.php?comic=4005#blogpost): The final letter is "w"

Combined with earlier clues this means the sentence ends in "w!!". Presumably this will rule out all the current false-positives that have been submitted.