# -*- coding: utf-8 -*-
"""
Helper functions for the CLI
"""

import click

from aiida.orm import load_node, Group, SinglefileData, QueryBuilder

from functools import wraps

_PQ_GROUP = "pq2_project_group"

def pk_decorator(func):
    """
    Decorator add click option `--pk` to the function
    if `--pk` is not provided, the function will try to find
    the active project and use the latest wavefunction
    """

    @click.option("--wavefunction", "-w", type=click.STRING, default=None, help="Wavefunction to use")
    @wraps(func)
    def f(*_args, **kwargs):
        if kwargs["wavefunction"] is not None:
            from aiida.orm import load_node
            kwargs["wavefunction"] = load_node(kwargs["wavefunction"])
        else:
            from aiida.orm import QueryBuilder, Group, SinglefileData as Wavefunction
            qb = QueryBuilder()
            qb.append(Group, filters={"label": _PQ_GROUP}, tag="group")
            qb.append(Wavefunction, filters={ 'id': group.base.extras.all['active_project']},
                                    with_group="group",
                                    tag="wavefunction")
            if qb.count() > 0:
                wavefunction, = qb.first()
                qb = QueryBuilder()
                qb.append(Wavefunction, filters={ 'id': wavefunction.pk}, tag="mother")
                qb.append(Wavefunction, with_ancestors="mother", tag="child")
                qb.order_by({"child": {'ctime': 'desc'}})
                if qb.count() > 0:
                    kwargs["wavefunction"] = qb.first()[0]
                else:
                    kwargs["wavefunction"] = wavefunction
            else:
                kwargs["wavefunction"] = None


        return func(*_args, **kwargs)
    return f
