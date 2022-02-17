from pathlib import Path
from doit import create_after
from doit.tools import CmdAction

HERE = Path(__file__).parent


def task_bootstrap():
    """bootstrap the kindling project"""
    from src.kindling.dodo import task_new, task_develop

    yield from task_new("kindling")
