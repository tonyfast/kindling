if __name__ == "__main__":
    from doit.doit_cmd import DoitMain
    from doit.cmd_base import ModuleTaskLoader
    from sys import argv
    from . import dodo

    DoitMain(ModuleTaskLoader(dodo)).run(argv[1:])
