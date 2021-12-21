# -*- coding: utf-8 -*-
"""
Calculations provided by qp2.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""

# needed in _unpack function
from collections.abc import Sequence

from aiida.common import CalcInfo, CodeInfo
from aiida.engine import CalcJob
from aiida.orm import Dict, Float, Code, StructureData, RemoteData
from aiida.plugins import DataFactory
from pymatgen.core.periodic_table import Element


class QpCalculation(CalcJob):
    """
    AiiDA calculation plugin wrapping the Quantum Package code.

    """
    # Defaults
    _INPUT_FILE = 'aiida.inp'
    _INPUT_COORDS_FILE = 'aiida.coords.xyz'
    _BASIS_FILE = 'aiida-basis-set'
    _PSEUDO_FILE = 'aiida-pseudo'

    @classmethod
    def define(cls, spec):
        """Define inputs and outputs of the calculation."""
        # yapf: disable
        super().define(spec)

        # Set default values for AiiDA options
        spec.input('parameters', valid_type=Dict, required=True, help='Input parameters to generate the input file.')
        # current keys: qp_create_ezfio, qp_commands, qp_prepend, qp_append, ezfio_name
        spec.input('structure', valid_type=StructureData, required=False, help='Input structrue')
        spec.input('ezfio', valid_type=RemoteData, required=False, help='The EZFIO database (without .tar.gz).')
        spec.input('settings', valid_type=Dict, required=False, help='Additional input parameters.')
        spec.input('code', valid_type=Code, required=False, help='The `Code` to use for this job.')

        spec.input_namespace(
            'basissets',
            dynamic=True,
            required=False,
            validator=validate_basissets_namespace,
            help=('A dictionary of basissets to be used in the calculations: key is the atomic symbol,'
                  ' value is either a single basisset.'))

        spec.input_namespace(
            'pseudos',
            dynamic=True,
            required=False,
            validator=validate_pseudos_namespace,
            help=('A dictionary of pseudopotentials to be used in the calculations: key is the atomic symbol,'
                  ' value is a single pseudopotential.'))

        spec.input('metadata.options.output_filename', valid_type=str, default='aiida-qp2.out')
        # `output_ezfio_basename` and `computer` options required to store the output EZFIO tar.gz file as RemoteData node
        spec.input('metadata.options.output_ezfio_basename', valid_type=str, required=True, default='aiida.ezfio')
        spec.input('metadata.options.computer', valid_type=str, required=True, default='localhost')

        spec.input('metadata.options.withmpi', valid_type=bool, default=False)
        spec.inputs['metadata']['options']['resources'].default = {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1,
        }
        spec.inputs['metadata']['options']['parser_name'].default = 'qp2'

        # Output parameters
        spec.output('output_energy', valid_type=Float, required=False, help='The result of the calculation')
        spec.output_node = 'output_energy'
        #spec.output('output_parameters', valid_type=Dict, required=True, help='The results of the calculation')
        #spec.output_node = 'output_parameters'
        spec.output('output_ezfio', valid_type=RemoteData, required=True, help='The wave function file (EZFIO tar.gz)')
        spec.output_node = 'output_ezfio'

        spec.exit_code(100, 'ERROR_NO_RETRIEVED_FOLDER', message='The retrieved folder data node could not be accessed.')
        spec.exit_code(300, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')
        spec.exit_code(400, 'ERROR_MISSING_ENERGY', message='Energy value is not present in the output file.')


    def prepare_for_submission(self, folder):
        """
        Create input files.

        :param folder: an `aiida.common.folders.Folder` where the plugin should temporarily place all files
            needed by the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

        settings = self.inputs.settings.get_dict() if 'settings' in self.inputs else {}
        parameters = self.inputs.parameters.get_dict()
        # extract the name of the ezfio database
        ezfio_name = parameters['ezfio_name'] if 'ezfio_name' in parameters.keys() else None
        # extract the first 8 symbols of uuid to be appended to the output ezfio tarball
        uuid_suffix_short = self.uuid[:8]
        # extract the name of the XYZ file for create_ezfio
        xyz_name = parameters['xyz'] if 'xyz' in parameters.keys() else None

        codeinfo = CodeInfo()
        codeinfo.cmdline_params = settings.pop('cmdline', [])
        codeinfo.join_files = True
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdin_name = self._INPUT_FILE
        codeinfo.stdout_name = self.metadata.options.output_filename
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.cmdline_params = codeinfo.cmdline_params
        calcinfo.stdin_name = self._INPUT_FILE
        calcinfo.stdout_name = self.metadata.options.output_filename
        calcinfo.codes_info = [codeinfo]
        calcinfo.local_copy_list = []
        # The remote copy list is useful to avoid unnecessary file transfers between the machine where the engine
        # runs and where the calculation jobs are executed. For example, a calculation job completed on a remote cluster
        # and now you want to launch a second one, that requires some of the output files of the first run as its inputs.
        # TODO current procedure relies on copying the EZFIO tar.gz to the local repository where AiiDA runs # pylint: disable=fixme
        # TODO perhaps this can be avoided by providing a path on the remote machine instead of the local one # pylint: disable=fixme
        if 'ezfio' in self.inputs.keys():
            calcinfo.remote_copy_list = [
                (self.inputs.metadata.computer.uuid, self.inputs.ezfio.get_remote_path(), './')
                ] if not 'xyz' in parameters.keys() else []
        else:
            calcinfo.remote_copy_list = []


        if 'basissets' in self.inputs:
            #validate_basissets(inp, self.inputs.basissets, self.inputs.structure if 'structure' in self.inputs else None)
            with open(folder.get_abs_path(self._BASIS_FILE), 'w') as fhandle:
                for elem in self.inputs.basissets.keys():
                    elem_name = Element(elem).long_name
                    fhandle.write(f'{elem_name.upper()}\n')
                    self.inputs.basissets[elem].to_qp(fhandle)
                    fhandle.write('\n')


        if 'pseudos' in self.inputs:
            #validate_pseudos(inp, self.inputs.pseudos, self.inputs.structure if 'structure' in self.inputs else None)
            with open(folder.get_abs_path(self._PSEUDO), 'w') as fhandle:
                for elem in self.inputs.pseudos.keys():
                    elem_name = Element(elem).long_name
                    fhandle.write(f'{elem_name.upper()}\n')
                    self.inputs.pseudos[elem].to_gamess(fhandle)
                    fhandle.write('\n')


        # retrieve_list will copy the files from the remote machine to the local one (where AiiDA runs)
        # This is not desirable for big files like EZFIO tar.gz or HDF5 file
        calcinfo.retrieve_list = [self.metadata.options.output_filename]
        # TODO the line below copies the produced and tar-ed EZFIO from # pylint: disable=fixme
        # TODO test-aiida/work/{AIIDA_IDs} to ~/.aiida/repository/posev-ubuntu/repository/node/... # pylint: disable=fixme
        # TODO this can probably be avoided by allowing AiiDA to operate entirely on remote computer # pylint: disable=fixme
        # TODO instead of copying to the local machine (where AiiDA runs) # pylint: disable=fixme
        calcinfo.retrieve_list.append(f'./{ezfio_name}_{uuid_suffix_short}.tar.gz')

        inp_structure = None
        if 'structure' in self.inputs:
            self._INPUT_COORDS_FILE = xyz_name
            # write StructureData in the ASE (Atoms) format
            #inp_structure = self.inputs.structure.get_ase()
            #ase.io.write(folder.get_abs_path(self._INPUT_COORDS_FILE), inp_structure, format='xyz')
            # write StructureData in the pymatgen (Molecule) format
            inp_structure = self.inputs.structure.get_pymatgen_molecule()
            inp_structure.to(filename=folder.get_abs_path(self._INPUT_COORDS_FILE), fmt='xyz')


        input_string = QpCalculation._render_input_string_from_params(
            parameters, inp_structure, uuid_suffix_short
            )


        with open(folder.get_abs_path(self._INPUT_FILE), 'w') as inp_file:
            inp_file.write(input_string)

        return calcinfo


    @classmethod
    def _render_input_string_from_params(cls, parameters, structure, uuid_suffix_short):
        """
        Generate the QP submission file based on the contents of the input `parameters` dictionary.
        """

        # Extract the name of the ezfio database
        ezfio_name = parameters['ezfio_name'] if 'ezfio_name' in parameters.keys() else None
        # Extract the list of commands to be executed before the Quantum Package
        prepend_commands = parameters['qp_prepend'] if 'qp_prepend' in parameters.keys() else []
        # Extract the list of command line options for create_ezfio
        create_commands = parameters['qp_create_ezfio'] if 'qp_create_ezfio' in parameters.keys() else {}
        # Extract the name of XYZ file for create_ezfio
        xyz_name = parameters['xyz'] if 'xyz' in parameters.keys() else None
        # Extract the list of qp commands to be executed
        todo_commands = parameters['qp_commands'] if 'qp_commands' in parameters.keys() else []
        # Extract the list of commands to be executed after the Quantum Package
        append_commands = parameters['qp_append'] if 'qp_append' in parameters.keys() else []

        # Prepend `qp` to the commands from the `parameters['qp_commands']` list
        qp_commands = [f'qp {command}' for command in todo_commands]

        # OPTIONAL build str with command line options for `qp create_ezfio` (in case StructureData is provided)
        if not structure is None:
            if len(create_commands) == 0:
                raise Exception('A set of qp_create_ezfio commands required upon creation of a new EZFIO database.')

            create_ezfio_command = 'qp create_ezfio'
            for param, value in create_commands.items():
                create_ezfio_command += f' --{param}={value}'

            if not xyz_name is None:
                create_ezfio_command += f' -- {xyz_name}'
            else:
                raise Exception('Missing "xyz" key in the parameters dict.')


        # ALWAYS build header of the execution script with prepend_commands, e.g. bash
        input_list = [
            '#!/bin/bash',
            'set -e',
            '\n'.join(prepend_commands)
            ]

        # OPTIONAL build a block of QP commands to be executed consequently (e.g. qp set_file, qp set, qp run)
        if structure is None:
            input_list.append(f'tar -zxf {ezfio_name}.tar.gz')
            input_list.append('\n'.join(qp_commands))
        # OPTIONAL create EZFIO database otherwise (in case StructureData is provided)
        else:
            input_list.append(create_ezfio_command)

        # ALWAYS tar resulting EZFIO folder to be stored as an output node in the data provenance
        input_list.append(f'mv {ezfio_name} {ezfio_name}_{uuid_suffix_short}')
        input_list.append(f'tar -zcf {ezfio_name}_{uuid_suffix_short}.tar.gz {ezfio_name}_{uuid_suffix_short}')
        input_list.append(f'rm -rf -- {ezfio_name}_{uuid_suffix_short} {ezfio_name}.tar.gz')
        input_list.append('\n'.join(append_commands))

        return '\n'.join(input_list)


