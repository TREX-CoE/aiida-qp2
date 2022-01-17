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
from aiida.plugins import DataFactory
from pymatgen.core.periodic_table import Element


class QP2Calculation(CalcJob):
    """ AiiDA calculation plugin wrapping the Quantum Package code.
    """

    # Defaults
    _INPUT_FILE = 'aiida.inp'
    _INPUT_COORDS_FILE = 'aiida.coords.xyz'
    _BASIS_FILE = 'aiida-basis-set'
    _PSEUDO_FILE = 'aiida-pseudo'
    QP_INIT = False

    @classmethod
    def define(cls, spec):
        """ Define inputs and outputs of the calculation."""
        # yapf: disable
        super().define(spec)

        # Set default values for AiiDA options

        # Dictionary of parameters, supported: qp_create_ezfio, qp_commands, qp_prepend, qp_append
        spec.input('parameters', valid_type=Dict, required=True,
                help='Input parameters to generate the input file.')

        spec.input('structure', valid_type=StructureData, required=False, help='Input structrue')

        spec.input('wavefunction', valid_type=SinglefileData, required=False, help='The wavefunction file (EZFIO or TREXIO).')

        spec.input('settings', valid_type=Dict, required=False, help='Additional input parameters.')

        spec.input('code', valid_type=Code, required=False, help='The `Code` to use for this job.')

        # Output wavefunction base name
        spec.input('metadata.options.output_wf_basename', valid_type=str, required=True, default='aiida.wf',
                help='Base name of the output wavefunction file (without .tar.gz or .h5).')

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

        spec.inputs['metadata']['options']['parser_name'].default = 'qp2'

        spec.input('metadata.options.withmpi', valid_type=bool, default=False)
        spec.inputs['metadata']['options']['resources'].default = {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1,
        }

        # Output parameters
        spec.output('output_energy', valid_type=Float, required=False, help='The result of the calculation')
        spec.output_node = 'output_energy'

        spec.output('output_wavefunction', valid_type=SinglefileData, required=True,
                    help='The wave function file (EZFIO or TREXIO)')
        spec.output_node = 'output_wavefunction'

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

        # check the input parameters for consistency
        if 'xyz' in parameters.keys() and 'wavefunction' in self.inputs.keys():
            raise Exception('JOB SETUP ERROR: `xyz` and `wavefunction` parameters cannot be specified simultaneously.')
        if not 'xyz' in parameters.keys() and not 'wavefunction' in self.inputs.keys():
            raise Exception('JOB SETUP ERROR: either `xyz` or `wavefunction` parameter has to be specified.')
        # if `xyz` parameter is provided then this job corresponds to creation of the wavefunction file
        if 'xyz' in parameters.keys() and not 'wavefunction' in self.inputs.keys():
            QP_INIT = True
        else:
            QP_INIT = False

        # extract the name of the wavefunction file
        wf_filename = self.inputs.wavefunction.filename if not QP_INIT else None
        input_wf_basename = wf_filename.replace('.tar.gz','') if wf_filename else None
        # extract the base name (without .tar.gz suffix)
        output_wf_basename = self.metadata.options.output_wf_basename
        # safety check
        if '.tar.gz' in output_wf_basename:
            output_wf_basename.replace('.tar.gz', '')
        # extract the name of the XYZ file for create_ezfio job
        xyz_name = parameters['xyz'] if QP_INIT else None

        # Prepare a `CodeInfo` to be returned to the engine
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
        # build the local_copy_list to copy the input wavefunction SinglefileData to the work directory
        calcinfo.local_copy_list = []
        if 'wavefunction' in self.inputs.keys():
            calcinfo.local_copy_list = [
                    (self.inputs.wavefunction.uuid, wf_filename, wf_filename)
                    ] if not QP_INIT else []
        else:
            calcinfo.local_copy_list = []

        # special case to use basissets and pseudos from aiida-gaussian-datatypes plugin
        if 'basissets' in self.inputs and QP_INIT:
            #validate_basissets(inp, self.inputs.basissets, self.inputs.structure if 'structure' in self.inputs else None)
            with open(folder.get_abs_path(self._BASIS_FILE), 'w', encoding='utf-8') as fhandle:
                for elem in self.inputs.basissets.keys():
                    elem_name = Element(elem).long_name
                    fhandle.write(f'{elem_name.upper()}\n')
                    self.inputs.basissets[elem].to_qp(fhandle)
                    fhandle.write('\n')

        if 'pseudos' in self.inputs and QP_INIT:
            #validate_pseudos(inp, self.inputs.pseudos, self.inputs.structure if 'structure' in self.inputs else None)
            with open(folder.get_abs_path(self._PSEUDO), 'w', encoding='utf-8') as fhandle:
                for elem in self.inputs.pseudos.keys():
                    elem_name = Element(elem).long_name
                    fhandle.write(f'{elem_name.upper()}\n')
                    self.inputs.pseudos[elem].to_gamess(fhandle)
                    fhandle.write('\n')


        # retrieve_list will copy the files from the remote machine to the local one (where AiiDA runs)
        calcinfo.retrieve_list = [self.metadata.options.output_filename]
        calcinfo.retrieve_list.append(f'{output_wf_basename}.tar.gz')

        inp_structure = None
        if 'structure' in self.inputs:
            self._INPUT_COORDS_FILE = xyz_name
            # write StructureData in the ASE (Atoms) format
            #inp_structure = self.inputs.structure.get_ase()
            #ase.io.write(folder.get_abs_path(self._INPUT_COORDS_FILE), inp_structure, format='xyz')
            # write StructureData in the pymatgen (Molecule) format
            inp_structure = self.inputs.structure.get_pymatgen_molecule()
            inp_structure.to(filename=folder.get_abs_path(self._INPUT_COORDS_FILE), fmt='xyz')

        input_string = QP2Calculation._render_input_string_from_params(
            parameters, input_wf_basename, output_wf_basename
            )

        with open(folder.get_abs_path(self._INPUT_FILE), 'w', encoding='utf-8') as inp_file:
            inp_file.write(input_string)

        return calcinfo


    @classmethod
    def _render_input_string_from_params(cls, parameters, input_wf_basename, output_wf_basename):
        """ Generate the QP submission file based on the contents of the input `parameters` dictionary.
        """

        if 'qp_create_ezfio' in parameters.keys() and 'xyz' in parameters.keys():
            QP_INIT = True
            # Extract the list of command line options for create_ezfio
            create_commands = parameters['qp_create_ezfio']
            # Extract the name of XYZ file for create_ezfio
            xyz_name = parameters['xyz']
        else:
            QP_INIT = False

        # Extract the list of commands to be executed before the Quantum Package
        prepend_commands = parameters['qp_prepend'] if 'qp_prepend' in parameters.keys() else []
        # Extract the list of QP-specific commands to be executed
        todo_commands = parameters['qp_commands'] if 'qp_commands' in parameters.keys() else []
        # Extract the list of commands to be executed after the Quantum Package
        append_commands = parameters['qp_append'] if 'qp_append' in parameters.keys() else []

        # Prepend `qp` to the commands from the `parameters['qp_commands']` list
        qp_commands = [f'qp {command}' for command in todo_commands]

        # OPTIONAL build str with command line options for `qp create_ezfio` (in case StructureData is provided)
        if QP_INIT:
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

        # preprocess the wavefunction file
        if QP_INIT:
            # create the wavefunction file
            input_list.append(create_ezfio_command)
        else:
            # extract the provided wavefunction file
            input_list.append(f'tar -zxf {input_wf_basename}.tar.gz')
            input_list.append(f'rm -- {input_wf_basename}.tar.gz')


        # build a block of QP commands to be executed consequently (e.g. qp set_file, qp set, qp run)
        if not QP_INIT:
            input_list.append('\n'.join(qp_commands))

        # run append commands (e.g. additional steps related to qmcchem before archiving
        input_list.append('\n'.join(append_commands))

        # ALWAYS tar the final wavefunction file to be stored in the data provenance
        input_list.append(f'tar -zcf {output_wf_basename}.tar.gz {output_wf_basename}')
        input_list.append(f'rm -rf -- {output_wf_basename}/')
        # 2 directories can be produced when exporting to TREXIO, so clean both
        if (not input_wf_basename is None) and (not output_wf_basename in input_wf_basename):
            input_list.append(f'rm -rf -- {input_wf_basename}/')

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
