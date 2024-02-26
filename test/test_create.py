# -*- coding: utf-8 -*-

"""
Testing the QPCreate class and its parser
"""

import pytest

from pathlib import Path
DATA_DIR = Path(__file__).resolve().parent / 'data'

@pytest.mark.filterwarnings('ignore:Creating AiiDA')
def test_create(aiida_profile_clean):
    from aiida.orm import StructureData, Dict
    from ase.io import read

    Calc = QPCreate()
    structure = StructureData(ase=read(DATA_DIR / 'H2.xyz'))
    parameters = Dict(dict={})

    calc = Calc(inputs={'structure': structure,
                        'parameters': parameters})


