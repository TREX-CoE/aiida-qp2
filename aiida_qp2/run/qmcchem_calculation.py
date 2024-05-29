# -*- coding: utf-8 -*-
"""
Calculations provided by qp2.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""

# needed in _unpack function
from collections.abc import Sequence

from aiida.common import CalcInfo, CodeInfo
from aiida.engine import CalcJob
from aiida.orm import Dict, Float, Code, Str, StructureData, SinglefileData
from aiida.plugins import DataFactory, CalculationFactory
from pymatgen.core.periodic_table import Element

QP2RunCalculation = CalculationFactory('qp2.run')


class QP2QmcchemRunCalculation(QP2RunCalculation):
    """ AiiDA calculation plugin wrapping the Quantum Package code.
    """
    @classmethod
    def define(cls, spec):
        """ Define inputs and outputs of the calculation."""
        # yapf: disable
        super().define(spec)

        spec.inputs['metadata']['options']['parser_name'].default = 'qp2.qmcchemrun'
