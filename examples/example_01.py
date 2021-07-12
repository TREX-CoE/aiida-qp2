#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a test calculation on localhost.

Usage: ./example_01.py
"""
from os import path
import click
from aiida import cmdline, engine
from aiida.plugins import CalculationFactory
from aiida.orm import Dict

INPUT_DIR = path.join(path.dirname(path.realpath(__file__)), 'input_files')


def test_run(qp2_code):
    """Run a calculation on the localhost computer.

    Uses test helpers to create AiiDA Code on the fly.
    """
    if not qp2_code:
        raise Exception('You forgot to provide the qp2 code as an input')

    # Prepare input parameters
    ezfio_name = 'hcn.ezfio'
    qp2_commands = [f'set_file {ezfio_name}', 'run scf']

    ezfio_tar = path.join(INPUT_DIR, f'{ezfio_name}.tar.gz')
    prepend_commands = [f'cp {ezfio_tar} .']

    qp2_parameters = {
        'qp_prepend': prepend_commands,
        'qp_commands': qp2_commands,
        'ezfio': ezfio_name
    }

    inputs = {'code': qp2_code, 'parameters': Dict(dict=qp2_parameters)}
    #file1 = SinglefileData(file=os.path.join(TEST_DIR, 'input_files', 'file1.txt'))

    result = engine.run(CalculationFactory('qp2'), **inputs)
    energy = float(result['output_energy'])

    print(f'Computed SCF energy: \n  {energy}')


@click.command()
@cmdline.utils.decorators.with_dbenv()
@cmdline.params.options.CODE()
def cli(code):
    """Run example.

    Example usage: $ ./example_01.py --code qp2@localhost

    Alternative (creates qp2@localhost-test code): $ ./example_01.py

    Help: $ ./example_01.py --help
    """
    test_run(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
