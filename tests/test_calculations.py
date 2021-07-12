# -*- coding: utf-8 -*-
""" Tests for calculations

"""
import os
from math import fabs
from aiida.plugins import CalculationFactory
from aiida.engine import run
from aiida.orm import Dict

from . import TEST_DIR


def test_process(qp2_code):
    """Test running a calculation
    note this does not test that the expected outputs are created of output parsing"""

    # Prepare input parameters
    ezfio_name = 'hcn.ezfio'
    qp2_commands = [f'set_file {ezfio_name}', 'run scf']

    ezfio_tar = os.path.join(TEST_DIR, 'input_files', f'{ezfio_name}.tar.gz')
    prepend_commands = [f'cp {ezfio_tar} .']

    qp2_parameters = {
        'qp_prepend': prepend_commands,
        'qp_commands': qp2_commands,
        'ezfio': ezfio_name
    }

    inputs = {'code': qp2_code, 'parameters': Dict(dict=qp2_parameters)}
    #file1 = SinglefileData(file=os.path.join(TEST_DIR, 'input_files', 'file1.txt'))

    result = run(CalculationFactory('qp2'), **inputs)
    energy = float(result['output_energy'])

    assert fabs(energy - 92.827856662751) < 0.0000000001
