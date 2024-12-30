import cProfile
import datetime
import json
from pstats import Stats
import click

from anagramist.solver import Solver
from anagramist.oracles import TransformerOracle
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
    _c1663_letters = sorted("""ttttttttttttooooooooooeeeeeeeeaaaaaaallllllnnnnnnuuuuuuiiiiisssssdddddhhhhhyyyyyIIrrrfffbbwwkcmvg:,!!""")  # noqa: E501
    if sorted(letters) == _c1663_letters:
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

    # heavy objects
    ctx.obj["SEARCH_TREE"] = PersistentSearchTree(db_name=database)
    ctx.obj["ORACLE"] = TransformerOracle(
        model_name_or_path, seed, (not use_gpu), use_fp16, c1663
    )
    ctx.obj["solver"] = Solver(
        ctx.obj["LETTERS"],
        ctx.obj["SEARCH_TREE"],
        ctx.obj["ORACLE"],
        c1663=ctx.obj["C1663"],
    )

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
@click.option(
    "--profile",
    "do_profiling",
    is_flag=True,
    default=False,
    show_default=True,
    help="Whether or not to run cProfile on this run",
)
@click.option("--max_iterations", is_flag=False, default=10, help="")
@click.pass_context
def solve(
    ctx: click.Context, root=("",), do_profiling: bool = False, max_iterations: int = 10
):
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

    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    profile_filename = f"profile_{now}.txt"
    stats_filename = f"prof_stats_{now}.txt"
    if do_profiling:
        with cProfile.Profile() as pr:
            s = Solver(
                ctx.obj["LETTERS"],
                ctx.obj["SEARCH_TREE"],
                ctx.obj["ORACLE"],
                c1663=ctx.obj["C1663"],
                max_iterations=max_iterations,
            )
            s.solve()
        with open(profile_filename, "w") as stream:
            stats = Stats(pr, stream=stream)
            stats.strip_dirs()
            stats.sort_stats("time")
            stats.dump_stats(stats_filename)
            stats.print_stats()
    else:
        solver: Solver = ctx.obj["solver"]
        solver.solve(r)


@cli.command()
@click.option(
    "-n",
    "--number",
    type=int,
    default=5,
    help="Maximum number of child nodes to show",
)
@click.option("-t", "--trim", is_flag=True, help="Remove all the descendents")
@click.option(
    "-s",
    "--status",
    type=int,
    default=-1,
    help="""Sets the candidate's status. See CANDIDATE_STATUS_CODES for more info
    
    In order for a status to be set, the candidate must already have a score or the
    program will exit with an error.
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
    status: int,
    quiet: bool,
):
    """Examine and manipulate individual candidate solutions.

    Operations that modify a candidate will occur first. Then the entry will be
    retrieved. Then summary stats will then be formatted and output.
    """

    verbose = ctx.obj["VERBOSE"]

    c = " ".join(candidate)

    # modify
    pst = ctx.obj["SEARCH_TREE"]

    if status >= 0:
        modified = pst.status(c, status)
        if verbose:
            if modified < 0:
                click.echo(f"Status was already set to {status}")
            elif modified == 0:
                click.echo(f"'{c}' not found. No status was changed")
            else:
                click.echo(f"Status changed to {status} for {modified} candidates")

    if trim:
        modified = pst.trim(c)
        if verbose:
            click.echo(f"{modified} child nodes removed")

    # display
    if quiet:
        return

    click.echo(f"'{c}'\n")

    solver: Solver = ctx.obj["solver"]
    stats, top_children, top_descendents = solver.retrieve_candidate(c, limit=number)

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


@cli.command()
@click.argument("candidate", nargs=-1)
@click.option(
    "--candidate-only",
    is_flag=True,
    help="Only output the candidate itself, not the full path to it",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Format the output as JSON",
)
@click.option(
    "--auto-letters",
    is_flag=True,
    help="""Override the letter bank so that it contains exactly the letters needed for
    the provided candidate""",
)
@click.option(
    "--record",
    is_flag=True,
    help="Record the resulting score, and the scores of all the intermediary nodes",
)
@click.pass_context
def check(
    ctx: click.Context,
    candidate: tuple,
    candidate_only: bool,
    json_output: bool,
    auto_letters: bool,
    record: bool,
):
    """Evaluate a candidate string

    Scores a candidate string as if it was the terminal state of the Solvers expansion
    method. By default, this does not record the resulting score.
    """
    if candidate == ():
        click.echo("Please provide a candidate to check")
        ctx.exit(1)

    sentence = " ".join(candidate)
    if auto_letters:
        solver: Solver = Solver(
        sentence,
        ctx.obj["SEARCH_TREE"],
        ctx.obj["ORACLE"],
        c1663=False,
    )
    else:
        solver: Solver = ctx.obj["solver"]

    # Items with invalid characters will break oracle assessment, so use soft_validate
    # to skim those off and replace them with synthetic failures
    i_c = 0
    v = sentence
    while not solver.soft_validate(v):
        i_c += 1
        v = " ".join(candidate[:-i_c]) if i_c > 0 else " ".join(candidate)

    path = solver.assessment(v)

    # re-pad the path with synthetic failure entries for each word that failed earlier
    if i_c > 0:
        invalid_candidates = [" ".join(candidate[:-i]) for i in range(1, i_c)][::-1]
        path.extend([[c, 0, 0, 0, 0, float("-inf"), 1] for c in invalid_candidates])
        path.append([" ".join(candidate), 0, 0, 0, 0, float("-inf"), 1])

    if record:
        for c in path:
            ctx["SEARCH_TREE"].push(*c)

    if candidate_only:
        path = [path[-1]]
    click.echo(path)
    if auto_letters and path[-1][-2] == float("-inf"): # auto letters implies c1663 == False
        click.echo("Error: --auto-letters set but candidate soft failed validation")
        click.echo("Investigate with a debugger:")
        click.echo(f"""
            $ anagramist check --auto-letters --candidate-only --json "{path[-1][0]}"
        """)
        ctx.exit(1)
        
    if json_output:
        s, _remaining, _parent, _, _, score, status = path[0]
        click.echo(json.dumps({"status": status, "score": score, "sentence": s}))
    else:
        click.echo("Status | Score | Sentence")
        click.echo("-------------------------")
        for s, _remaining, _parent, _, _, score, status in path[::-1]:
            click.echo(f"   {status}   | {score: =5.1f} | {s}")


cli.add_command(solve)
cli.add_command(candidates)
cli.add_command(check)
