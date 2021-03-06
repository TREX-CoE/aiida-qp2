#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a 3-step test QP calculation.

Usage:
  (1) ./example_trexio_from_xyz.py
  (2) verdi run example_trexio_from_xyz.py
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
            'basis': '"6-31g"',
            #'basis': '"aug-cc-pvtz"',
            'charge': '0',
            'output': EZFIO_NAME,
        },
        'xyz': XYZ_FILE
    }

    builder.metadata.options.output_wf_basename = EZFIO_NAME
    builder.metadata.options.output_filename = 'qp.out'

    # ============== CREATE_EZFIO SPECIFIC PARAMETERS =========== #
    # QP run to create EZFIO database from the XYZ file
    mol = Molecule.from_file(path.join(INPUT_DIR, XYZ_FILE))
    structure = orm.StructureData(pymatgen_molecule=mol)

    builder.structure = structure
    builder.parameters = orm.Dict(dict=create_parameters)
    # =========================================================== #

    builder.code = code
    builder.metadata.description = 'Test job submission with the aiida_qp2 plugin to create an EZFIO database'
    builder.metadata.computer = computer

    # Run the calculation & parse results
    print('\nQP create_ezfio execution: STARTED\n')

    result = engine.run(builder)

    print('\nQP create_ezfio execution: FINISHED\n')

    ezfio_RemoteData = result['output_wavefunction']
    ezfio_full_name = ezfio_RemoteData.filename

    print('EZFIO RemoteData name   : ', ezfio_full_name)
    print('EZFIO RemoteData object : ', ezfio_RemoteData)

    return ezfio_RemoteData


def test_run_scf_from_ezfio(code, computer, ezfio_RemoteData_inp):
    """Run JOB #2: SCF calculation on the existing EZFIO database from JOB #1
    """
    builder_scf = code.get_builder()

    ezfio_full_name = ezfio_RemoteData_inp.filename
    ezfio_inp_name = ezfio_full_name.replace('.tar.gz', '')

    # COMPILE THE DICTIONARY OF QP2 PARAMETERS FOR PURE QP RUN

    qp_commands = [f'set_file {ezfio_inp_name}', 'run scf']

    qp_parameters = {'qp_commands': qp_commands}

    # --------------- TO RUN QMC=CHEM INSTEAD --------------- #

    # to run qmcchem after the QP 2
    #qp_commands = [
    #        f'set_file {ezfio_inp_name}',
    #        'run scf',
    #        'run save_for_qmcchem'
    #        ]

    #qmcchem_commands = [
    #    'source ~/qmcchem/qmcchemrc',
    #    f'qmcchem edit --block-time=10 --stop-time=60 {ezfio_inp_name}',
    #    f'qmcchem run {ezfio_inp_name}',
    #    f'qmcchem result -e E_loc {ezfio_inp_name}' +
    #    """ | tail -1 | awk '{printf  $2 "  " $3 "\n"}' """
    #]

    # COMPILE THE DICTIONARY OF QP2 PARAMETERS
    #qp_parameters = {
    #    'ezfio_name': ezfio_inp_name,
    #    'qp_prepend': prepend_commands,
    #    'qp_commands': qp_commands,
    #    'qp_append': qmcchem_commands
    #}

    # --------------- QMC=CHEM SECTION --------------- #

    # conventional QP run
    builder_scf.parameters = orm.Dict(dict=qp_parameters)
    builder_scf.wavefunction = ezfio_RemoteData_inp
    builder_scf.metadata.options.output_wf_basename = ezfio_inp_name

    builder_scf.metadata.options.output_filename = 'qp.out'

    builder_scf.code = code
    builder_scf.metadata.description = 'Test job submission with the aiida_qp2 plugin to run SCF calculations'
    builder_scf.metadata.computer = computer

    print('\nQP run_scf execution: STARTED\n')

    result = engine.run(builder_scf)

    print('\nQP run_scf execution: FINISHED\n')

    ezfio_RemoteData = result['output_wavefunction']
    ezfio_full_name = ezfio_RemoteData.filename

    print('EZFIO RemoteData name   : ', ezfio_full_name)
    print('EZFIO RemoteData object : ', ezfio_RemoteData)

    energy = result['output_energy']

    return (energy, ezfio_RemoteData)


def test_export_trexio(code, computer, wf_inp):
    """Run JOB #3: export TREXIO file from the existing EZFIO database.
    """
    builder_scf = code.get_builder()

    ezfio_full_name = wf_inp.filename
    ezfio_inp_name = ezfio_full_name.replace('.tar.gz', '')

    output_wf_basename = 'hcn.trexio.text'
    # COMPILE THE DICTIONARY OF QP2 PARAMETERS
    qp_commands = [
        f'set_file {ezfio_inp_name}', 'set trexio backend 1',
        f'set trexio trexio_file {output_wf_basename}', 'run export_trexio'
    ]

    qp_parameters = {'qp_commands': qp_commands}

    # conventional QP run
    builder_scf.parameters = orm.Dict(dict=qp_parameters)
    builder_scf.wavefunction = wf_inp
    builder_scf.metadata.options.output_wf_basename = output_wf_basename

    builder_scf.metadata.options.output_filename = 'qp.out'

    builder_scf.code = code
    builder_scf.metadata.description = 'Test job submission with the aiida_qp2 plugin to run SCF calculations'
    builder_scf.metadata.computer = computer

    print('\nQP export_trexio execution: STARTED\n')

    result = engine.run(builder_scf)

    print('\nQP export_trexio execution: FINISHED\n')

    ezfio_RemoteData = result['output_wavefunction']
    ezfio_full_name = ezfio_RemoteData.filename

    print('EZFIO RemoteData name   : ', ezfio_full_name)
    print('EZFIO RemoteData object : ', ezfio_RemoteData)

    return 0


@click.command()
@cmdline.utils.decorators.with_dbenv()
def cli():
    """Run example_trexio_from_xyz.py : execute 3 jobs using QP code.

    Job #1: create an EZFIO database from the existing XYZ (hcn.xyz) file using `qp create_ezfio [arguments]` command;

        Output: EZFIO wavefunction (AiiDA-native SinglefileData object) from the AiiDA database.

    Job #2: perform SCF calculation on the EZFIO database created in the prevous step;

        Output:
        1. SCF energy (AiiDA-native Float object) from the AiiDA database;
        2. EZFIO wavefunction (AiiDA-native SinglefileData object).

    Job #3: export TREXIO wavefunction file using EZFIO from the previous step;

        Output: TREXIO wavefunction (AiiDA-native SinglefileData object).

    Run:  $ verdi run example_trexio_from_xyz.py

    Help: $ ./example_trexio_from_xyz.py --help
    """
    (code, computer) = load_aiida_setup()
    wf1 = test_run_create_ezfio(code, computer)

    energy_scf, wf2 = test_run_scf_from_ezfio(code, computer, wf1)
    print('\nOutput: SCF energy\n', float(energy_scf))

    test_export_trexio(code, computer, wf2)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
