# -*- coding: utf-8 -*-
"""
Parsers provided by qp2.

"""

from os.path import join as path_join

from aiida.engine import ExitCode
from aiida.parsers.parser import Parser
from aiida.plugins import CalculationFactory
from aiida.common import exceptions
from aiida.orm import Float, SinglefileData
import json

QP2RunCalculation = CalculationFactory('qp2.run')

_DICTIONARES = {
    'scf': 'hartree_fock',
    'ccsd': 'ccsd',
}


class QP2QmcchemRunParser(Parser):
    """
    Parser class for parsing output of calculation.
    """
    def __init__(self, node):
        """
        Initialize Parser instance

        Checks that the ProcessNode being passed was produced by a QP2RunCalculation.

        :param node: ProcessNode of calculation
        :param type node: :class:`aiida.orm.ProcessNode`
        """
        super().__init__(node)
        if not issubclass(node.process_class, QP2RunCalculation):
            raise exceptions.ParsingError('Can only parse QP2RunCalculation')

    def parse(self, **kwargs):  # pylint: disable=too-many-locals
        """
        Parse outputs, store results in database.

        :returns: an exit code, if parsing fails (or nothing if parsing succeeds)
        """
        output_filename = self.node.get_option('output_filename')
        output_wf_basename = self.node.get_option('output_wf_basename')
        output_wf_filename = output_wf_basename + '.tar.gz'
        store_wavefunction = self.node.get_option('store_wavefunction')

        run_type = self.node.inputs.parameters.get_dict().get('run_type')

        try:
            out_folder = self.retrieved
        except exceptions.NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        files_retrieved = self.retrieved.list_object_names()
        files_expected = [output_filename, output_wf_filename]

        if not set(files_expected) <= set(files_retrieved):
            self.logger.error("Found files '{}', expected to find '{}'".format(
                files_retrieved, files_expected))
            return self.exit_codes.ERROR_MISSING_OUTPUT_FILES

        import tarfile
        method = _DICTIONARES.get(run_type, None)
        if method:
            path_energy = f'aiida.ezfio/{method}/energy'
            with out_folder.open(output_wf_filename, 'rb') as wf_out:
                with tarfile.open(fileobj=wf_out, mode='r') as tar:
                    f_out = tar.extractfile(path_energy)
                    if f_out is None:
                        raise exceptions.ParsingError(
                            f'File {path_energy} not found in wavefunction file'
                        )
                    from aiida.orm import Float
                    self.out('utput_energy', Float(-1.0 * float(f_out.read())))
        else:
            energy = self._json_reader(out_folder)

        if store_wavefunction:
            # Store the wavefunction file
            with out_folder.open(output_wf_filename, 'rb') as handle:
                wf_file = SinglefileData(file=handle)

            wf_file.base.attributes.set('wavefunction', True)
            self.out('output_wavefunction', wf_file)

    def _json_reader(self, out_folder):
        # List aiida.wf/json/
        json_files = out_folder.list_object_names()
