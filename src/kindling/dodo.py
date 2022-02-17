from typing import Any, List
from doit import task_params
from doit.tools import create_folder, CmdAction
from contextlib import suppress
from pathlib import Path
from shutil import rmtree
import py
from pydantic import BaseModel, Field

DOIT_CONFIG = dict(default_tasks=["new"])
HERE = Path().resolve()
GITIGNORE = Path(".gitignore")
SETUPTOOLS_SCM = lambda name: dict(
    write_to=f"src/{name}/_version.py",
    version_scheme="release-branch-semver",
    local_scheme="node-and-timestamp",
)
README = Path("README.md")

ISORT = dict(profile="black")
BLACK = dict(line_length=100)
PYTEST = dict(ini_options=dict(addopts=f"""--nbval --nbval-sanitize-with docs/santize.cfg"""))

BUILD_SYSTEM = dict(
    requires=["setuptools>=45", "wheel", "setuptools_scm>=6.2"],
    **{"build-backend": "setuptools.build_meta"},
)

DOIT = dict(backend="json", verbosity=2, commands=dict(list=dict(status=True, subtasks=True)))

EXTRAS = dict(
    doc="""
jupyter-book""",
    test="""
pytest
nbval""",
)


class Model(BaseModel):
    @classmethod
    def task(cls, name):
        def write():
            x = cls.object(name=name)
            print(x)
            x.write()

        return dict(
            name=cls.__name__,
            actions=[(create_folder, [Path(cls._filename).parent]), write],
            clean=True,
            uptodate=[Path(cls._filename).exists()],
            targets=[cls._filename],
        )

    def __init_subclass__(cls, file=None):
        cls._filename = file

    def print(self):
        print(self.dump())

    def __fspath__(self):
        return str(Path(self._filename).resolve())

    def write(self):
        with open(self, "w") as file:
            file.write(self.dump())
            print(f"wrote {file.name}")

    def clean(self):
        Path(self.__fspath__()).unlink()

    class Config:
        allow_population_by_field_name = True


class Toml(Model):
    def dump(self):
        from tomlkit import dumps

        return dumps(self.dict())


class Json(Model):
    def dump(self):
        from json import dumps

        return dumps(self.dict())


class Cfg(Model):
    def dump(self):
        from io import StringIO
        from configparser import ConfigParser

        parser = ConfigParser()
        parser.read_dict(self.dict())
        text = StringIO()
        parser.write(text)
        return text.getvalue()


PYPROJECT = Path("pyproject.toml")


class pyproject(Toml, file=PYPROJECT):

    tool: dict = Field(default_factory=dict)
    __annotations__.update({"build-system": dict})
    locals().update(
        {"build-system": Field(default_factory=BUILD_SYSTEM.copy, alias="build-system")}
    )

    @classmethod
    def object(cls, name):
        return cls(
            tool=dict(
                setuptools_scm=SETUPTOOLS_SCM(name),
                doit=DOIT,
                isort=ISORT,
                black=BLACK,
                pytest=PYTEST,
            )
        )

    def dump(self):
        from tomlkit import dumps

        return dumps(self.dict())


class toc(Json, file=Path("_toc.yml")):
    format: str = "jb-book"
    root: str = "README.md"
    chapters: List = Field(default_factory=list)

    @classmethod
    def object(cls, name):
        return cls(chapters=[dict(file=f"docs/test_{name}.ipynb")])


class config(Json, file=Path("docs", "_config.yml")):
    title: str
    execute: dict = Field(default_factory=dict(execute="off").copy)

    @classmethod
    def object(cls, name):
        return cls(title=name)


SETUPCFG = Path("setup.cfg")


class setupcfg(Cfg, file=SETUPCFG):
    class Metadata(Model):
        name: str
        description: str = ""
        long_description: str = "file: README.md"
        long_description_content_type: str = "text/markdown"
        url: str = ""
        author: str = ""
        author_email: str = ""
        keywords: str = ""

    metadata: Metadata

    class Options(Model):
        install_requires: Any = ""
        package_dir: str = """\n=src"""
        packages: str = "find:"

    options: Options
    __annotations__.update({"options.extras_require": dict})
    locals().update({"options.extras_require": Field(default_factory=EXTRAS.copy)})

    @classmethod
    def object(cls, name):
        return cls(metadata=cls.Metadata(name=name), options=cls.Options())


@task_params([dict(name="name", short="n", long="name", default="sample", type=str)])
def task_new(name):
    """start a new project"""
    yield pyproject.task(name)
    yield setupcfg.task(name)
    yield toc.task(name)
    yield config.task(name)
    yield dict(
        name="gitignore",
        actions=[(write, (GITIGNORE, ignores(name)))],
        uptodate=[GITIGNORE.exists()],
        clean=True,
    )
    yield dict(name="git", actions=["git init"], uptodate=[Path(".git").exists()])
    INIT, MAIN = Path("src", name, "__init__.py"), Path("src", name, "__main__.py")
    yield dict(
        name="python",
        actions=[(write, [INIT, ""]), (write, [MAIN, ""])],
        targets=[INIT, MAIN],
        uptodate=[INIT.exists(), MAIN.exists()],
    )
    yield dict(
        name="readme",
        actions=[f"echo # {name} > {README}"],
        targets=[README],
        uptodate=[README.exists()],
        clean=True,
    )


def task_develop():
    return dict(actions=["pip install -e."], file_dep=["pyproject.toml", "setup.cfg"])


from pathlib import Path

DOCS = Path("docs")
BUILD = Path("_build")
CONF = DOCS / "conf.py"
TOC = "_toc.yml"
CONFIG = DOCS / "_config.yml"
HTML = BUILD / "html"
README = Path("README.md")


def task_docs():
    def configure():
        action = CmdAction(["jb", "config", "sphinx", "--config", str(CONFIG), "."])
        action.execute()

    yield dict(
        name="config",
        file_dep=[TOC, CONFIG],
        actions=[configure],
        clean=True,
        targets=[CONF],
    )
    yield dict(
        name="build",
        file_dep=[README, CONF],
        actions=[f"sphinx-build -c {DOCS} . {HTML}"],
        clean=[(remove, [HTML])],
    )


def remove(path):
    with suppress(FileNotFoundError):
        rmtree(path)
        print(f"removed {path}")


def write(path, input):
    Path(path).write_text(input)


ignores = lambda x: """.doit.db*
__pycache__
_build
src/{name}/_version.py
*.egg-info""".format(
    name=x
)
