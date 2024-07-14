import click

from collections import Counter
from typing import Set

from anagramist.persistentsearchtree import PersistentSearchTree
from anagramist import search, compute_valid_vocab, vocab, vocab_c1663


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
@click.option(
    "-s",
    "--status",
    type=int,
    default=7,
    help="Status code for the root node. Non-zero will prevent further searching.",
)
def trim(root: str, status):
    click.echo(f"Trimming descendents of: '{root}'")
    pst = PersistentSearchTree()
    modified, deleted = pst.trim(root, status=status)
    if modified == 0 and deleted == 0:
        click.echo(f"Root '{root}' not found in tree.")
        click.Context.exit(1)
    if modified == -1 and deleted == -1:
        click.echo(f"Root '{root}' found but already trimmed. No changes made.")
        click.Context.exit(1)
    if modified == -1 and deleted >= 0:
        click.echo(f"Root '{root}' already has correct status. Deleted {deleted} rows.")
        click.Context.exit(1)
    click.echo(f"{modified} rows modified. {deleted} rows deleted.")


@click.command()
@click.argument("root")
@click.option(
    "-c",
    "--candidates",
    type=int,
    default=5,
    help="Maximum number of child nodes to show",
)
@click.option(
    "--c1663",
    is_flag=True,
    default=True,
    help="""Leverage additional checks specific to the cryptoanagram puzzle in Dinosaur 
    comics 1663""",
)
def show(root: str, candidates, vocabulary: Set[str] = vocab, c1663: bool = True):
    click.echo(f"Showing: '{root}'")
    pst = PersistentSearchTree()
    placed, remaining, parent, score, cumulative_score, mean_score, status = pst.get(
        root
    )
    children = pst.get_children(root)

    if c1663:
        vocabulary = vocab_c1663
    valid_vocab = [w for w in compute_valid_vocab(vocabulary, Counter(remaining))]
    explored_vocab = {entry[0]: entry for entry in children}

    status_codes = {0: 0, 7: 0}
    children = []
    for word in valid_vocab:
        new_sentence = root + " " + word
        w = explored_vocab.get(
            new_sentence,
            (new_sentence, "", "", None, None, None, "Unexplored"),
        )
        sc = w[6]
        if status_codes.get(sc) is None:
            status_codes[sc] = 0
        status_codes[sc] += 1
        if sc == 0:  # see CANDIDATE_STATUS_CODES for details
            children.append(w)
    total = float(sum(status_codes.values()))
    click.echo(f"Child node demographics ({total:4} children):")
    click.echo("-----------------------")
    for sc, v in sorted(status_codes.items(), key=lambda x: str(x)):
        s = str(sc)[0]
        percentage = float(v) / total
        click.echo(f"{s}: {v:4} ({percentage:.2f}%)")
    click.echo("")

    click.echo("Top next candidates:")
    click.echo("--------------------")
    for entry in sorted(children, key=lambda x: x[5], reverse=True)[:candidates]:
        score = float(entry[5])
        click.echo(f"{score:.2f}: {entry[0]}")
    click.echo("")


cli.add_command(solve)
cli.add_command(trim)
cli.add_command(show)
