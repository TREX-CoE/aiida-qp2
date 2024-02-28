# -*- coding: utf-8 -*-


import click

from aiida.cmdline.commands.cmd_data import verdi_data
from aiida import cmdline
from aiida.cmdline.utils import decorators, echo
from aiida_qp2.cli_helpers import wf_option, code_option

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
        from aiida.orm import StructureData
        structure = StructureData(ase=read(structure))
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
    qb.append(Group, filters={"label": _QP_GROUP})
    group = qb.first()
    if group is None:
        echo.echo_success("Group qp2 does not exist, creating it")
        group = Group(label=_QP_GROUP)
        group.store()
        group.base.extras.set("active_project", None)
    else:
        group = group[0]

    inputs = {"code": code,
              "structure": structure,
              "parameters": Dict(dict={}) }

    if basis_set:
        inputs["basis_set"] = Str(basis_set)

    from aiida.plugins import CalculationFactory
    Create = CalculationFactory("qp2.create")
    calc = Create(inputs=inputs)

    from aiida.engine import run
    ret = run(calc)

    ret["wavefunction"].base.extras.set("name", name)
    ret["wavefunction"].base.extras.set("default_code", code.pk)

    group.add_nodes(ret["wavefunction"])

@smart.command("list")
@decorators.with_dbenv()
def list():
    """List qp2 projects"""

    from aiida.orm import QueryBuilder, Group, SinglefileData as Wavefunction
    from aiida.orm import load_node, load_group

    group = load_group(_QP_GROUP)

    qb = QueryBuilder()
    qb.append(Group, filters={"label": _QP_GROUP}, tag="group")
    qb.append(Wavefunction, filters={ 'attributes.wavefunction': True,
                                      'extras': {'has_key': 'name'}},
                            with_group="group",
                            tag="wavefunction")

    echo.echo(f"List of qp2 projects ({qb.count()}):")
    echo.echo("")

    # Decorator

    from functools import wraps

    def bolderrer(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if args[0] % 2 == 0:
                return f(*args, **kwargs)
            else:
                return f"\033[1m{f(*args, **kwargs)}\033[0m"
        return wrapper


    @bolderrer
    def get_name(n, w):
        return w.base.extras.all['name']

    @bolderrer
    def get_formula(n, w):
        return w.base.attributes.all['formula'] if 'formula' in w.base.attributes.all else ''

    @bolderrer
    def get_active(n, w):
        return "*" if group.base.extras.all['active_project'] == w.pk else ""

    @bolderrer
    def get_code(n, w):
        return load_node(w.base.extras.all['default_code']).full_label

    data = [ (get_active(n, w),
              get_name(n, w),
              w.pk,
              w.ctime.strftime('%Y-%m-%d %H:%M:%S'),
              w.user,
              get_formula(n, w),
              get_code(n,w)) for n, (w,) in enumerate(qb.iterall())]

    import tabulate

    echo.echo(tabulate.tabulate(data, headers=[" ", "Name", "ID", "Time", "User", "Formula", "Def. code"]))

@smart.command("activate")
@click.argument("pk", type=click.INT)
@decorators.with_dbenv()
def activate(pk):
    """Activate a pq2 project"""

    from aiida.orm import QueryBuilder, Group, SinglefileData as Wavefunction, load_group

    try:
        group = load_group(_QP_GROUP)
    except Exception as e:
        echo.echo_critical("Group qp2 does not exist")
        return

    qb = QueryBuilder()
    qb.append(Group, filters={"label": _QP_GROUP}, tag="group")
    qb.append(Wavefunction, filters={ 'id': pk},
                            with_group="group",
                            tag="wavefunction")

    if qb.count() == 1:
        echo.echo_success(f"Activated {qb.first()[0].base.extras.all['name']}")
        group.base.extras.set("active_project", pk)
    else:
        echo.echo_error(f"Project with pk={pk} not found")

@smart.command("deactivate")
@decorators.with_dbenv()
def deactivate():
    """Deactivate a pq2 project"""

    from aiida.orm import QueryBuilder, Group, SinglefileData as Wavefunction, load_group

    try:
        group = load_group(_QP_GROUP)
    except Exception as e:
        echo.echo_critical("Group qp2 does not exist")
        return

    group.base.extras.set("active_project", None)
    echo.echo_success("Deactivated project")

@smart.command("run")
@click.argument("operation", type=click.STRING)
@code_option
@wf_option
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@decorators.with_dbenv()
def run(operation, code, wavefunction, args):
    """Run a pq2 operation"""

    echo.echo(f"Running operation {operation} ...")
    echo.echo("")

    if wavefunction is None:
        echo.echo_critical("Please specify a wavefunction or activate a project")
        return
    else:
        echo.echo(f"Wavefunction: {wavefunction.pk} generated at {wavefunction.ctime}")

    if code is None:
        echo.echo_critical("Please specify a code")
        return
    else:
        echo.echo(f"Code: {code.full_label}")

    from aiida.plugins import CalculationFactory
    from aiida.orm import Dict

    Calc = CalculationFactory("qp2.run")

    inputs = {"wavefunction": wavefunction,
              "code": code,
              "parameters": Dict(dict={"run_type": operation,
                                       "qp_append": "".join(args)}) }

    calc = Calc(inputs=inputs)

    from aiida.engine import run

    ret = run(calc)

    if "output_energy" in ret:
        echo.echo(f"Energy: {ret['output_energy'].value}")
        echo.echo("")
        echo.echo_success(f"Operation {operation} completed")
    else:
        echo.echo_critical(f"Operation {operation} failed")

@smart.command("show")
@decorators.with_dbenv()
def show():
    """Show active qp2 project"""

    from aiida.orm import QueryBuilder, Group, SinglefileData as Wavefunction
    from aiida.orm import CalcJobNode, Dict, load_group

    try:
        group = load_group(_QP_GROUP)
    except Exception as e:
        echo.echo(e)
        echo.echo_critical("Group qp2 does not exist")
        return

    if group.base.extras.all['active_project'] is None:
        echo.echo_error("No active project")
        return

    qb = QueryBuilder()
    qb.append(Group, filters={"label": _QP_GROUP}, tag="group")
    qb.append(Wavefunction, filters={ 'id': group.base.extras.all['active_project']},
                            with_group="group",
                            tag="wavefunction")
    if qb.count() == 1:
        wavefunction, = qb.first()
        echo.echo(f"Active project: {wavefunction.base.extras.all['name']}")
    else:
        echo.echo_error(f"No active project")

    qb = QueryBuilder()
    qb.append(Wavefunction, filters={ 'id': group.base.extras.all['active_project']}, tag="mother")
    qb.append(Wavefunction, with_ancestors="mother", tag="child", project=["id"])
    qb.append(CalcJobNode, with_outgoing="child", tag="calc", project=["*"])
    qb.append(Dict, with_outgoing="calc", tag="dict", project=["attributes.run_type"])
    qb.append(Wavefunction, with_outgoing="calc", tag="par", project=["id"])
    echo.echo(f"Number of wavefunctions: {qb.count()}")
    echo.echo("")

    try:
        from treelib import Tree
    except ImportError:
        echo.echo("Please install treelib to show the tree")
        echo.echo("")
        Tree = None

    if Tree is None:
        echo.echo(f"Parent: {wavefunction.pk}")
        for child, job, a, par in sorted(qb.iterall(), key=lambda x: x[1].ctime):
            echo.echo(f"{a}: {child}")
    else:
        tree = Tree()
        tree.create_node(wavefunction.pk, wavefunction.pk)

        for child, job, a, par in sorted(qb.iterall(), key=lambda x: x[1].ctime):
            tree.create_node(f"{a}: {child}", child, parent=par)

        echo.echo(tree.show(stdout=False))

@smart.command("set_default_code")
#@click.argument("code", type=click.STRING, help="Code to set as default, provide pk, uuid or label")
@click.argument("code", type=click.STRING)
@decorators.with_dbenv()
def set_default_code(code):
    """Set default code for active qp2 project"""

    from aiida.orm import QueryBuilder, Group, SinglefileData as Wavefunction

    try:
        code = load_code(code)
    except:
        echo.echo_error(f"Code {code} not found")
        return

    try:
        group = load_group(_QP_GROUP)
    except Exception as e:
        echo.echo_critical("Group qp2 does not exist")
        return

    qb = QueryBuilder()
    qb.append(Group, filters={"label": _QP_GROUP}, tag="group")
    qb.append(Wavefunction, filters={ 'id': group.base.extras.all['active_project']},
                            with_group="group",
                            tag="wavefunction")

    if qb.count() == 1:
        wavefunction, = qb.first()
        echo.echo(f"Setting default code for {wavefunction.base.extras.all['name']} to {code}")
        wavefunction.base.extras.set("default_code", code.pk)
    else:
        echo.echo_error(f"No active project")

