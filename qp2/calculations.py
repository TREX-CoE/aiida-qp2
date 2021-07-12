# -*- coding: utf-8 -*-
"""
Calculations provided by qp2.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""
from aiida.common import CalcInfo, CodeInfo
from aiida.engine import CalcJob
from aiida.orm import Dict, Float, Code


class QpCalculation(CalcJob):
    """
    AiiDA calculation plugin wrapping the Quantum Package code.

    """

    # Defaults
    _INPUT_FILE = 'aiida.inp'
    _OUTPUT_FILE = 'aiida.out'
    #_INPUT_COORDS_FILE = 'aiida.coords.xyz'

    @classmethod
    def define(cls, spec):
        """Define inputs and outputs of the calculation."""
        # yapf: disable
        super().define(spec)

        # set default values for AiiDA options
        spec.input('parameters', valid_type=Dict, required=True, help='Input parameters to generate the input file.')
        # current keys: qp_commands, qp_prepend, qp_append, ezfio

        #spec.input('ezfio', valid_type=str, required=True, help='The name of the input EZFIO database (without .tar.gz).')
        spec.input('settings', valid_type=Dict, required=False, help='Additional input parameters.')
        spec.input('code', valid_type=Code, help='The `Code` to use for this job.')
        #spec.input('structure', valid_type=StructureData, required=True, help='Input structure.')


        spec.input('metadata.options.output_filename', valid_type=str, default='aiida-qp2.out')

        spec.inputs['metadata']['options']['resources'].default = {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1,
        }

        spec.input('metadata.options.withmpi', valid_type=bool, default=False)
        spec.inputs['metadata']['options']['parser_name'].default = 'qp2'

        # Output parameters
        spec.output('output_energy', valid_type=Float, required=True, help='the result of the calculation')
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
        # extract the list of qp commands to be executed
        qp_commands = parameters['qp_commands']
        # extract the list of commands to be executed before the Quantum Package
        prepend_commands = parameters['qp_prepend'] if 'qp_prepend' in parameters.keys() else []
        # extract the list of commands to be executed after the Quantum Package
        append_commands = parameters['qp_append'] if 'qp_append' in parameters.keys() else []
        # extract the first 8 symbols of uuid to be appended to the output ezfio tarball
        uuid_suffix_short = self.uuid[:8]

        codeinfo = CodeInfo()
        codeinfo.cmdline_params = settings.pop('cmdline', []) + [self._INPUT_FILE]
        codeinfo.join_files = True
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdout_name = self.metadata.options.output_filename
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.cmdline_params = codeinfo.cmdline_params
        calcinfo.codes_info = [codeinfo]
        calcinfo.local_copy_list = [] #[f'{ezfio}.tar.gz']
        calcinfo.retrieve_list = [self.metadata.options.output_filename, f'{ezfio}_{uuid_suffix_short}.tar.gz']

        input_block = []

        input_block = [f'qp {command}' for command in qp_commands]

        with open(folder.get_abs_path(self._INPUT_FILE), 'w') as fobj:
            #    fobj.write('source ~/qp2/quantum_package.rc\n')
            fobj.write('#!/bin/bash\n\n')
            fobj.write('set -e\n')
            fobj.write('set -x\n')
            fobj.write('\n'.join(prepend_commands))
            fobj.write('\n')
            fobj.write(f'tar -zxf {ezfio}.tar.gz\n')
            fobj.write('\n'.join(input_block))
            fobj.write('\n')
            fobj.write(f'tar -zcf {ezfio}_{uuid_suffix_short}.tar.gz {ezfio}\n')
            fobj.write(f'rm -rf -- {ezfio} {ezfio}.tar.gz\n')
            fobj.write('\n'.join(append_commands))
            fobj.write('\n')

        return calcinfo
