from anagramist.cli import cli

from click.testing import CliRunner


def test_version():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert result.output.startswith("cli, version ")


def test_base():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert result.output.startswith("Usage: cli [OPTIONS] COMMAND [ARGS]...")


def test_candidates():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["candidates"])
        assert result.exit_code == 1
        assert "Candidate not yet explored" in result.output
