import datetime
import os
import shutil
import click

from pathlib import Path
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
    show_default=True,
    type=click.Path(),
    help="path to the sqlite database to use for persistence",
)
@click.option(
    "-l",
    "--letters",
    default="""ttttttttttttooooooooooeeeeeeeeaaaaaaallllllnnnnnnuuuuuuiiiiisssssdddddhhhhhyyyyyIIrrrfffbbwwkcmvg:,!!""",  # noqa: E501
    help="the bank of characters to use. Defaults to using the Comic 1663 letter bank",
)
@click.option(
    "--suppress-c1663",
    default=False,
    help="""This suppressed the application of additional rules and heuristics specific
    to Comic 1663. The rules only apply if the letter bank matches c1663, so only set
    this flag if you are using the c1663 letter bank AND you do not want the additional
    heuristics to apply.""",
)
@click.option(
    "-m",
    "--model_name_or_path",
    default="microsoft/phi-1_5",
    type=click.Path(),
    help="Model name or path to a model to use when evaluating candidates",
)
@click.option(
    "--seed", type=int, default=42, help="Which seed to use for model evaluation"
)
@click.option(
    "--use_gpu",
    is_flag=True,
    default=False,
    show_default=True,
    help="Whether to use the gpu (otherwise, cpu) for evaluating candidates",
)
@click.option(
    "--use_fp16",
    is_flag=True,
    help="""Whether to use 16-bit (mixed) precision (through NVIDIA apex) instead of 
    32-bit""",
)
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def cli(
    ctx: click.Context,
    database: str,
    letters: str,
    suppress_c1663: bool,
    model_name_or_path: click.Path,
    seed: int,
    use_gpu: bool,
    use_fp16: bool,
    verbose: bool,
):
    """a solver utility for dinocomics 1663-style cryptoanagrams"""

    c1663 = False
    _c1663_letters = """ttttttttttttooooooooooeeeeeeeeaaaaaaallllllnnnnnnuuuuuuiiiiisssssdddddhhhhhyyyyyIIrrrfffbbwwkcmvg:,!!"""  # noqa: E501
    if letters == _c1663_letters:
        c1663 = True
        if suppress_c1663:
            c1663 = False

    ctx.ensure_object(dict)
    ctx.obj["DATABASE"] = database
    ctx.obj["LETTERS"] = letters
    ctx.obj["C1663"] = c1663
    # transformers.py settings
    ctx.obj["MODEL_NAME_OR_PATH"] = model_name_or_path
    ctx.obj["SEED"] = seed
    ctx.obj["USE_GPU"] = use_gpu
    ctx.obj["USE_FP16"] = use_fp16
    # utility
    ctx.obj["VERBOSE"] = verbose

    if ctx.invoked_subcommand is None:
        if not ctx.obj["VERBOSE"]:
            click.echo("This space intentionally left blank. Pass `-v` for more info.")
            click.echo(
                "Use `anagramist --help` for full list of arguments and options."
            )

    ctx.obj["SEARCH_TREE"] = PersistentSearchTree(db_name=database)
    if ctx.obj["VERBOSE"]:
        click.echo("Configuration:")
        click.echo(f"* letter bank: {"".join(sorted(ctx.obj["LETTERS"]))}")
        if ctx.obj["C1663"]:
            click.echo("* C1663 heuristics enabled")
        click.echo(f"* database: {database}")


@cli.command()
@click.pass_context
def solve(ctx: click.Context):
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
@click.argument("candidate")
@click.pass_context
def candidates(
    ctx: click.Context,
    candidate: str,
):
    click.echo("CANDIDATES - Context:")
    for k, v in ctx.obj.items():
        click.echo(f"  {k}: {v}")
    pass


@click.group(invoke_without_command=True)
@click.pass_context
def database(ctx: click.Context):
    click.echo("DATABASE - Context:")
    for k, v in ctx.obj.items():
        click.echo(f"  {k}: {v}")
    pass


@database.command()
@click.pass_context
def verify(ctx: click.Context):
    # verify that every entry in the database uses the same
    click.echo("DATABASE -> VERIFY - Context:")
    for k, v in ctx.obj.items():
        click.echo(f"  {k}: {v}")
    pass


@database.command()
@click.argument(
    "backup_to",
    type=click.Path(),
)
@click.pass_context
def backup(ctx: click.Context, backup_to: click.Path):
    """BACKUP_TO: Path to the backup that will be created. If this is a directory the
    backup will be created there. If it is a filename, it will be used for the backup.

    This may lose some metadata. See Python `shutil.copy2()` and `shutil.copystat()`
    for more information.
    """
    src = Path(ctx.obj['DATABASE'])
    dest = Path(backup_to)
    
    if Path.samefile(src, dest):
        click.echo("Cannot backup the database to itself")
        ctx.exit(1)

    if dest.is_dir():
        cur_time = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%S")
        # this might fail if you are running on one OS (say, POSIX) and accessing files
        # from a different OS (say, Windows)
        db_filename = os.path.basename(src)
        dest = dest.with_suffix(f"{db_filename}-backup-{cur_time}")

    if dest.exists():
        click.echo(f"Cannot back up database {src} to {dest}")
        click.echo(f"Destination file already exists")
        ctx.exit(1)

    click.echo(f"Backing up {src} to {dest}!")
    # shutil.copy2(src, dest)
    click.echo(f"Dry run completed!")


@database.command()
@click.confirmation_option(prompt="DESTROY THE CURRENT DB IN ORDER TO REPLACE IT?")
@click.argument(
    "restore_from",
    type=click.Path(exists=True),
)
@click.pass_context
def restore(ctx: click.Context, restore_from: click.Path):
    """RESTORE_FROM: Path to the database which will replace the current DB"""
    if restore_from == ctx.obj.get("DATABASE"):
        click.echo(f"Cannot restore database `{restore_from}` from itself")
        ctx.exit(code=1)
    else:
        click.echo(ctx.obj.get("DATABASE"))

    click.echo("DATABASE -> RESTORE2 - Context:")
    for k, v in ctx.obj.items():
        click.echo(f"  {k}: {v}")
    pass

cli.add_command(solve)
cli.add_command(candidates)
cli.add_command(database)