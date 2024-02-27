# -*- coding: utf-8 -*-


import click

from aiida.cmdline.commands.cmd_data import verdi_data
from aiida import cmdline
from aiida.cmdline.utils import decorators, echo
from cli_helpers import wf_option

_QP_GROUP = "qp2_project_group"

@verdi_data.group("qp2")
def smart():
    """Manage qp2"""


@smart.command("create")
@click.argument("name", type=click.STRING)
@click.option("--structure", "-s", type=click.STRING, required=True, help="Structure to use")
@click.option("--basis_set", "-b", type=click.STRING, required=False, help="Basis set to use")
@cmdline.params.options.CODE()
@decorators.with_dbenv()
def create(name, structure, basis_set, code):
    """Create a qp2 project"""

    if code is None:
        echo.echo_critical("Please specify a code")
        return

    if not structure:
        echo.echo_critical("Please specify a structure")
        return

    # Check if structure is not a path
    import pathlib
    from ase.io import read

    if pathlib.Path(structure).exists():
        structure = StructureData(ase=ase.io.read(structure))
    else:
        from aiida.orm import load_node
        try:
            structure = load_node(structure)
        except Exception as e:
            echo.echo_critical(f"Error loading structure: {structure}")
            return

        if not isinstance(structure, StructureData):
            echo.echo_critical(f"Invalid structure: {structure}")
            return

    echo.echo(f"Creating project {name} ...")

    # Find the group
    from aiida.orm import QueryBuilder, Group, Dict

    qb = QueryBuilder()
    qb.append(Group, filters={"label": _PQ_GROUP})
    group = qb.first()
    if group is None:
        echo.echo_success("Group qp2 does not exist, creating it")
        group = Group(label=_PQ_GROUP)
        group.store()
        group.base.extras.set("active_project", None)
    else:
        group = group[0]

    inputs = {"code": code,
              "structure": structure,
              "parameters": Dict(dict={}) }

    if basis_set:
        inputs["basis_set"] = Str(basis_set)

    Create = CalculationFactory("qp2.create")
    calc = Create(inputs=inputs)

    from aiida.engine import run
    ret = run(calc)

    ret["wavefunction"].base.extras.set("name", name)
    ret["wavefunction"].base.extras.set("default_code", code.pk)

