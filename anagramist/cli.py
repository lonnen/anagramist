import click

from anagramist.persistentsearchtree import PersistentSearchTree

from . import search


@click.group()
@click.version_option()
def cli():
    "a solver for dinocomics 1663-style cryptoanagrams"


@click.command()
@click.argument("letters")  # nee prompt
@click.option(
    "-m", "--model_name_or_path", default="microsoft/phi-1_5", type=click.Path()
)
@click.option("--seed", type=int, default=42, help="random seed for initialization")
@click.option(
    "--use_gpu",
    is_flag=True,
    help="Whether or not to use cpu.",
)
@click.option(
    "--fp16",
    is_flag=True,
    help="""Whether to use 16-bit (mixed) precision (through NVIDIA apex) instead of 
    32-bit""",
)
@click.option(
    "--c1663",
    is_flag=True,
    help="""Leverage additional checks specific to the cryptoanagram puzzle in Dinosaur 
    comics 1663""",
)
def solve(letters, model_name_or_path, seed, use_gpu, fp16, c1663):
    click.echo(f"Assembling anagrams of:{"".join(sorted(letters))}")
    search(
        letters,
        model_name_or_path,
        seed,
        use_gpu,
        fp16,
        c1663=c1663,
    )


@click.command()
@click.argument("root")
def trim(root: str):
    click.echo(f"Trimming descendents of: '{root}'")
    pst = PersistentSearchTree()
    modified, deleted = pst.trim(root)
    if modified == 0 and deleted == 0:
        click.echo(f"Root '{root}' not found in tree.")
    if modified == -1 and deleted == 0:
        click.echo(f"Root '{root}' found but already trimmed")
    else:
        click.echo(f"Modified {modified} rows. Deleted {deleted} rows.")


cli.add_command(solve)
cli.add_command(trim)
