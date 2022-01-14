#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a 2-step test QP calculation.

Usage:
  (1) ./example_scf_fromXYZ.py
  (2) verdi run example_scf_fromXYZ.py
"""
from os import path
from pymatgen.core import Molecule
import click
from aiida import orm, engine, cmdline
from aiida.common.exceptions import NotExistent

INPUT_DIR = path.join(path.dirname(path.realpath(__file__)), 'input_files')
XYZ_FILE = 'hcn.xyz'
EZFIO_NAME = XYZ_FILE.replace('.xyz', '.ezfio')

CODE_NAME = 'qp2_singularity'
COMP_NAME = 'olympe'

#CODE_NAME = 'qp2'
#COMP_NAME = 'tutor'


def load_aiida_setup():
    """Load computer and code from the AiiDA database.
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
        code = orm.load_code(f'{CODE_NAME}@{COMP_NAME}')
    except NotExistent:
        # Setting up code via python API (or use "verdi code setup")
        raise Exception(
            'Create the qp2 code for this example') from NotExistent

    return (code, computer)


def test_run_create_ezfio(code, computer):
    """Run JOB #1: create an EZFIO database from XYZ file
    """
    # Set up inputs
    builder = code.get_builder()

    # COMPILE THE DICTIONARY OF QP2 PARAMETERS
    create_parameters = {
        'qp_create_ezfio': {
            #'basis': '"6-31g"',
            'basis': '"aug-cc-pvtz"',
            'charge': '0',
            'output': EZFIO_NAME,
        },
        'xyz': XYZ_FILE,
        'wf_basename': EZFIO_NAME
    }

    builder.metadata.options.output_filename = 'qp.out'
    builder.metadata.options.output_wf_basename = EZFIO_NAME

    #builder.metadata.options.computer = computer.label

    # ============== CREATE_EZFIO SPECIFIC PARAMETERS =========== #
    # QP run to create EZFIO database from the XYZ file
    mol = Molecule.from_file(path.join(INPUT_DIR, XYZ_FILE))
    #print(mol)
    structure = orm.StructureData(pymatgen_molecule=mol)
    # uncomment to see how Molecule->StructureData conversion modifies the atomic positions
    #mol2 = structure.get_pymatgen_molecule()
    #print(mol2)

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
    #path_to_ezfio = ezfio_RemoteData.get_remote_path()
    #computer_with_ezfio = ezfio_RemoteData.get_computer_name()

    ezfio_full_name = ezfio_RemoteData.filename
    #path_to_ezfio.split('/')[-1]
    #ezfio_base_name = ezfio_full_name.split('.tar.gz')[0]

    print('EZFIO RemoteData name   : ', ezfio_full_name)
    print('EZFIO RemoteData object : ', ezfio_RemoteData)

    return ezfio_RemoteData


def test_run_scf_from_ezfio(code, computer, ezfio_RemoteData_inp):
    """Run JOB #2: SCF calculation on the existing EZFIO database from JOB #1
    """
    builder_scf = code.get_builder()
    #ezfio_name = 'hcn.ezfio'

    #path_to_ezfio = ezfio_RemoteData_inp.get_remote_path()
    ezfio_full_name = ezfio_RemoteData_inp.filename
    ezfio_inp_name = ezfio_full_name.split('.tar.gz')[0]

    qp2_commands = [f'set_file {ezfio_inp_name}', 'run scf']

    # COMPILE THE DICTIONARY OF QP2 PARAMETERS
    qp2_parameters = {
        'wf_basename': ezfio_inp_name,
        'qp_commands': qp2_commands
    }

    # conventional QP run
    builder_scf.parameters = orm.Dict(dict=qp2_parameters)
    builder_scf.wavefunction = ezfio_RemoteData_inp

    builder_scf.metadata.options.output_filename = 'qp.out'
    builder_scf.metadata.options.output_wf_basename = ezfio_inp_name
    #builder_scf.metadata.options.computer = computer.label

    builder_scf.code = code
    builder_scf.metadata.description = 'Test job submission with the aiida_qp2 plugin to run SCF calculations'
    builder_scf.metadata.computer = computer

    print('\nQP2 run_scf execution: STARTED\n')

    result = engine.run(builder_scf)

    print('\nQP2 run_scf execution: FINISHED\n')

    ezfio_RemoteData = result['output_wavefunction']

    ezfio_full_name = ezfio_RemoteData.filename
    #ezfio_base_name = ezfio_full_name.split('.tar.gz')[0]

    print('EZFIO RemoteData name   : ', ezfio_full_name)
    print('EZFIO RemoteData object : ', ezfio_RemoteData)

    energy = result['output_energy']

    return energy


@click.command()
@cmdline.utils.decorators.with_dbenv()
def cli():
    """Run example_scf_fromXYZ.py : execute 2 jobs using QP code.

    Job #1: create an EZFIO database from the existing XYZ (hcn.xyz) file using `qp create_ezfio [arguments]` command;

        Output: ezfio (AiiDA-native RemoteData object) from the AiiDA database.

    Job #2: perform SCF calculation on the EZFIO database created in the prevous step;

        Output: SCF energy (AiiDA-native Float object) from the AiiDA database

    Example usage: $ ./example_scf_fromXYZ.py

    Alternative:   $ verdi run example_scf_fromXYZ.py

    Help: $ ./example_scf_fromXYZ.py --help
    """
    (code, computer) = load_aiida_setup()
    ezfio_RemoteData = test_run_create_ezfio(code, computer)

    energy_scf = test_run_scf_from_ezfio(code, computer, ezfio_RemoteData)
    print('\nOutput: SCF energy\n', float(energy_scf))


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
