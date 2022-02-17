from os import environ
from pathlib import Path

from nox import session

HERE = Path(__file__).parent
DOCS = HERE / "docs"
TOC, CONFIG = HERE / "_toc.yml", DOCS / "_config.yml"
REUSE = "CI" not in environ


@session(reuse_venv=REUSE)
def test(session):
    session.install("-e.[test]")
    session.run("pytest", *session.posargs)


@session(reuse_venv=REUSE)
def docs(session):
    session.install("-e.[doc]")
    session.run("jb", "--toc", str(TOC), "--config", str(CONFIG), str(HERE))
