# -*- coding: utf-8 -*-

import click

from aiida import cmdline
from aiida.cmdline.commands.cmd_data import verdi_data
from aiida.cmdline.groups import VerdiCommandGroup
from aiida.cmdline.params import options, types
from aiida.cmdline.utils import decorators, echo

from .cli_helpers import wf_option, code_option

from . import cli_root

@cli_root.group("edit")
def edit():
    """
    Edit a Wavefunction
    """
    pass

@edit.command("operation")
@wf_option
@click.option("-g", "--get", type=click.STRING, nargs=1, multiple=True, help="Get the value of a parameter")
@click.option("-s", "--set", type=click.STRING, nargs=2, multiple=True, help="Set the value of a parameter")
@decorators.with_dbenv()
def edit_operation(wavefunction, get, set):
    """
    Edit the operation of a Wavefunction, setter fo always first then getters
    """

    if not wavefunction:
        echo.echo_critical("No wavefunction specified")
        return

    echo.echo(f"Editing wavefunction {wavefunction.pk}")

    operations = []

    if set:
        for key, value in set:
            operations.append(("set", key, value))

    if get:
        for key in get:
            operations.append(("get", key, None))

    from aiida_qp2.utils.wavefunction_handler import wavefunction_handler
    from aiida.orm import List

    ret  = wavefunction_handler(wavefunction, List(operations))

    if "data" in ret:
        data = ret["data"].get_list()
        for line in data:
            echo.echo_dictionary(line)

    if "wavefunction" in ret:
        echo.echo_success("Wavefunction edited")

@edit.command("interactive")
@wf_option
@decorators.with_dbenv()
def edit_interactive(wavefunction):
    """
    Edit the wavefunction interactively
    """

    if not wavefunction:
        echo.echo_critical("No wavefunction specified")
        return

    _WF_NAME = "wavefunction.wf.tar.gz"
    from aiida_qp2.utils.ezfio import ezfio
    import tempfile
    import tarfile
    import os
    from IPython import start_ipython

    with tempfile.TemporaryDirectory() as temp_dir:
        wf_path = os.path.join(temp_dir, _WF_NAME)
        with open(wf_path, 'wb') as handle, \
             wavefunction.open(mode='rb') as wavefunction_handle:
            handle.write(wavefunction_handle.read())
        # untar the wavefunction
        with tarfile.open(wf_path, 'r:gz') as tar:
            tar.extractall(temp_dir)
        ezfio_path = os.path.join(temp_dir, "aiida.ezfio")
        ezfio.set_file(ezfio_path)
        echo.echo("")
        echo.echo("#"*80)
        echo.echo("")
        echo.echo("You can now edit the wavefunction (wf) using the ezfio object")
        echo.echo("")
        echo.echo("Example: wf.set_jastrow_j2e_type('Mu')")
        echo.echo("         wf.set_jastrow_j1e_type('None')")
        echo.echo("         wf.get_jastrow_j2e_type('Mu')")
        echo.echo("         [Out]: 'Mu'")
        echo.echo("")
        echo.echo_warning("This is not (yet) a calcjob! The changes are not logged, and the provenance is not tracked")
        echo.echo("")
        echo.echo("#"*80)
        echo.echo("")

        start_ipython(argv=[], user_ns={"wf": ezfio})

        click.confirm("Do you want to save the changes?", default=True, abort=True)
        from aiida.orm import SinglefileData

        with tarfile.open(wf_path, 'w:gz') as tar:
            tar.add(ezfio_path, arcname="aiida.ezfio")
        with open(wf_path, 'rb') as handle:
            wavefunction = SinglefileData(file=handle)
            wavefunction.base.attributes.all["wavefunction"] = True
            wavefunction.store()

        echo.echo_success(f"Wavefunction edited and stored (pk={wavefunction.pk})")



@edit.command("from_file")
@wf_option
@click.argument("file", type=click.Path(exists=True))
@decorators.with_dbenv()
def edit_from_file(wavefunction, file):
    """
    Edit the wavefunction from a file
    """

    if not wavefunction:
        echo.echo_critical("No wavefunction specified")
        return

    from aiida.orm import SinglefileData
    import re

    operations = []
    with open(file, 'r') as handle:
        getter = re.compile(r"get\s+(\w+)")
        setter = re.compile(r'set\s+(\w+)\s+"([^"]*)"')
        for line in handle:
            match = getter.match(line)
            if match:
                key = match.group(1)
                operations.append(("get", key, None))
                continue
            match = setter.match(line)
            if match:
                key = match.group(1)
                value = match.group(2)
                operations.append(("set", key, value))
                continue

    from aiida_qp2.utils.wavefunction_handler import wavefunction_handler
    from aiida.orm import List

    ret  = wavefunction_handler(wavefunction, List(operations))

    if "data" in ret:
        data = ret["data"].get_list()
        for line in data:
            echo.echo_dictionary(line)

    if "wavefunction" in ret:
        echo.echo_success(f"Wavefunction edited and stored (pk={wavefunction.pk})")
    else:
        echo.echo("Wavefunction unmofified")


