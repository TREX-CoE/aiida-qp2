#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run a test calculation on the computer.

Usage: ./example_scf_from_ezfio.py
"""
from os import path
import click
from aiida import cmdline, engine
from aiida.plugins import CalculationFactory
from aiida.orm import Dict, load_code, load_computer
from aiida.common.exceptions import NotExistent

INPUT_DIR = path.join(path.dirname(path.realpath(__file__)), 'input_files')
COMP_NAME = 'tutor'


def test_run_scf(qp2_code, computer, ezfio_name):
    """Run SCF calculation with QP code using existing EZFIO file.
    """
    if not computer:
        try:
            computer = load_computer(COMP_NAME)
        except:
            raise Exception('You forgot to provide the --computer argument'
                            ) from NotExistent

    if not qp2_code:
        try:
            qp2_code = load_code(f'qp2@{COMP_NAME}')
        except:
            raise Exception(
                'You forgot to provide the --code argument') from NotExistent

    if not ezfio_name:
        raise Exception('You forgot to provide the --ezfio_filename argument')

    # Prepare input parameters
    # ezfio_name = 'hcn.ezfio' pass from the command line
    qp2_commands = [f'set_file {ezfio_name}', 'run scf']

    ezfio_tar = path.join(INPUT_DIR, f'{ezfio_name}.tar.gz')
    prepend_commands = [f'cp {ezfio_tar} .']

    qp2_parameters = {
        'qp_prepend': prepend_commands,
        'qp_commands': qp2_commands,
        'ezfio_name': ezfio_name
    }

    inputs = {
        'code': qp2_code,
        'parameters': Dict(dict=qp2_parameters),
        'metadata': {
            'computer': computer,
            'options': {
                'output_wf_basename': ezfio_name
            }
        }
    }

    result = engine.run(CalculationFactory('qp2'), **inputs)
    energy = float(result['output_energy'])

    print(f'Computed SCF energy: \n  {energy}')


@click.command()
@cmdline.utils.decorators.with_dbenv()
@cmdline.params.options.CODE()
@cmdline.params.options.COMPUTER()
@click.option('--ezfio_filename', '-e', help='EZFIO file name.')
def cli(code, computer, ezfio_filename):
    """Run example_scf_from_ezfio: SCF calculation using QP2 on existing EZFIO database.

    Example usage:
    $ ./example_scf_from_ezfio.py --code qp2@localhost --computer localhost --ezfio_filename hcn.ezfio

    Alternative usage (loads qp2@tutor code and tutor computer):
    $ ./example_scf_from_ezfio.py

    Help: $ ./example_scf_from_ezfio.py --help
    """

    test_run_scf(code, computer, ezfio_filename)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
