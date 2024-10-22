import click

from typing import Set

from anagramist import search, vocab, show_candidate
from anagramist.persistentsearchtree import PersistentSearchTree
from anagramist.vocab import c1663_disallow


@click.group(invoke_without_command=True)
@click.version_option()
@click.option(
    "-d",
    "--database",
    default="anagramist.db",
    type=click.Path(),
    help="path to the sqlite database to use for persistence",
)
@click.option(
    "-l",
    "--letters",
    default="ttttttttttttooooooooooeeeeeeeeaaaaaaallllllnnnnnnuuuuuuiiiiisssssdddddhhhhhyyyyyIIrrrfffbbwwkcmvg:,!!",
    help="the bank of characters to use. Defaults to using Comic 1663",
)
@click.option(
    "--c1663/--no-c1663",
    default=False,
    help="""Whether to apply rules specific to Comic 1663. If the letter bank of 
    Comic 1663 is detected this will be inferred to be True. 
    
    Only set this manually if you are using the c1663 letter bank but don't want the 
    additional rules, or if you want to apply the rules to a non-c1663 letter bank.""",
)

@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def cli(ctx, database, letters, c1663, verbose):
    "a solver for dinocomics 1663-style cryptoanagrams"
    ctx.ensure_object(dict)
    ctx.obj["DATABASE"] = database
    ctx.obj["LETTERS"] = letters
    ctx.obj["C1663"] = c1663
    ctx.obj["VERBOSE"] = verbose

    if letters == "ttttttttttttooooooooooeeeeeeeeaaaaaaallllllnnnnnnuuuuuuiiiiisssssdddddhhhhhyyyyyIIrrrfffbbwwkcmvg:,!!":
        # infer c1663
        click.echo(c1663)

    if ctx.invoked_subcommand is None:
        click.echo("Anagramist was invoked without subcommand")
    else:
        click.echo(f"Anagramist was invoked with subcommand: {ctx.invoked_subcommand}")
    click.echo("CLI - Context:")
    for k, v in ctx.obj.items():
        click.echo(f"  {k}: {v}")


@click.group(invoke_without_command=True)
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
    "--use_fp16",
    is_flag=True,
    help="""Whether to use 16-bit (mixed) precision (through NVIDIA apex) instead of 
    32-bit""",
)
@click.pass_context
def transfomers(ctx, model_name_or_path, seed, use_gpu, use_fp16):
    ctx.ensure_object(dict)
    ctx.obj["MODEL"] = model_name_or_path
    ctx.obj["SEED"] = seed
    ctx.obj["USE_GPU"] = use_gpu
    ctx.obj["USE_FP16"] = use_fp16

    click.echo("TRANSFORMERS - Context:")
    for k, v in ctx.obj.items():
        click.echo(f"  {k}: {v}")


@cli.command()
@click.pass_context
def solve(ctx):
    # click.echo(f"Assembling anagrams from: {"".join(sorted(ctx.obj["PUZZLE"]))}")

    click.echo("SOLVE - Context:")
    for k, v in ctx.obj.items():
        click.echo(f"  {k}: {v}")
    # search(
    #     ctx.obj["PUZZLE"],
    #     ctx.obj["DATABASE"],
    #     ctx.obj["MODEL_NAME_OR_PATH"],
    #     ctx.obj["SEED"],
    #     ctx.obj["USE_GPU"],
    #     ctx.obj["USE_FP15"],
    #     ctx.obj["C1663"],
    # )


@click.command()
@click.argument("root")
@click.option(
    "-s",
    "--status",
    type=int,
    default=7,
    help="Status code for the root node. Non-zero will prevent further searching.",
)
@click.option(
    "-c",
    "--containing",
    is_flag=True,
    help="""Trim all explored nodes containing the 'root' string at each occurance of
    the root string.""",
)
def trim(root: str, status, containing: bool):
    pst = PersistentSearchTree()
    if containing:
        click.echo(f"Trimming all branches containing: '{root}'")
        modified, deleted = pst.trim_containing(root, status=status)
    else:
        click.echo(f"Trimming descendents of: '{root}'")
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

    stats, top_children, top_descendents = show_candidate(
        root,
        limit=candidates,
        c1663=c1663,
    )

    total = float(sum([x["count"] for x in stats.values()]))

    click.echo(f"Child node demographics: ({total:4} children)")
    click.echo("-----------------------")
    for sc, v in sorted(stats.items(), key=lambda x: str(x[0])):
        status = (str(sc)[0],)
        count = v["count"]
        percentage = float(v["percentage"]) * 100
        click.echo(f"{status}: {count:4} ({percentage:.1f}%)")
    click.echo("")

    click.echo("Top next candidates:")
    click.echo("--------------------")
    for entry in top_children.values():
        score = float(entry[5])
        click.echo(f"{score:.2f}: {entry[0]}")
    click.echo("")

    click.echo("Top descendents: (mean score)")
    click.echo("---------------")
    for entry in top_descendents.values():
        score = float(entry[5])
        click.echo(f"{score:.2f}: {entry[0]}")
    click.echo("")


@click.command()
@click.argument("words")
def prune(words: str):
    """Prune the tree by trimming every occurance of a word or set of words at the
    occurance of each word

    Args:
        Words - variadic. Either '*' for the c1663_disallow list or a space-separated
        list of words to be pruned.
    """
    to_prune = words.split()
    if words == "*":
        click.echo(f"pruning the c1663 dissalow list: {len(c1663_disallow)} entries")
        to_prune = sorted(c1663_disallow)
    total_modified, total_deleted = 0, 0
    pst = PersistentSearchTree()
    for word in to_prune:
        click.echo(f"Trimming all branches containing: '{word}'")
        m, d = pst.trim_containing(word, status=7)
        click.echo(f"{m} rows modified. {d} rows deleted.")
        total_modified += m
        total_deleted += d
    click.echo(f"Fin. {total_modified} rows modified. {total_deleted} rows deleted.")
    click.echo("")


# @click.command()
# @click.option(
#     "--yes",
#     is_flag=True,
#     help="""Enable to automatically confirm all prompts, allowing the command to finish
#     without user input""",
# )
# def database(subcommand):
#     subcommand in {"backup", "restore", "verify"}
#     # dispatch:
#     # > backup [optional arg: backup_destination]
#     # > restore [arg: restore_source]
#     # > verify [--puzzle=inferred]
#     passqs


cli.add_command(solve)
cli.add_command(trim)
cli.add_command(show)
cli.add_command(prune)
