# -*- coding: utf-8 -*-
"""
Calculation class for the Quantum Package code.

CalcJob creates new ezfio files from inputs
and stores them in a tarball.

"""

from aiida.common import CalcInfo, CodeInfo
from aiida.engine import CalcJob
from aiida.orm import Dict, Float, Code, Str, StructureData, SinglefileData
from aiida.plugins import DataFactory


class QP2CreateCalculation(CalcJob):
    """ AiiDA calculation plugin for Quantum Package.
        Creates new ezfio files from inputs and stores them in a tarball.
    """

    # Defaults
    _INPUT_FILE = 'aiida.inp'
    _INPUT_COORDS_FILE = 'aiida.xyz'

    @classmethod
    def define(cls, spec):
        """ Define inputs and outputs of the calculation."""
        # yapf: disable
        super().define(spec)

        # Set default values for AiiDA options
        spec.input('parameters',
                   valid_type=Dict,
                   required=True,
                   help='Input parameters to generate the input file.')

        spec.input('code',
                   valid_type=Code,
                   required=True,
                   help='The `Code` to use for this job.')

        spec.input('structure',
                   valid_type=StructureData,
                   required=True,
                   help='Input structure to be used in the calculation.')

        spec.input('basis_set',
                   valid_type=Str,
                   required=False,
                   default=lambda: Str('cc-pvdz'),
                   help='The basis set to use for this calculation.')

        spec.input('pseudo_potential',
                   valid_type=Str,
                   required=False,
                   default=lambda: Str(''),
                   help='The pseudo potential to use for this calculation.')


        # Metadata
        spec.input('metadata.options.output_wf_basename',
                   valid_type=str,
                   required=True,
                   default='aiida.wf',
                   help='Base name of the output wavefunction file (without .tar.gz or .h5).')

        spec.input('metadata.options.output_filename',
                   valid_type=str,
                   default='aiida-qp2.out')

        # Resources (MPI might be disabled in the future)
        spec.input('metadata.options.withmpi',
                   valid_type=bool,
                   default=False)
        spec.inputs['metadata']['options']['resources'].default = {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1,
        }

        # Parser
        spec.inputs['metadata']['options']['parser_name'].default = 'qp2.create'

        # Output parameters
        spec.output('wavefunction',
                    valid_type=SinglefileData,
                    required=True,
                    help='The result of the calculation')

    def prepare_for_submission(self, folder):
        """
        Create input files.

        :param folder: an `aiida.common.folders.Folder`
                       where the plugin should temporarily
                       place all files needed by the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

        basis_set = self.inputs.basis_set.value
        # TODO: Check if basis set is valid

        with folder.open(self._INPUT_FILE, 'w') as handle:
            handle.write(f'qp create_ezfio -b {basis_set} {self._INPUT_COORDS_FILE}\n')
            handle.write(f'tar czf {self.metadata.options.output_wf_basename}.tar.gz *.ezfio\n')

        with folder.open(self._INPUT_COORDS_FILE, 'w') as handle:
            structure = self.inputs.structure.get_ase()
            self.metadata.options.input_formula = structure.get_chemical_formula()
            structure.write(handle, format='xyz')

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
        calcinfo.retrieve_list = [self._INPUT_COORDS_FILE,
                                  self.metadata.options.output_filename,
                                  f'{self.metadata.options.output_wf_basename}.tar.gz']

        return calcinfo
