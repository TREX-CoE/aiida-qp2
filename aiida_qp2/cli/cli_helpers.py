# -*- coding: utf-8 -*-
"""
Helper functions for the CLI
"""

import click
from functools import wraps

_QP_GROUP = 'qp2_project_group'


def wf_option(func):
    """
    Decorator add click option `--pk` to the function
    if `--pk` is not provided, the function will try to find
    the active project and use the latest wavefunction
    """
    @click.option('--wavefunction',
                  '-w',
                  type=click.STRING,
                  default=None,
                  help='Wavefunction to use')
    @wraps(func)
    def f(*_args, **kwargs):
        if kwargs['wavefunction'] is not None:
            from aiida.orm import load_node
            kwargs['wavefunction'] = load_node(kwargs['wavefunction'])
        else:
            from aiida.orm import (QueryBuilder, Group, load_group,
                                   SinglefileData as Wavefunction)

            try:
                group = load_group(_QP_GROUP)
            except:
                kwargs['wavefunction'] = None
                return func(*_args, **kwargs)

            qb = QueryBuilder()
            qb.append(Group, filters={'label': _QP_GROUP}, tag='group')
            qb.append(Wavefunction,
                      filters={'id': group.base.extras.all['active_project']},
                      with_group='group',
                      tag='wavefunction')
            if qb.count() == 0:
                kwargs['wavefunction'] = None
                return func(*_args, **kwargs)

            wavefunction, = qb.first()
            qb = QueryBuilder()
            qb.append(Wavefunction,
                      filters={'id': wavefunction.pk},
                      tag='mother')
            qb.append(Wavefunction, with_ancestors='mother', tag='child')
            qb.order_by({'child': {'ctime': 'desc'}})
            if qb.count() > 0:
                kwargs['wavefunction'] = qb.first()[0]
            else:
                kwargs['wavefunction'] = wavefunction

        return func(*_args, **kwargs)

    return f


def code_option(func):
    """
    Decorator add click option `--code` to the function
    if `--code` is not provided, the function will try to find
    the active code
    """
    @click.option('--code',
                  '-c',
                  type=click.STRING,
                  default=None,
                  help='Code to use')
    @wraps(func)
    def f(*_args, **kwargs):
        if kwargs['code'] is not None:
            from aiida.orm import load_node
            kwargs['code'] = load_node(kwargs['code'])
        else:
            from aiida.orm import (QueryBuilder, Code, Group, SinglefileData as
                                   Wavefunction, load_group, load_node)

            try:
                group = load_group(_QP_GROUP)
            except:
                kwargs['code'] = None
                return func(*_args, **kwargs)

            qb = QueryBuilder()
            qb.append(Group, filters={'label': _QP_GROUP}, tag='group')
            qb.append(Wavefunction,
                      filters={'id': group.base.extras.all['active_project']},
                      with_group='group',
                      tag='wavefunction')
            if qb.count() == 0:
                kwargs['code'] = None
                return func(*_args, **kwargs)

            kwargs['code'] = load_node(
                qb.first()[0].base.extras.all['default_code'])

        return func(*_args, **kwargs)

    return f
