# -*- coding: utf-8 -*-

"""
Testing the QPCreate class and its parser
"""

import pytest

from pathlib import Path
DATA_DIR = Path(__file__).resolve().parent / 'data'

@pytest.mark.filterwarnings('ignore:Creating AiiDA')
def test_create(aiida_profile_clean):
    from aiida.orm import StructureData, Dict, QueryBuilder, Code
    from aiida.plugins import CalculationFactory
    from ase.io import read

    # Find code
    qb = QueryBuilder()
    #qb.append(Code, filters={'attributes.input_plugin': 'qp.create'})
    qb.append(Code)
    codes = [c[0] for c in qb.iterall()]

    code = None
    for c in codes:
        print(c)
        if c.attributes['input_plugin'] == 'qp.create':
            code = c
            break
        if 'qp.create' in c.attributes['input_plugin']:
            code = c
            break

    if code is None:
        pytest.skip('No code qp.create found')

    Calc = CalculationFactory('qp.create')
    structure = StructureData(ase=read(DATA_DIR / 'H2.xyz'))
    parameters = Dict(dict={})

    # get code
    code = Calc.get_code()

    calc = Calc(inputs={'structure': structure,
                        'parameters': parameters,
                        'code': code})


