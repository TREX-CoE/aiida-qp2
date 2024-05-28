# -*- coding: utf-8 -*-

import numpy as np

from aiida.plugins import DataFactory, CalculationFactory

from aiida.orm import load_node
from aiida.orm import load_code
from aiida.engine import run
from aiida import load_profile
from aiida_qp2.utils.wavefunction_handler import wavefunction_handler

SinglefileData = DataFactory('core.singlefile')
Dict = DataFactory('core.dict')
List = DataFactory('core.list')
Code = DataFactory('core.code')

Calculation = CalculationFactory('qp2.run')


class JastOpt():
    def __init__(self,
                 wavefunction: SinglefileData,
                 code: Code,
                 parameter_setter: callable,
                 parameter_getter: callable = None,
                 qmcchem_prepend: list = []):

        self._wavefunction = wavefunction
        self.wavefunction = None
        self.code = code
        self.parameter_setter = parameter_setter
        self.parameter_getter = parameter_getter
        self.qmcchem_prepend = qmcchem_prepend

    def __call__(self, parameters: tuple):
        return self.run(parameters)[0]

    def run(self, parameters: dict):
        self.set_parameters(parameters)
        builder = Calculation.get_builder()
        builder.parameters = Dict({
            'run_type': 'qmcchem',
            'qp_prepend': self.qmcchem_prepend
        })
        builder.wavefunction = self.wavefunction
        builder.code = self.code
        ret = run(builder)
        return ret['output_energy'], ret['output_energy_error']

    def set_parameters(self, parameters):
        operation = self.parameter_setter(parameters)
        self.wavefunction = wavefunction_handler(self._wavefunction,
                                                 operation)['wavefunction']
