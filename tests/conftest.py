import os
from xtlib import console
import xtlib.xt_run as xt_run
from xtlib.helpers import xt_config

def pytest_configure(config):
    """
    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.
    """
    local_config_path = os.environ.get("XT_GLOBAL_CONFIG", None)
    config = xt_config.get_merged_config(local_overrides_path=local_config_path)
    workspace = config.get("general", "workspace")
    console.set_capture(True)
    if workspace != "ws1" and workspace != "xt-demo":
        xt_run.main("xt list workspaces")
        output = console.set_capture(False)
        matching = list(filter(lambda entry: entry.find(workspace) != -1, output))
        if matching:
            xt_run.main(f"xt delete workspace {workspace} --response={workspace}")

        xt_run.main(f"xt create workspace {workspace}")


def pytest_sessionstart(session):
    """
    Called after the Session object has been created and
    before performing collection and entering the run test loop.
    """


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before
    returning the exit status to the system.
    """
    config = xt_config.get_merged_config()
    workspace = config.get("general", "workspace")
    if workspace != "ws1" and workspace != "xt-demo":
        xt_run.main(f"xt delete workspace {workspace} --response={workspace}")


def pytest_unconfigure(config):
    """
    called before test process is exited.
    """
