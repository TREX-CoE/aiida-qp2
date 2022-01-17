#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Load the basis set from the database.

Usage:
  ./example_ezfio_from_gdt.py
"""
from os import path
from pymatgen.core import Molecule
import click
from aiida import orm, cmdline, engine
from aiida.common.exceptions import NotExistent
from aiida.plugins import DataFactory

INPUT_DIR = path.join(path.dirname(path.realpath(__file__)), 'input_files')
XYZ_FILE = 'hcn.xyz'
EZFIO_NAME = XYZ_FILE.replace('.xyz', '.ezfio')
COMP_NAME = 'tutor'


def load_aiida_setup():
    """Load computer and qp2@computer from the AiiDA database.
    """
    #try:
    #    aiida_profile = load_profile(profile)
    #except:
    #    raise Exception('Create the profile for this example') from NotExistent

    # Load the computer
    try:
        computer = orm.load_computer(f'{COMP_NAME}')
    except:
        raise Exception(f'Create the computer {COMP_NAME} for this example'
                        ) from NotExistent

    # Create or load the qp2 code
    try:
        code = orm.load_code(f'qp2@{COMP_NAME}')
    except NotExistent:
        # Setting up code via python API (or use "verdi code setup")
        code = orm.Code(label='qp2',
                        remote_computer_exec=[computer, '~/qp2/bin/qpsh'],
                        input_plugin_name='qp2')

    return (code, computer)


def test_run_create_ezfio(code, computer):
    """Run JOB #1: create an EZFIO database from XYZ file
    """

    # create a StructureData node for the calculation
    mol = Molecule.from_file(path.join(INPUT_DIR, XYZ_FILE))
    structure = orm.StructureData(pymatgen_molecule=mol)

    # Basis set section: build a dictionary with
    #   key   - label of the atom
    #   value - instance of the BasisSet data item corresponding to the "basis_name" basis set
    BasisSet = DataFactory('gaussian.basisset')
    basis_name = 'aug-cc-pVDZ'
    # symbol_set is an attribute of Molecule class from pymatgen, it contains a tuple of unique atoms
    basis_dict = {
        atom: BasisSet.get(element=atom, name=basis_name)
        for atom in mol.symbol_set
    }

    # Set up inputs
    builder = code.get_builder()

    # COMPILE THE DICTIONARY OF QP2 PARAMETERS
    # at the moment the name of the basis set and ECP files is hardcoded in qp2 plugin
    # it can be also provided as one of the metadata arguments
    create_parameters = {
        'qp_create_ezfio': {
            'basis': 'aiida-basis-set',
            'charge': '0',
            'output': EZFIO_NAME,
        },
        'xyz': XYZ_FILE
    }

    builder.basissets = basis_dict

    builder.metadata.options.output_filename = 'qp.out'
    builder.metadata.options.output_wf_basename = EZFIO_NAME

    # ============== CREATE_EZFIO SPECIFIC PARAMETERS =========== #

    # QP run to create EZFIO database from the XYZ file
    builder.structure = structure
    builder.parameters = orm.Dict(dict=create_parameters)

    # =========================================================== #

    builder.code = code
    builder.metadata.description = 'Test job submission with the aiida_qp2 plugin to create an EZFIO database'
    builder.metadata.computer = computer

    # Run the calculation & parse results
    print('\nQP2 create_ezfio execution: STARTED\n')

    result = engine.run(builder)

    print('\nQP2 create_ezfio execution: FINISHED\n')

    ezfio_RemoteData = result['output_wavefunction']
    ezfio_full_name = ezfio_RemoteData.filename

    print('EZFIO RemoteData name   : ', ezfio_full_name)
    print('EZFIO RemoteData object : ', ezfio_RemoteData)

    return 0


@click.command()
@cmdline.utils.decorators.with_dbenv()
def cli():
    """Create EZFIO using GTO basis sets from aiida-gaussian-datatypes plugin

    Creates an EZFIO database from the existing XYZ (hcn.xyz) file using `qp create_ezfio [arguments]` command;

    Output: ezfio (AiiDA-native RemoteData object) from the AiiDA database.

    Example usage: $ ./example_ezfio_from_gdt.py

    Alternative:   $ verdi run example_ezfio_from_gdt.py

    Help: $ ./example_ezfio_from_gdt.py --help
    """

    (code, computer) = load_aiida_setup()
    test_run_create_ezfio(code, computer)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
