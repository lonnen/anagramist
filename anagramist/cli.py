import click

from anagramist import search, show_candidate
from anagramist.persistentsearchtree import PersistentSearchTree


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
    help="the bank of characters to use. [default: the Comic 1663 letter bank]",
)
@click.option(
    "--suppress-c1663",
    is_flag=True,
    help="""Enable to suppress the application of additional rules and heuristics 
    specific to Comic 1663. These rules only apply if the letter bank matches c1663, so
    only set this flag if you are using the c1663 letter bank AND you do not want the
    additional heuristics to apply.""",
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
    """a solver utility for dinocomics 1663-style cryptoanagrams

    Options of anagramist must occur before any subcommands. Subcommands may have
    their own options, which must be provided after the subcommand.

    Searches are persisted to a SQLite DB. If the need arises external tools should be
    used to back up the db with `cp database.db database.db-backup`, restore the db
    with with `mv` and `cp`, or by pointing `--database=` at a new file, or migrate the
    db using the sqlite cli to output each DB row into a call to `anagramist candidates`
    in order to directly enter into a new DB.
    """

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
    ctx.obj["USE_GPU"] = use_gpu
    ctx.obj["USE_FP16"] = use_fp16
    ctx.obj["SEED"] = seed
    # utility
    ctx.obj["VERBOSE"] = verbose

    ctx.obj["SEARCH_TREE"] = PersistentSearchTree(db_name=database)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
    else:
        if ctx.obj["VERBOSE"]:
            click.echo("General configuration:")
            click.echo(f"  * letter bank: {"".join(sorted(ctx.obj["LETTERS"]))}")
            if ctx.obj["C1663"]:
                click.echo("  * C1663 heuristics enabled")
            click.echo(f"  * database: {database}")
            click.echo("Transformers.py configuration:")
            click.echo(f"  * model: {model_name_or_path}")
            click.echo(f"  * use gpu?: {use_gpu}")
            click.echo(f"  * use FP16?: {use_fp16}")
            click.echo(f"  * seed: {seed}")


@cli.command()
@click.argument("root", nargs=-1)
@click.pass_context
def solve(ctx: click.Context, root=("",)):
    """Search for a valid arrangement of letters

    Search proceeds from the root, or the empty string if no root is provided, or "I" if
    the Comic 1663 heuristics are applied and no other root is provided.

    Search proceeds in a loop by choosing either the root or one explored descendent of
    the root at random, weighted by the recorded score of each in the `--database`.
    Starting from the chosen candidate, words are pulled at random from the remaining
    set of `--letters` and applied to the candidate until a hard validating solution is
    found or the candidate fails soft validation. If hard validation passes record it,
    output a message, and exit the program. If soft validation fails then no additional
    placement of the remaining letters can improve the chances of this candidate. The
    candidate and all of the intermediary parent states are scored and recorded. The
    loop then starts over.
    """
    r = " ".join(root)
    click.echo(f"Assembling anagrams from: {"".join(sorted(ctx.obj["LETTERS"]))}")
    click.echo(f"Searching for solutions starting from: {r}")
    search(
        ctx.obj["PUZZLE"],
        ctx.obj["DATABASE"],
        ctx.obj["MODEL_NAME_OR_PATH"],
        ctx.obj["SEED"],
        ctx.obj["USE_GPU"],
        ctx.obj["USE_FP15"],
        ctx.obj["C1663"],
    )


@click.command()
@click.option(
    "-n",
    "--number",
    type=int,
    default=5,
    help="Maximum number of child nodes to show",
)
@click.option("-t", "--trim", is_flag=True, help="Remove all the descendents")
@click.option(
    "--validate",
    is_flag=True,
    help="""(re-)validate and (re-)score the candidate. If the candidate is not in the
    search tree this will create it. If the candidate passes validation all the parent
    intermediary candidates will also be created and entered into the search tree.
    """,
)
@click.option(
    "-s",
    "--status",
    type=int,
    help="""Sets the candidate's status. See CANDIDATE_STATUS_CODES for more info
    
    In order for a status to be set, the candidate must have a score or the program will
    exit with an error. If the candidate has never been examined, pass the `--validate`
    flag to score it 
    """,
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="This will suppress the output summary of the candidate",
)
@click.argument("candidate", nargs=-1)
@click.pass_context
def candidates(
    ctx: click.Context,
    candidate: tuple,
    number: int,
    trim: bool,
    validate: bool,
    status: int,
    quiet: bool,
):
    """Examine and manipulate individual candidate solutions.

    Operations that modify a candidate will occur first. Then the entry will be
    retrieved. Then summary stats will then be formatted and output.
    """

    # modify

    # display
    if quiet:
        return

    c = " ".join(candidate)
    click.echo(f"'{c}'\n")

    stats, top_children, top_descendents = show_candidate(
        c,
        ctx.obj["SEARCH_TREE"],
        limit=number,
        c1663=ctx.obj["C1663"],
    )

    if len(stats) == 0:
        click.echo("Candidate not yet explored")
        ctx.exit(1)

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
@click.pass_context
def check_database(ctx: click.Context):
    """Verify the integrity of the configured database

    Connect to the database, examine every entry in the DB to determine the letter
    bank(s) for the row, and exit 0 if all rows use the same bank. If `--verbose` flag
    is passed it will also output some summary statistics about the entire database.
    """
    pst = ctx.obj["SEARCH_TREE"]
    integrity, counts = pst.verify_integrity()
    if ctx.obj["VERBOSE"]:
        if integrity:
            click.echo(f"DB {ctx.obj["DATABASE"]} is internally consistent.")
        else:
            click.echo(f"Multiple letter banks found in DB {ctx.obj["DATABASE"]}")
        click.echo("")
        for bank, count in counts:
            click.echo(f"{bank}, {count}")
    # exit codes are integers, the reverse of a boolean success value
    ctx.exit(int(not integrity))


cli.add_command(solve)
cli.add_command(candidates)
cli.add_command(check_database)
