import logging
from collections import Counter
from os import PathLike

from accelerate import PartialState
from accelerate.utils import set_seed

from torch import FloatTensor, LongTensor, gather
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    LogitsProcessorList,
    LogitsProcessor,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
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
        self.distributed_state = PartialState(cpu=use_cpu)

        logger.warning(
            f"device: {self.distributed_state.device}, 16-bits inference: {fp16}"
        )

        # Initialize the model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_name_or_path)
        # tokenizer = GPT2Tokenizer.from_pretrained(args.model_name_or_path)
        # model = OPTForCausalLM.from_pretrained(args.model_name_or_path)

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

    def generate_solutions(self, letters):
        # prompt_text = """Indeed! In comparison being an anagramist today is totally boring, as nobody is encoding anagramistal discoveries into word games anymore."""
        prompt_text = " "

        inputs = self.tokenizer(
            prompt_text, return_tensors="pt", add_special_tokens=False
        )

        logits = LogitsProcessorList([
            LetterBankLogitsProcessor(letters, self.tokenizer.eos_token_id, self.tokenizer.decode),
        ])
        if self.c1663:
            logits.extend(LogitsProcessorList())

        output_sequences = self.model.generate(
            inputs.input_ids,
            # BEAM search params
            num_beams=10,
            num_return_sequences=5,
            no_repeat_ngram_size=1,
            remove_invalid_values=True,
            logits_processor=logits,
            # tokens ~= 4 english chars, and valid answers must use exactly all the letters
            max_length=int(len(letters) / 3) + len(inputs["input_ids"][0]),
        )

        for output in output_sequences:
            print(f"=== CANDIDATE SOLUTION ===")

            # Decode text
            text = self.tokenizer.decode(
                output,
                clean_up_tokenization_spaces=True,
                add_special_tokens=False,
            )

            print(text + "\n")
        return output_sequences


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


class LetterBankLogitsProcessor(LogitsProcessor):
    r"""
    [`LetterBankLogitsProcessor`] restricts sampling to ensure output can be assembled out of letters in the bank.

    Args:
        letter_bank (`List[]`)
    """

    def __init__(self, letter_bank: str, eos_token_id: int, decode_function):
        self.letter_bank = Counter(letter_bank)
        # ensure eos_token_id is not suppressed
        self.eos_token_id = eos_token_id
        self.decode = decode_function

    def __call__(self, input_ids: LongTensor, scores: FloatTensor) -> FloatTensor:
        print("==SCORES==")
        for tokens in input_ids.tolist():
            # calculate letters used by current input_ids
            candidate = self.decode(tokens)
            candidate_letters = Counter(candidate)
            candidate_letters[' '] = 0 # remove empty spaces
            subset = self.letter_bank < candidate_letters
            print(r"{}: {}".format(subset, candidate.strip()))
            print(tokens)
            
        # calculate letters used in proposed tokens
        # calculate which ones fit in the remaining letters
        return scores
