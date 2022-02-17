from pathlib import Path

from doit import create_after
from doit.tools import CmdAction

HERE = Path(__file__).parent


def task_bootstrap():
    """bootstrap the kindling project"""

    def deps():
        from textwrap import indent

        from configupdater import ConfigUpdater

        c = ConfigUpdater()
        c.read(SETUPCFG)
        if "doit" not in str(c["options"]["install_requires"]):
            c["options"]["install_requires"] = indent("\n".join(["", "pydantic", "doit"]), " " * 4)
            c.update_file()

    from src.kindling.dodo import SETUPCFG, task_new

    yield from task_new("kindling")
    yield dict(name="deps", actions=[deps], file_dep=[SETUPCFG], uptodate=[False])
