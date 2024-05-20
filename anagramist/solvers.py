import logging
from os import PathLike

from accelerate import PartialState
from accelerate.utils import set_seed

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    LogitsProcessorList,
)

from .logits import LetterBankLogitsProcessor


logger = logging.getLogger(__name__)


class GenerativeSolver:
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
        # logits probabilities are all conditional on the next token
        # so the input needs ~ 1 token of padding in order to get the actual first token
        input_ids = self.tokenizer(
            "   " + candidates, return_tensors="pt"
        ).input_ids
        outputs = self.model(input_ids)
        probabilities = torch.log(outputs.logits.softmax(dim=-1) / 100).detach()

        # collect the probability of the generated token -- probability at index 0 corresponds to the token at index 1
        probabilities = probabilities[:, :-1, :]
        input_ids = input_ids[:, 1:]
        gen_probs = torch.gather(probabilities, 2, input_ids[:, :, None]).squeeze(-1)

        batch = []
        for input_sentence, input_probs in zip(input_ids, gen_probs, strict=True):
            text_sequence = []
            for token, p in zip(input_sentence, input_probs, strict=True):
                if token not in self.tokenizer.all_special_ids:
                    text_sequence.append((self.tokenizer.decode(token), p.item()))
            batch.append(text_sequence)
        return batch
