from .logits import LetterBankLogitsProcessor
from .vocab import vocab

import logging
from collections import Counter
from os import PathLike

from accelerate import PartialState
from accelerate.utils import set_seed

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    LogitsProcessorList,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


class Solver:
    def __init__(
        self,
        model_name_or_path: str | PathLike[str],
        seed: int = None,
        use_cpu: bool = True,
        fp16: bool = False,
        c1663: bool = False,
    ) -> None:
        # Transformers Model Initialization
        self.distributed_state = PartialState(cpu=use_cpu)

        logger.warning(
            f"device: {self.distributed_state.device}, 16-bits inference: {fp16}"
        )

        # Initialize the model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_name_or_path)

        # Set the model to the right device
        self.model.to(self.distributed_state.device)

        self.fp16 = fp16
        if fp16:
            self.model.half()

        self.seed = seed
        if seed is not None:
            set_seed(seed)

        self.use_cpu = use_cpu
        self.c1663 = c1663

        # Puzzle Specific Initialization
        self.puzzle_context = ""
        if c1663:
            self.puzzle_context = """In comparison, being an anagramist today is totally boring, as nobody is encoding fundamental discoveries into word games anymore."""

    def generate_solutions(self, letters):
        prompt_text = self.puzzle_context

        inputs = self.tokenizer(
            prompt_text, return_tensors="pt", add_special_tokens=False
        )

        logits = LogitsProcessorList(
            [
                LetterBankLogitsProcessor(letters + prompt_text, self.tokenizer),
            ]
        )

        if self.c1663:
            logits.extend(LogitsProcessorList([]))

        output_sequences = self.model.generate(
            inputs.input_ids,
            # BEAM search params
            num_beams=10,
            num_return_sequences=5,
            no_repeat_ngram_size=1,
            remove_invalid_values=True,
            logits_processor=logits,
            # renormalization is recommended with beam search and heavy logits modification
            renormalize_logits=True,
            # tokens ~= 4 english chars, and valid answers must use exactly all the letters
            max_length=int(len(letters) / 3) + len(inputs["input_ids"][0]),
        )

        for output in output_sequences:
            logger.info("CANDIDATE SOLUTION: ")

            # Decode text
            text = self.tokenizer.decode(
                output,
                clean_up_tokenization_spaces=True,
                add_special_tokens=False,
            )
            logger.info(text + "\n")
        return output_sequences

    def probability_of_candidate(self, candidates):
        """Calculate the log probability of a given set of candidate sentences

        adapted from: https://discuss.huggingface.co/t/announcement-generation-get-probabilities-for-generated-output/30075/17
        """
        encoded_candidate = self.tokenizer(
            candidates, padding=True, return_tensors="pt"
        )
        outputs = self.model(encoded_candidate.input_ids)
        probabilities = torch.log(outputs.logits.softmax(dim=-1) / 100).detach()

        # collect the probability of the generated token -- probability at index 0 corresponds to the token at index 1
        probs = probs[:, :-1, :]
        input_ids = input_ids[:, 1:]
        gen_probs = torch.gather(probs, 2, input_ids[:, :, None]).squeeze(-1)

        batch = []
        for input_sentence, input_probs in zip(input_ids, gen_probs):
            text_sequence = []
            for token, p in zip(input_sentence, input_probs):
                if token not in self.tokenizer.all_special_ids:
                    text_sequence.append((self.tokenizer.decode(token), p.item()))
            batch.append(text_sequence)
        return batch


def validate_solution(
    letter_bank: str, candidate_sentence: str, c1663: bool = False
) -> bool:
    """Answers whether the candidate_sentence satisfies the constraints of the Qwantzle puzzle. Not all constraints can be checked computationally, but
    the following are checked:

        * The candidate_sentence uses exactly all of the characters from the letter_bank, not counting whitespace
        * The characters are case-sensitive
        * All the words are vocabulary.txt dictionary included in this library (1-grams from qwantz comics up to c1663)

    Additional constraints that are checked iff c1663:

        * The solution starts with "I"
        * The punctuation appears in the order :,!!
        * The longest word is 11 characters long
        * The second longest word is 8 characters, and occurs adjacent to the longest word

    Constraints that are not validated:

        * The solution is a natural-sounding, reasonably-grammatical dialogue that T-rex would say
        * The solution does not refer to anagrams or puzzles or winning t-shirts
        * The solution is directly related to the content of the comic 1663 "The Qwantzle"
        * The solution "would make a good epitaph"

    Constraints collected from https://github.com/lonnen/cryptoanagram/blob/main/README.md. There are multiple anagrams of c1663
    that will pass this function, which satisfy several of the "Constraints that are not validated", but which are not the solution.

    Args:
        letter_bank (`String`) - the letters available for the anagram. Spaces are ignored, so sentences may be passed directly
        candidate_sentence (`String`) - a string to validate against the constraints of the Qwantzle
        c1663 (`bool`) - whether or not to apply special constraints that only apply to comic 1663 "The Qwantzle"

    return (`bool`) - does the candidate sentence satisfy the constraints of the Qwantzle puzzle
    """
    bank = Counter(letter_bank)
    candidate = Counter(candidate_sentence)

    # strip whitespace
    bank[" "] = 0
    candidate[" "] = 0

    # first check - do they have the same numbers of specific letters?
    remaining_letters = bank.copy()
    remaining_letters.subtract(candidate_sentence)

    if not candidate == bank:
        return False

    # partition out the candidate sentence into words with some punctuation treated as its own words
    words = [""]
    for char in candidate_sentence:
        if char in set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'-"):
            words[-1] += char
        elif char == " ":
            # on whitespace, ensure the next word is a fresh, empty string
            # this is necessary for longer stretches of whitespace, or the case
            # of no whitespace around punctuation-that-is-itself-a-word
            if words[-1] != "":
                words.append("")
        else:
            # anything else is a word unto itself
            words.append(char)
            words.append("")

    # check that every word appears in the vocab list
    for w in words:
        if w is '': continue
        if w not in vocab:
            print(r"'{}' not in vocabulary".format(w))
            return False

    if not c1663:
        return True

    # From here out, only rules specific to comic 1663

    # practically this is unlikely to occur, since anything that got this far is using exactly all of the letters
    # but it will catch an input error where somehow letter_bank is also provided as candidate_sentence
    if len(words) < 2:
        return False

    if words[0] != "I":
        return False

    words_len = [len(w) for w in words]

    longest, second_longest = sorted(words_len)[:2]
    if longest != 11 or second_longest != 8:
        return False

    position_longest = words_len.index(11)
    if words_len[position_longest - 1] != 8 or words_len[position_longest + 1] != 8:
        return False

    return True


def generate_text(
    letters: str,
    model_name_or_path: str | PathLike[str],
    seed: int,
    use_gpu: bool = False,
    fp16: bool = False,
    c1663: bool = False,
):
    solver = Solver(model_name_or_path, seed, (not use_gpu), fp16, c1663)
    solver.generate_solutions(letters)
