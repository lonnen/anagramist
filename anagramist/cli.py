from . import generate_text

import click


@click.group()
@click.version_option()
def cli():
    "a solver for dinocomics 1663-style cryptoanagrams"


@click.command()
@click.argument("letters")  # nee prompt
@click.option(
    "-m", "--model_name_or_path", default="mistralai/Mistral-7B-v0.1", type=click.Path()
)
@click.option("--k", type=int, default=0, help="Top-k parameter used for generation.")
@click.option("--penalty_alpha", type=float, default=0.0)
@click.option(
    "--p", type=float, default=0.9, help="Top P parameter used for nucles sampling"
)
@click.option("--seed", type=int, default=42, help="random seed for initialization")
@click.option(
    "--use_cpu",
    is_flag=True,
    help="Whether or not to use cpu. If set to False, "
    "we will use gpu/npu or mps device if available",
)
@click.option(
    "--fp16",
    is_flag=True,
    help="Whether to use 16-bit (mixed) precision (through NVIDIA apex) instead of 32-bit",
)
def solve(letters, model_name_or_path, k, penalty_alpha, p, seed, use_cpu, fp16):
    generate_text(letters, model_name_or_path, k, penalty_alpha, p, seed, use_cpu, fp16)
