# -*- coding: utf-8 -*-
import click

from aiida import cmdline
from aiida.cmdline.commands.cmd_data import verdi_data
from aiida.cmdline.groups import VerdiCommandGroup
from aiida.cmdline.params import options, types
from aiida.cmdline.utils import decorators, echo

from .cli_helpers import wf_option, code_option

from . import cli_root


@cli_root.group('dump')
def dump():
    """
    Dump the data to the file system
    """
    pass


@dump.command('wavefunction')
@wf_option
@click.option('--extract', '-e', is_flag=True, help='Extract the wavefunction')
@decorators.with_dbenv()
def dump_wavefunction(wavefunction, extract):
    """Dump wavefunction to the file system (in the current directory)"""

    from aiida.orm import SinglefileData as Wavefunction

    if wavefunction is None:
        echo.echo_critical('Please specify a wavefunction')
        return

    if not isinstance(wavefunction, Wavefunction):
        echo.echo_critical('Invalid wavefunction')
        return

    import os
    if extract:
        import tarfile
        with wavefunction.open(mode='rb') as handle_wf:
            with tarfile.open(fileobj=handle_wf, mode='r:gz') as handle_tar:
                handle_tar.extractall(path=os.getcwd())
        echo.echo_success(f'Extracted wavefunction to {os.getcwd()}')
    else:
        with open(f'{os.getcwd()}/{wavefunction.pk}_wf.tar.gz', 'wb') as handle_output, \
             wavefunction.open(mode='rb') as handle_input:
            handle_output.write(handle_input.read())
        echo.echo_success(
            f'Dumped wavefunction to {os.getcwd()}/{wavefunction.pk}_wf.tar.gz'
        )


@dump.command('output')
@wf_option
@decorators.with_dbenv()
def dump_output(wavefunction):
    """Show calculation output"""

    from aiida.orm import QueryBuilder, CalcJobNode, FolderData, SinglefileData as Wavefunction
    from aiida.plugins import CalculationFactory

    if wavefunction is None:
        echo.echo_critical('Please specify a wavefunction')
        return

    if not isinstance(wavefunction, Wavefunction):
        echo.echo_critical('Invalid wavefunction')
        return

    qb = QueryBuilder()
    qb.append(Wavefunction, filters={'id': wavefunction.pk}, tag='wf')
    qb.append(CalcJobNode,
              with_outgoing='wf',
              tag='calc',
              project=['attributes.output_filename'])
    qb.append(FolderData,
              with_incoming='calc',
              edge_filters={'label': 'retrieved'},
              tag='output',
              project=['*'])

    if qb.count() < 1:
        echo.echo_error('No output found')
        return

    filename, rf = qb.first()

    with rf.open(filename, mode='r') as handle:
        echo.echo(handle.read())


@dump.command('input')
@wf_option
@decorators.with_dbenv()
def dump_input(wavefunction):
    """Show calculation input"""

    from aiida.orm import QueryBuilder, CalcJobNode, Dict, SinglefileData as Wavefunction
    from aiida.plugins import CalculationFactory

    if wavefunction is None:
        echo.echo_critical('Please specify a wavefunction')
        return

    if not isinstance(wavefunction, Wavefunction):
        echo.echo_critical('Invalid wavefunction')
        return

    qb = QueryBuilder()
    qb.append(Wavefunction, filters={'id': wavefunction.pk}, tag='wf')
    qb.append(CalcJobNode, with_outgoing='wf', tag='calc')
    qb.append(Dict,
              with_outgoing='calc',
              edge_filters={'label': 'parameters'},
              tag='input',
              project=['*'])

    if qb.count() < 1:
        echo.echo_error('No input found')
        return

    params, = qb.first()

    import yaml
    from io import StringIO

    buffer = StringIO()
    yaml.dump(params.get_dict(), buffer)
    buffer.seek(0)
    echo.echo(buffer.read())


cli_root.add_command(dump)
