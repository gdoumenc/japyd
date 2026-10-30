import argparse
import sys
from importlib.resources import files
from pathlib import Path

SKILL_NAME = "japyd"


def skill_source() -> str:
    """Content of the Agent Skill shipped in the package."""
    return files("japyd").joinpath("skills", SKILL_NAME, "SKILL.md").read_text(encoding="utf-8")


def skill_target(user: bool = False, directory: Path | None = None) -> Path:
    """Path of the installed SKILL.md: in the given skills directory, the user one or the project one."""
    if directory is None:
        directory = Path.home() / ".claude" / "skills" if user else Path.cwd() / ".claude" / "skills"
    return directory / SKILL_NAME / "SKILL.md"


def install(target: Path, force: bool = False) -> str:
    """Copies the skill to target; a different existing skill is only replaced with force."""
    content = skill_source()
    if target.exists():
        if target.read_text(encoding="utf-8") == content:
            return f"japyd skill already up to date in {target.parent}"
        if not force:
            raise FileExistsError(f"{target} differs from the japyd skill, use --force to replace it")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"japyd skill installed in {target.parent}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="japyd-skill", description="Install the japyd Agent Skill.")
    commands = parser.add_subparsers(dest="command", required=True)

    install_parser = commands.add_parser("install", help="copy the skill into a skills directory")
    where = install_parser.add_mutually_exclusive_group()
    where.add_argument("--user", action="store_true", help="install in ~/.claude/skills instead of ./.claude/skills")
    where.add_argument("--dir", type=Path, help="skills directory to install in (e.g. .agents/skills)")
    install_parser.add_argument("--force", action="store_true", help="replace a modified skill")

    commands.add_parser("show", help="print the skill")

    args = parser.parse_args(argv)
    if args.command == "show":
        print(skill_source(), end="")
        return 0

    try:
        print(install(skill_target(args.user, args.dir), args.force))
    except (FileExistsError, OSError) as e:
        print(f"japyd-skill: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
