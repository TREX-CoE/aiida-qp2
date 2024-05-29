# -*- coding: utf-8 -*-
"""
Calculations provided by qp2.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""

# needed in _unpack function
from collections.abc import Sequence

from aiida.common import CalcInfo, CodeInfo
from aiida.engine import CalcJob
from aiida.orm import Dict, Int, Float, Code, Str, StructureData, SinglefileData
from aiida.plugins import DataFactory
from pymatgen.core.periodic_table import Element


class QP2RunCalculation(CalcJob):
    """ AiiDA calculation plugin wrapping the Quantum Package code.
    """

    # Defaults
    _INPUT_FILE = 'aiida.inp'
    _INPUT_COORDS_FILE = 'aiida.xyz'
    _BASIS_FILE = 'aiida-basis-set'
    _PSEUDO_FILE = 'aiida-pseudo'

    @classmethod
    def define(cls, spec):
        """ Define inputs and outputs of the calculation."""
        # yapf: disable
        super().define(spec)

        # Set default values for AiiDA options

        spec.input('parameters',
                   valid_type=Dict,
                   required=True,
                   help='Calculation parameters to be specified in the input file.')

        spec.input('wavefunction',
                   valid_type=SinglefileData,
                   required=False,
                   help='The wavefunction file (EZFIO or TREXIO).')

        spec.input('code',
                   valid_type=Code,
                   required=False,
                   help='The `Code` to use for this job.')

        # Output wavefunction base name
        spec.input('metadata.options.output_wf_basename',
                   valid_type=str,
                   required=True,
                   default='aiida.wf',
                   help='Base name of the output wavefunction file (without .tar.gz or .h5).')

        spec.input('metadata.options.output_filename',
                   valid_type=str,
                   default='aiida-qp2.out')

        spec.input('metadata.options.store_wavefunction',
                   valid_type=bool,
                   default=True)

        spec.inputs['metadata']['options']['parser_name'].default = 'qp2.run'

        spec.input('metadata.options.withmpi', valid_type=bool, default=False)
        spec.inputs['metadata']['options']['resources'].default = {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1,
        }

        # Output parameters
        spec.output('output_energy',
                    valid_type=Float,
                    required=False,
                    help='The result of the calculation')
        spec.output_node = 'output_energy'

        spec.output('output_energy_error',
                    valid_type=Float,
                    required=False,
                    help='The error of the energy calculation')
        spec.output_node = 'output_energy_error'

        spec.output('output_energy_stddev',
                    valid_type=Float,
                    required=False,
                    help='The standard deviation of the energy calculation')
        spec.output_node = 'output_energy_stddev'

        spec.output('output_energy_stddev_error',
                    valid_type=Float,
                    required=False,
                    help='The error of the standard deviation calculation')
        spec.output_node = 'output_energy_stddev_error'

        spec.output('output_number_of_blocks',
                    valid_type=Int,
                    required=False,
                    help='The number of blocks in the calculation')
        spec.output_node = 'output_number_of_blocks'

        spec.output('output_wavefunction', valid_type=SinglefileData, required=False,
                    help='The wave function file (EZFIO or TREXIO)')
        spec.output_node = 'output_wavefunction'


    def prepare_for_submission(self, folder):
        """
        Create input files.

        :param folder: an `aiida.common.folders.Folder` where the plugin should temporarily place all files
            needed by the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """


        with folder.open(self._INPUT_FILE, 'w') as handle:
            self._write_input_file(handle)

        with folder.open('aiida.wf.tar.gz', 'wb') as handle, self.inputs.wavefunction.open(mode='rb') as handle_wf:
            handle.write(handle_wf.read())

        # Prepare a `CodeInfo` to be returned to the engine
        codeinfo = CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdin_name = self._INPUT_FILE
        codeinfo.stdout_name = self.metadata.options.output_filename

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.stdin_name = self._INPUT_FILE
        calcinfo.stdout_name = self.metadata.options.output_filename
        calcinfo.codes_info = [codeinfo]

        calcinfo.local_copy_list = []
        calcinfo.retrieve_list = [self.metadata.options.output_filename,
                                  f'{self.metadata.options.output_wf_basename}.tar.gz']

        return calcinfo

    def _write_input_file(self, handle):
        """Write the input file to the handle"""
        # yapf: disable

        run_type = self.inputs.parameters.get_dict().get('run_type', 'none')
        tbf = self.inputs.parameters.get_dict().get('trexio_bug_fix', False)
        append = self.inputs.parameters.get_dict().get('qp_append', '')

        if run_type == 'none':
            raise ValueError('run_type not specified in parameters')

        code_command = 'qp'
        config_command = 'set'
        run_command = f'qp run {run_type} {append}'
        ezfio = ''

        if run_type == 'qmcchem':
            code_command = 'qmcchem'
            config_command = 'edit'
            run_command = 'qmcchem run aiida.ezfio'
            ezfio = 'aiida.ezfio'

        handle.write('#!/bin/bash\n')
        handle.write('set -e\n')
        handle.write('set -x\n')
        handle.write('tar xzf aiida.wf.tar.gz\n')
        handle.write(f'qp set_file aiida.ezfio\n')

        # Iter over prepend parameters
        if self.inputs.parameters.get_dict().get('qp_prepend', None):
            for value in self.inputs.parameters.get_dict().get('qp_prepend'):
                handle.write(f'{code_command} {config_command} {value} {ezfio}\n')

        handle.write(run_command + '\n')

        if tbf:
            handle.write(f'sed -i "1s|^|$(pwd)/|" aiida.ezfio/trexio/trexio_file\n')

        handle.write(f'echo "#*#* ERROR CODE: $? #*#*"\n')
        handle.write(f'tar czf {self.metadata.options.output_wf_basename}.tar.gz *.ezfio\n')
#EOF
