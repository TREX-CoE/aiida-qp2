# -*- coding: utf-8 -*-
from . import _QP_GROUP


class CalcHolder():
    """
    Helper class to hold information about a calculation
    """
    def __init__(self, child, job, name, par):
        self.child = child
        self.job = job
        self.name = name
        self.par = par
        self.active = False

    @property
    def energy(self):
        try:
            return self.job.outputs['output_energy'].value
        except:
            return None

    @property
    def label(self):
        wf_pk = self.child
        name = self.name
        if name == 'wavefunction_handler':
            name = 'edit'
        msg = f'{name}: {wf_pk}'
        if self.energy is not None:
            msg += f' | {self.energy:.6f}'
        if self.active:
            msg = '\033[1m' + msg + '\033[0m'
        return msg

    @property
    def ctime(self):
        return self.job.ctime

    @property
    def graph_label(self):
        wf_pk = self.child
        name = self.name
        if name == 'wavefunction_handler':
            name = 'edit'
        msg = f'{wf_pk}\n{name}'
        if self.energy is not None:
            msg += f'\n{self.energy:.6f}'
        return msg


def show_all(style):

    import sys
    from aiida.orm import QueryBuilder, Group, SinglefileData as Wavefunction
    from aiida.orm import CalcJobNode, Dict, load_group, CalcFunctionNode
    from aiida.cmdline.utils import decorators, echo

    try:
        group = load_group(_QP_GROUP)
    except Exception as e:
        echo.echo(e)
        echo.echo_critical('Group qp2 does not exist')
        return

    if group.base.extras.all['active_project'] is None:
        echo.echo_error('No active project')
        return

    qb = QueryBuilder()
    qb.append(Group, filters={'label': _QP_GROUP}, tag='group')
    qb.append(Wavefunction,
              filters={'id': group.base.extras.all['active_project']},
              with_group='group',
              tag='wavefunction')
    if qb.count() == 1:
        wavefunction, = qb.first()
        echo.echo(f"Active project: {wavefunction.base.extras.all['name']}")
    else:
        echo.echo_error(f'No active project')

    qb = QueryBuilder()
    qb.append(Wavefunction,
              filters={'id': group.base.extras.all['active_project']},
              tag='mother')
    qb.append(Wavefunction,
              with_ancestors='mother',
              tag='child',
              project=['id'])
    qb.append(CalcJobNode, with_outgoing='child', tag='calc', project=['*'])
    qb.append(Dict,
              with_outgoing='calc',
              tag='dict',
              project=['attributes.run_type'])
    qb.append(Wavefunction, with_outgoing='calc', tag='par', project=['id'])

    # Special case for calcfunctions
    qbf = QueryBuilder()
    qbf.append(Wavefunction,
               filters={'id': group.base.extras.all['active_project']},
               tag='mother')
    qbf.append(Wavefunction,
               with_ancestors='mother',
               tag='child',
               project=['id'])
    qbf.append(CalcFunctionNode,
               with_outgoing='child',
               tag='calc',
               project=['*', 'label'])
    qbf.append(Wavefunction, with_outgoing='calc', tag='par', project=['id'])

    echo.echo(f'Number of wavefunctions: {qb.count() + qbf.count()}')
    echo.echo('')

    # get data
    nodes = []
    for child, job, a, par in qb.iterall():
        nodes.append(CalcHolder(child, job, a, par))
    for child, job, a, par in qbf.iterall():
        nodes.append(CalcHolder(child, job, a, par))

    if len(nodes) > 0:
        newest = sorted(nodes, key=lambda x: x.job.ctime)[-1]
        newest.active = True

    if style == 'plain':
        show_plain(wavefunction, nodes)
        return

    if style == 'tree':
        show_tree(wavefunction, nodes)
        return

    if style == 'graph':
        show_graph(wavefunction, nodes)
        return


def show_plain(wavefunction, nodes):
    from aiida.cmdline.utils import echo
    echo.echo(f'Parent: {wavefunction.pk}')
    for ch in sorted(nodes, key=lambda x: x.job.ctime):
        echo.echo(ch.label)


