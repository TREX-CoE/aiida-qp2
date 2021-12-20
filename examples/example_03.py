#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Load the basis set from the database.

Usage:
  (1) ./example_03.py
  (2) verdi run example_03.py
"""
from os import path
from pymatgen.core import Molecule
from pymatgen.core.periodic_table import Element
import click
from aiida import orm, cmdline  #engine
from aiida.common.exceptions import NotExistent
from aiida.plugins import DataFactory

INPUT_DIR = path.join(path.dirname(path.realpath(__file__)), 'input_files')
XYZ_FILE = 'hcn.xyz'


def load_aiida_setup():
    """Load localhost computer and qp2@localhost from the AiiDA database.

    """
    #try:
    #    aiida_profile = load_profile(profile)
    #except:
    #    raise Exception('Create the profile for this example') from NotExistent

    # Load the localhost computer
    try:
        computer = orm.load_computer('localhost')
    except:
        raise Exception(
            'Create the localhost computer for this example') from NotExistent

    # Create or load the qp2 code
    try:
        code = orm.load_code('qp2@localhost')
    except NotExistent:
        # Setting up code via python API (or use "verdi code setup")
        code = orm.Code(label='qp2',
                        remote_computer_exec=[computer, '~/qp2/bin/qpsh'],
                        input_plugin_name='qp2')

    return (code, computer)


def test_run_create_ezfio():  #(code, computer):
    """Run JOB #1: create an EZFIO database from XYZ file

   Runs on the localhost computer using qp2@localhost code
   """

    # create a StructureData node for the calculation
    mol = Molecule.from_file(path.join(INPUT_DIR, XYZ_FILE))
    #structure = orm.StructureData(pymatgen_molecule=mol)
    # uncomment to see how Molecule->StructureData conversion modifies the atomic positions
    #mol2 = structure.get_pymatgen_molecule()
    #print(mol2)

    # Basis set section: build a dictionary with
    #   key   - full name of the atom
    #   value - instance of the BasisSet data item corresponding to the "basis_name" basis set
    BasisSet = DataFactory('gaussian.basisset')
    basis_name = 'aug-cc-pVDZ'
    # symbol_set is an attribute of Molecule class from pymatget, it contains a tuple of unique atoms
    # Element class is part of the pymatgen.core.periodic_table module
    basis_dict = {
        Element(atom).long_name: BasisSet.get(element=atom, name=basis_name)
        for atom in mol.symbol_set
    }

    # create single file with basis sets for all unique atoms involved in the calculation
    # this can be read and processed by the Quantum Package (at the moment - write in GAMESS format)
    basis_file = 'AiiDA-aug-cc-pVDZ'
    with open(basis_file, 'w') as f:
        for unique_atom in basis_dict.keys():
            f.write(f'{unique_atom.upper()}\n')
            basis_dict[unique_atom].to_qp(f)
            f.write('\n')

    return 0


#   # Set up inputs
#   builder = code.get_builder()
#
#   # COMPILE THE DICTIONARY OF QP2 PARAMETERS
#  ezfio_name = 'hcn.ezfio'
#  create_parameters = {
#      'qp_create_ezfio': {
#          'basis': basis_file,
#          'charge': '0',
#          'output': ezfio_name,
#      },
#      'xyz': 'hcn.xyz',
#      'ezfio_name': ezfio_name
#  }
#
#  builder.metadata.options.output_filename = 'qp.out'
#  builder.metadata.options.output_ezfio_basename = ezfio_name
#  builder.metadata.options.computer = 'localhost'
#
#  # ============== CREATE_EZFIO SPECIFIC PARAMETERS =========== #

#  # QP run to create EZFIO database from the XYZ file
#  builder.structure = structure
#  builder.parameters = orm.Dict(dict=create_parameters)

#  # =========================================================== #
#
#  builder.code = code
#  builder.metadata.description = 'Test job submission with the aiida_qp2 plugin to create an EZFIO database'
#  builder.metadata.computer = computer
#
#  # Run the calculation & parse results
#  print('\nQP2 create_ezfio execution: STARTED\n')
#
#  result = engine.run(builder)
#
#  print('\nQP2 create_ezfio execution: FINISHED\n')
#
#  ezfio_RemoteData = result['output_ezfio']
#  path_to_ezfio = ezfio_RemoteData.get_remote_path()
#  #computer_with_ezfio = ezfio_RemoteData.get_computer_name()
#
#  ezfio_full_name = path_to_ezfio.split('/')[-1]
#  #ezfio_base_name = ezfio_full_name.split('.tar.gz')[0]
#
#  print('EZFIO RemoteData name   : ', ezfio_full_name)
#  print('EZFIO RemoteData object : ', ezfio_RemoteData)
#  print('EZFIO RemoteData path   : ', path_to_ezfio)
#
#  return ezfio_RemoteData

#def test_run_scf_from_ezfio(code, computer, ezfio_RemoteData_inp):
#   """Run JOB #2: SCF calculation on the existing EZFIO database from JOB #1
#
#   Runs on the localhost computer using qp2@localhost code
#   """
#   builder_scf = code.get_builder()
#   #ezfio_name = 'hcn.ezfio'
#
#   prepend_commands = []
#   # proper use of calcinfo.remote_copy_list allows to avoid manually copying
#   # the ezfio files on remote machines from the previous job directory to the current one
#   #prepend_commands = [f'cp {path_to_ezfio} .']
#
#   path_to_ezfio = ezfio_RemoteData_inp.get_remote_path()
#   ezfio_full_name = path_to_ezfio.split('/')[-1]
#   ezfio_inp_name = ezfio_full_name.split('.tar.gz')[0]
#
#   qp2_commands = [f'set_file {ezfio_inp_name}', 'run scf']
#
#   # COMPILE THE DICTIONARY OF QP2 PARAMETERS
#   qp2_parameters = {
#       'ezfio_name': ezfio_inp_name,
#       'qp_prepend': prepend_commands,
#       'qp_commands': qp2_commands
#   }
#
#   # conventional QP run
#   builder_scf.parameters = orm.Dict(dict=qp2_parameters)
#   builder_scf.ezfio = ezfio_RemoteData_inp
#
#   builder_scf.metadata.options.output_filename = 'qp.out'
#   builder_scf.metadata.options.output_ezfio_basename = ezfio_inp_name
#   builder_scf.metadata.options.computer = 'localhost'
#
#   builder_scf.code = code
#   builder_scf.metadata.description = 'Test job submission with the aiida_qp2 plugin to run SCF calculations'
#   builder_scf.metadata.computer = computer
#
#   print('\nQP2 run_scf execution: STARTED\n')
#
#   result = engine.run(builder_scf)
#
#   print('\nQP2 run_scf execution: FINISHED\n')
#
#   ezfio_RemoteData = result['output_ezfio']
#   path_to_ezfio = ezfio_RemoteData.get_remote_path()
#
#   ezfio_full_name = path_to_ezfio.split('/')[-1]
#   #ezfio_base_name = ezfio_full_name.split('.tar.gz')[0]
#
#   print('EZFIO RemoteData name   : ', ezfio_full_name)
#   print('EZFIO RemoteData object : ', ezfio_RemoteData)
#   print('EZFIO RemoteData path   : ', path_to_ezfio)
#
#   energy = result['output_energy']
#
#   return energy
#


@click.command()
@cmdline.utils.decorators.with_dbenv()
def cli():
    """Run example_02: execute 2 jobs using QP2 code.

    Job #1: create an EZFIO database from the existing XYZ (hcn.xyz) file using `qp create_ezfio [arguments]` command;

        Output: ezfio (AiiDA-native RemoteData object) from the AiiDA database.

    Job #2: perform SCF calculation on the EZFIO database created in the prevous step;

        Output: SCF energy (AiiDA-native Float object) from the AiiDA database

    Example usage: $ ./example_02.py

    Alternative:   $ verdi run example_02.py

    Help: $ ./example_02.py --help
    """
    #(code, computer) = load_aiida_setup()
    #ezfio_RemoteData = test_run_create_ezfio(code, computer)
    #energy_scf = test_run_scf_from_ezfio(code, computer, ezfio_RemoteData)

    test_run_create_ezfio()


#    print('\nOutput: SCF energy\n', float(energy_scf))

if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
