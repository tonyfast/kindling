def load_ipython_extension(shell):
    from doit import load_ipython_extension
    load_ipython_extension(shell)
    from .dodo import task_new, task_develop , task_docs
    shell.user_ns.update(
        {x.__name__: x for x in (task_new, task_develop , task_docs)}
    )

def unload_ipython_extension(shell):
    pass