# the code below is copied from the utils/data_helpers.py of the aiida-cp2k plugin
# https://github.com/aiidateam/aiida-cp2k/blob/develop/aiida_cp2k/utils/datatype_helpers.py

def validate_basissets_namespace(basissets, _):
    """A input_namespace validator to ensure passed down basis sets have the correct type."""
    return _validate_gdt_namespace(basissets, DataFactory('gaussian.basisset'), 'basis set')


def validate_pseudos_namespace(pseudos, _):
    """A input_namespace validator to ensure passed down pseudopentials have the correct type."""
    return _validate_gdt_namespace(pseudos, DataFactory('gaussian.pseudo'), 'pseudo')

def _validate_gdt_namespace(entries, gdt_cls, attr):
    """Common namespace validator for both basissets and pseudos"""

    identifiers = []

    for kind, gdt_instance in _unpack(entries):
        if not isinstance(gdt_instance, gdt_cls):
            return f"invalid {attr} for '{kind}' specified"

        identifier = (gdt_instance.element, gdt_instance.name)

        if identifier in identifiers:
            # note: this should be possible for basissets with different versions
            #       but at this point we should require some format for the key to match it
            return f'{attr} for kind {gdt_instance.element} ({gdt_instance.name}) specified multiple times'

        identifiers += [identifier]

    return None


def _unpack(adict):
    """Unpack any lists as values into single elements for the key"""

    for key, value in adict.items():
        if isinstance(value, Sequence):
            for item in value:
                yield (key, item)
        else:
            yield (key, value)

#EOF
