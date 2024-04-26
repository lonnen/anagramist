import logging

from accelerate import PartialState
from accelerate.utils import set_seed

from transformers import AutoModelForCausalLM, AutoTokenizer

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class Solver:
    def __init__(
        self,
        model_name_or_path,
        k,
        p,
        penalty_alpha: float = 0.6,
        seed: int = None,
        use_cpu: bool = True,
        fp16: bool = False,
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

        self.seed = seed
        if seed is not None:
            set_seed(seed)

        self.fp16 = fp16
        if fp16:
            self.model.half()

        self.penalty_alpha = penalty_alpha
        self.k = k # how many words are considered at each step
        self.use_cpu = use_cpu

    def generate_solutions(self, letters):
        # prompt_text = """Indeed! In comparison being an anagramist today is totally boring, as nobody is encoding anagramistal discoveries into word games anymore."""
        prompt_text = ""

        inputs = self.tokenizer(
            prompt_text, return_tensors="pt", add_special_tokens=False
        )
        inputs = {
            key: value.to(self.distributed_state.device)
            for key, value in inputs.items()
        }

        output_sequences = self.model.generate(
            **inputs,
            # tokens ~= 4 english chars, and valid answers must use exactly all the letters
            max_length=(len(letters) / 3) + len(inputs["input_ids"][0]),
            penalty_alpha=self.penalty_alpha,
            top_k=self.k,
        )

        generated_sequences = []
        for generated_sequence_idx, generated_sequence in enumerate(output_sequences):
            print(f"=== GENERATED SEQUENCE {generated_sequence_idx + 1} ===")
            generated_sequence = generated_sequence.tolist()

            # Decode text
            text = self.tokenizer.decode(
                generated_sequence,
                clean_up_tokenization_spaces=True,
                add_special_tokens=False,
            )

            # Add the prompt at the beginning of the sequence. Remove the excess text that was used for pre-processing
            total_sequence = (
                prompt_text
                + text[
                    len(
                        self.tokenizer.decode(
                            inputs["input_ids"][0], clean_up_tokenization_spaces=True
                        )
                    ) :
                ]
            )

            generated_sequences.append(total_sequence)
            print(total_sequence)

        return generated_sequences


def generate_text(
    letters, model_name_or_path, k, penalty_alpha, p, seed, use_cpu, fp16
):
    solver = Solver(model_name_or_path, k, p, penalty_alpha, seed, use_cpu, fp16)
    solver.generate_solutions()
