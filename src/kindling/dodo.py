from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, List, Union

from doit import task_params
from doit.tools import CmdAction, create_folder
from pydantic import BaseModel, Field

# doit tasks


@task_params([dict(name="name", short="n", long="name", default="sample", type=str)])
def task_new(name):
    """start a new project"""
    yield pyproject.task(name)
    yield setupcfg.task(name)
    yield toc.task(name)
    yield config.task(name)
    TESTNB = DOCS / f"test_{name}.ipynb"

    class nb(notebook, file=TESTNB):
        pass

    yield nb.task(name)
    yield dict(
        name="gitignore",
        actions=[(write, (GITIGNORE, gitignores(name)))],
        uptodate=[GITIGNORE.exists()],
        clean=True,
    )
    yield release.task(name)
    yield test.task(name)
    yield dict(name="git", actions=["git init"], uptodate=[Path(".git").exists()])
    SRC = Path("src", name)
    INIT, MAIN = SRC / "__init__.py", SRC / "__main__.py"
    yield dict(
        name="nox",
        actions=[(copyfile, [THIS / NOX, NOX])],
        targets=[NOX],
        uptodate=[NOX.exists()],
        clean=True,
    )
    yield dict(
        name="nbval-sanitize",
        actions=[(copyfile, [THIS / SANITIZE, DOCS / SANITIZE])],
        targets=[SANITIZE],
        uptodate=[SANITIZE.exists()],
        clean=True,
    )
    yield dict(
        name="python",
        actions=[(create_folder, [SRC]), (write, [INIT, ""]), (write, [MAIN, ""])],
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


# doit configuration

DOIT_CONFIG = dict(default_tasks=["new"])

# files
HERE = Path().resolve()
THIS = Path(__file__).parent
README = Path("README.md")
SETUPCFG = Path("setup.cfg")
CONFIG = Path("docs", "_config.yml")
TOC = Path("_toc.yml")
GITIGNORE = Path(".gitignore")
PYPROJECT = Path("pyproject.toml")
DOCS = Path("docs")
BUILD = Path("_build")
CONF = DOCS / "conf.py"
CONFIG = DOCS / "_config.yml"
HTML = BUILD / "html"
NOX = Path("noxfile.py")
WORKFLOWS = Path(".github", "workflows")
SANITIZE = Path("sanitize.cfg")
# default configurations

ISORT = dict(profile="black")
BLACK = dict(line_length=100)
PYTEST = dict(ini_options=dict(addopts=f"""--nbval --sanitize-with docs/sanitize.cfg -pno:warnings"""))

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


def SETUPTOOLS_SCM(name):
    return dict(
        write_to=f"src/{name}/_version.py",
        version_scheme="release-branch-semver",
        local_scheme="node-and-timestamp",
    )


def gitignores(x):
    return """.doit.db*
__pycache__
_build
src/{name}/_version.py
*.egg-info""".format(
        name=x
    )


# kindling models
class Model(BaseModel):
    """base model for kindling that exports doit tasks on type creation"""

    @classmethod
    def task(cls, name):
        def write():
            cls.object(name=name).write()

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

        return dumps(self.dict(), indent=2)


class Cfg(Model):
    def dump(self):
        from configparser import ConfigParser
        from io import StringIO

        parser = ConfigParser()
        parser.read_dict(self.dict())
        text = StringIO()
        parser.write(text)
        return text.getvalue()


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


class toc(Json, file=TOC):
    format: str = "jb-book"
    root: str = "README.md"
    chapters: List = Field(default_factory=list)

    @classmethod
    def object(cls, name):
        return cls(chapters=[dict(file=f"docs/test_{name}.ipynb")])


class config(Json, file=CONFIG):
    title: str
    execute: dict = Field(default_factory=dict(execute="off").copy)

    @classmethod
    def object(cls, name):
        return cls(title=name)


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

    
class notebook(Json):
    nbformat: int = 4
    nbformat_minor: int = 5
    metadata: dict = Field(default_factory=dict)
    cells: list = Field(default_factory=list)

    @classmethod
    def object(cls, name):
        from uuid import uuid1

        return cls(
            cells=[
                dict(
                    cell_type="markdown",
                    metadata={},
                    source=f"# `{name}` tests",
                ),
                dict(
                    id=str(uuid1()),
                    cell_type="code",
                    metadata={},
                    execution_count=None,
                    source=f"    import {name}\n    {name}",
                    outputs=[],
                ),
            ]
        )


class step(Model):
    name: str


class action(step):
    uses: str
    __annotations__.update({"with": dict})
    locals().update({"with": Field(default_factory=dict)})


class run(step):
    run: str


class workflow(Json):
    class job(Model):

        steps: List[step]
        strategy: dict = Field(default_factory=dict)
        __annotations__.update({"runs-on": str})
        locals().update({"runs-on": "ubuntu-latest"})

    on: Union[list, dict]
    jobs: Dict[str, job]


class steps:
    def python(x=3.9):
        return action(
            name="setup python", uses="actions/setup-python@v2", **{"with": {"python-version": x}}
        )

    def upgrade(x="pip build setuptools wheel"):
        return run(
            name="upgrade dependencies",
            run=f"python -m pip install --upgrade {x}",
        )

    build = run(name="build python", run="python -m build --sdist --wheel")
    checkout = action(
        name="fetch all history and tags",
        uses="actions/checkout@v2",
        **{"with": {"fetch-depth": 0}},
    )

    test = run(name="test within nox", run="nox -s test")

    def install(x):
        return workflow(name="install dependencies", run=f"python -m pip install {x}")

    def publish(user):
        return action(
            name="publish",
            uses="pypa/gh-action-pypi-publish@master",
            **{"with": dict(user=user, password="${{ secrets.pypi_password }}")},
        )


class release(workflow, file=WORKFLOWS / "release.yml"):
    @classmethod
    def object(cls, name):
        return cls(
            on=dict(release=dict(types=["created"])),
            jobs=dict(
                pypi=workflow.job(
                    steps=[
                        steps.python(),
                        steps.checkout,
                        steps.upgrade(),
                        steps.build,
                        steps.publish("docfast"),
                    ]
                )
            ),
        )


class release(workflow, file=WORKFLOWS / "release.yml"):
    @classmethod
    def object(cls, name):
        return cls(
            on=dict(release=dict(types=["created"])),
            jobs=dict(
                pypi=workflow.job(
                    strategy=dict(matrix={"python-version": [3.8, 3.9]}),
                    steps=[
                        steps.checkout,
                        steps.python("${{ matrix.python-version}}"),
                        steps.upgrade("pip nox"),
                        steps.test,
                    ],
                )
            ),
        )


class test(workflow, file=WORKFLOWS / "test.yml"):
    @classmethod
    def object(cls, name):
        return cls(
            on=["push"],
            jobs=dict(
                pypi=workflow.job(
                    strategy=dict(matrix={"python-version": [3.8, 3.9]}),
                    steps=[
                        steps.checkout,
                        steps.python("${{ matrix.python-version}}"),
                        steps.upgrade("pip nox"),
                        steps.test,
                    ],
                )
            ),
        )


# utilities


def remove(path):
    from shutil import rmtree

    with suppress(FileNotFoundError):
        rmtree(path)
        print(f"removed {path}")


def copyfile(*args, **kwargs):
    from shutil import copyfile

    copyfile(*args, **kwargs)


def write(path, input):
    Path(path).write_text(input)
