import logging

from transformers import AutoModelForCausalLM, AutoTokenizer

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def generate_text(letters, model_name_or_path, k, penalty_alpha, p, seed, use_cpu, fp16):
    # Initialize the distributed state.
    distributed_state = PartialState(cpu=args.use_cpu)

    logger.warning(f"device: {distributed_state.device}, 16-bits inference: {args.fp16}")

    if args.seed is not None:
        set_seed(args.seed)

    # Initialize the model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path)
    model = AutoModelForCausalLM.from_pretrained(args.model_name_or_path)

    # tokenizer = GPT2Tokenizer.from_pretrained(args.model_name_or_path)
    # model = OPTForCausalLM.from_pretrained(args.model_name_or_path)
    # Set the model to the right device
    model.to(distributed_state.device)

    if args.fp16:
        model.half()

    logger.info(args)
    prompt_text = args.prompt if args.prompt else input("Model prompt >>> ")

    inputs = tokenizer(prompt_text, return_tensors="pt", add_special_tokens=False)
    inputs = {key: value.to(distributed_state.device) for key, value in inputs.items()}

    output_sequences = model.generate(
        **inputs,
        max_length=args.length + len(inputs["input_ids"][0]),
        penalty_alpha=args.penalty_alpha,
        top_k=args.k,
    )

    generated_sequences = []
    for generated_sequence_idx, generated_sequence in enumerate(output_sequences):
        print(f"=== GENERATED SEQUENCE {generated_sequence_idx + 1} ===")
        generated_sequence = generated_sequence.tolist()

        # Decode text
        text = tokenizer.decode(generated_sequence, clean_up_tokenization_spaces=True, add_special_tokens=False)

        # Remove all text after the stop token
        text = text[: text.find(args.stop_token) if args.stop_token else None]

        # Add the prompt at the beginning of the sequence. Remove the excess text that was used for pre-processing
        total_sequence = (
            prompt_text + text[len(tokenizer.decode(inputs["input_ids"][0], clean_up_tokenization_spaces=True)) :]
        )

        generated_sequences.append(total_sequence)
        print(total_sequence)

    return generated_sequences
