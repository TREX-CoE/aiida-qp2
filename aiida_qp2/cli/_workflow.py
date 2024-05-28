# -*- coding: utf-8 -*-

import click
from aiida.cmdline.utils import decorators, echo

from .cli_helpers import wf_option, code_option

from . import cli_root


@cli_root.group('workflow')
def workflow():
    """Workflow commands"""
    pass


@workflow.command('jastopt')
@wf_option
@code_option
@click.option('--optimize',
              '-1',
              nargs='+',
              type=click.STRING,
              help='Jastrow parameters to optimize')
@decorators.with_dbenv()
def jastopt_operation(wf, code, optimize):
    """Jastopt operation"""
