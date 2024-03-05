# -*- coding: utf-8 -*-

import click

from . import cli_root

from .cli_helpers import wf_option, code_option

@cli_root.group("workflow")
def workflow():
    """Workflow commands"""
    pass

@workflow.command("jastopt")
@wf_option
@code_option
@click.option("--optimize", -1, nargs="+", type=string, help="Jastrow parameters to optimize")
@decorators.with_dbenv()
def jastopt_operation(wf, code, optimize):
    """Jastopt operation"""


