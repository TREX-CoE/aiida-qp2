# -*- coding: utf-8 -*-
"""
Calculations provided by qp2.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""
from aiida.common import CalcInfo, CodeInfo
from aiida.engine import CalcJob
from aiida.orm import Dict, Float, Code, StructureData


class QpCalculation(CalcJob):
    """
    AiiDA calculation plugin wrapping the Quantum Package code.

    """
    # Defaults
    _INPUT_FILE = 'aiida.inp'
    _OUTPUT_FILE = 'aiida.out'
    _INPUT_COORDS_FILE = 'aiida.coords.xyz'

    @classmethod
    def define(cls, spec):
        """Define inputs and outputs of the calculation."""
        # yapf: disable
        super().define(spec)

        # set default values for AiiDA options
        spec.input('structure', valid_type=StructureData, required=False, help='Input structrue')
        spec.input('parameters', valid_type=Dict, required=True, help='Input parameters to generate the input file.')
        # current keys: qp_create_ezfio, qp_commands, qp_prepend, qp_append, ezfio

        spec.input('settings', valid_type=Dict, required=False, help='Additional input parameters.')
        spec.input('code', valid_type=Code, required=False, help='The `Code` to use for this job.')
        #spec.input('ezfio', valid_type=RemoteData, required=False, help='The EZFIO database (without .tar.gz).')


        spec.input('metadata.options.output_filename', valid_type=str, default='aiida-qp2.out')
        spec.inputs['metadata']['options']['resources'].default = {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1,
        }

        spec.input('metadata.options.withmpi', valid_type=bool, default=False)
        spec.inputs['metadata']['options']['parser_name'].default = 'qp2'

        # Output parameters
        spec.output('output_energy', valid_type=Float, required=False, help='the result of the calculation')
        spec.output_node = 'output_energy'

        #spec.output('output_parameters', valid_type=Dict, required=True, help='the result of the calculation')
        #spec.output_node = 'output_parameters'

        #spec.output('qp2_wf_file', valid_type=RemoteData, required=False, help='the wave function file (archive or h5)')
        #spec.output_node = 'qp2_wf_file'

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
        ezfio = parameters['ezfio']
        # extract the first 8 symbols of uuid to be appended to the output ezfio tarball
        uuid_suffix_short = self.uuid[:8]

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
        calcinfo.local_copy_list = [] #[f'{ezfio}.tar.gz']
        calcinfo.retrieve_list = [self.metadata.options.output_filename, f'{ezfio}_{uuid_suffix_short}.tar.gz']

        if 'structure' in self.inputs:
            self._INPUT_COORDS_FILE = f'{ezfio}.xyz'
            #inp_structure = self.inputs.structure.get_ase()
            #ase.io.write(folder.get_abs_path(self._INPUT_COORDS_FILE), inp_structure, format='xyz')
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
        Generate the QP submission file using pymatgen
        In the following, the param_dict.get() method is used, which returns
        `None` if the corresponding key is not specified, resulting in the
        default value defined by the pymatgen library. For example, charge
        and spin_multiplicity are then defined based on the pymatgen molecule
        definition.
        """

        # extract the name of the ezfio database
        ezfio = parameters['ezfio']
        # extract the list of commands to be executed before the Quantum Package
        prepend_commands = parameters['qp_prepend'] if 'qp_prepend' in parameters.keys() else []
        # extract the list of command line options for create_ezfio
        create_commands = parameters['qp_create_ezfio'] if 'qp_create_ezfio' in parameters.keys() else {}
        # extract the list of qp commands to be executed
        todo_commands = parameters['qp_commands'] if 'qp_commands' in parameters.keys() else []
        # extract the list of commands to be executed after the Quantum Package
        append_commands = parameters['qp_append'] if 'qp_append' in parameters.keys() else []

        qp_commands = [f'qp {command}' for command in todo_commands]

        # OPTIONAL build str with command line options for create_ezfio (in case StructureData is provided)
        if not structure is None:
            if len(create_commands) == 0:
                raise Exception(
                    'A set of qp_create_ezfio commands has to be provided upon creation of a new EZFIO database'
                    )

            create_ezfio_command = 'qp create_ezfio'
            for param, value in create_commands.items():
                create_ezfio_command += f' --{param}={value}'

            create_ezfio_command += f' -- {ezfio}.xyz'

        # ALWAYS build header of the execution script, i.e. to execute some bash commands
        input_list = [
            '#!/bin/bash',
            'set -e',
            '\n'.join(prepend_commands),
            '\n'
            ]

        # OPTIONAL build a block of QP commands to be executed consequently (e.g. qp set_file, qp set, qp run)
        if structure is None:
            input_list.append(f'tar -zxf {ezfio}.tar.gz')
            input_list.append('\n'.join(qp_commands))
            input_list.append('\n')
        # OPTIONAL create EZFIO database otherwise (in case StructureData is provided)
        else:
            input_list.append(create_ezfio_command)

        # ALWAYS tar resulting EZFIO folder to be store as a node in the data provenance
        input_list.append(f'tar -zcf {ezfio}_{uuid_suffix_short}.tar.gz {ezfio}\n')
        input_list.append(f'rm -rf -- {ezfio} {ezfio}.tar.gz\n')
        input_list.append('\n'.join(append_commands))
        input_list.append('\n')

        return '\n'.join(input_list)


#EOF