def show_tree(wavefunction, nodes):

    import sys
    from aiida.cmdline.utils import echo

    try:
        from treelib import Tree
    except ImportError:
        echo.echo('Please install treelib to show the tree')
        echo.echo('')
        return

    tree = Tree()
    tree.create_node(wavefunction.pk,
                     wavefunction.pk,
                     data=CalcHolder(wavefunction.pk, None, 'root', None))

    for ch in sorted(nodes, key=lambda x: x.job.ctime):
        try:
            tree.create_node(ch.label, ch.child, parent=ch.par, data=ch)
        except:
            pass

    if tree.depth() > 20:
        echo.echo_warning('Tree is very deep')

    ptree = tree.show(stdout=False, data_property='label')

    # First fill white space in ptree
    def _length(s):
        s = s.replace('\033[1m', '')
        s = s.replace('\033[0m', '')
        return len(s)

    longest_line = max(_length(x) for x in ptree.split('\n'))

    # Add white space to the end of each line
    ptree = '\n'.join(x + ' ' * (longest_line - _length(x)) + '|'
                      for x in ptree.split('\n'))

    dtree = tree.show(stdout=False,
                      data_property='energy',
                      line_type='ascii-ex')
    dtree = dtree.replace('\u2502', '')
    dtree = dtree.replace('\u251c\u2500\u2500 ', '')
    dtree = dtree.replace('\u2514\u2500\u2500 ', '')

    dtree = dtree.split('\n')
    dtree = [x.strip() for x in dtree]

    # This is messy (and should be done in a better way)
    try:
        from termgraph.module import Data, BarChart, Args, Colors

        data_without_none = [
            float(x) for x in dtree if x.strip() not in ('None', '')
        ]
        if len(data_without_none) == 0:
            raise NotImplementedError
        max_data = max(data_without_none)
        data = [
            float(x) if x.strip() not in ('None', '') else max_data
            for x in dtree
        ]
        labels = [
            'GOOD' if x.strip() not in ('None', '') else 'BAAD' for x in dtree
        ]
        ldata = len(data)
        data = [abs(x) for x in data]
        data = [[x] for x in data]
        data = Data(data, labels)

        colors = [
            Colors.Red if ii % 2 == 0 else Colors.Red for ii in range(ldata)
        ]

        chart = BarChart(data, Args(colors=colors))

        from io import StringIO
        capture_output = StringIO()
        original_stdout = sys.stdout
        try:
            sys.stdout = capture_output
            echo.echo(chart.draw())
        finally:
            sys.stdout = original_stdout

        bg = capture_output.getvalue().strip()
        stree = [' ' * (len(ptree.split('\n')[0]) - 1) + f'| ']

        bg = bg.split('\n')
        bg = [l.replace('GOOD:', '') if 'GOOD' in l else '' for l in bg]

        for line, dline in zip(ptree.split('\n'), bg):
            stree.append(line + ' ' + dline)

        ptree = '\n'.join(stree)

    except ImportError:
        echo.echo('Please install termgraph to show the plots')
        echo.echo('')

    except NotImplementedError:
        pass

    echo.echo(ptree)


def show_graph(wavefunction, nodes):

    from aiida.cmdline.utils import echo

    missing_modules = []
    try:
        import asciinet as an
    except ImportError:
        missing_modules.append('asciinet')

    try:
        import networkx as nx
    except ImportError:
        missing_modules.append('networkx')

    if len(missing_modules) > 0:
        echo.echo(
            f"Please install the following modules to show the graph: {', '.join(missing_modules)}"
        )
        echo.echo('')
        return

    dict_of_nodes = {x.child: x for x in nodes}
    dict_of_nodes[wavefunction.pk] = CalcHolder(wavefunction.pk, None, 'root',
                                                None)

    G = nx.DiGraph()

    for ch in sorted(nodes, key=lambda x: x.job.ctime):
        G.add_node(ch.graph_label)
        if ch.par is not None:
            G.add_edge(dict_of_nodes[ch.par].graph_label, ch.graph_label)

    echo.echo(an.graph_to_ascii(G))
