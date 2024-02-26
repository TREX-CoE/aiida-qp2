# -*- coding: utf-8 -*-
"""
Parser for the QP2Create calculation.

"""

from os.path import join as path_join

from aiida.engine import ExitCode
from aiida.parsers.parser import Parser
from aiida.plugins import CalculationFactory
from aiida.common import exceptions
from aiida.orm import Float, SinglefileData

from ase.io import read

QP2Calculation = CalculationFactory('qp2.create')


class QP2CreateParser(Parser):
    """
    Parser class for parsing output of `create` calculation.
    """
    def __init__(self, node):
        """
        Initialize Parser instance

        Checks that the ProcessNode being passed was produced by a QP2Calculation.

        :param node: ProcessNode of calculation
        :param type node: :class:`aiida.orm.ProcessNode`
        """
        super().__init__(node)
        if not issubclass(node.process_class, QP2Calculation):
            raise exceptions.ParsingError('Can only parse QP2Calculation')

    def parse(self, **kwargs):  # pylint: disable=too-many-locals
        """
        Parse outputs, store results in database.

        :returns: an exit code, if parsing fails (or nothing if parsing succeeds)
        """

        # Load metadata
        output_filename = self.node.get_option('output_filename')
        output_wf_filename = self.node.get_option(
            'output_wf_basename') + '.tar.gz'

        # Put wavefunction into the output nodes
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

        # Store the wavefunction in the database
        with out_folder.open(output_wf_filename, 'rb') as handle:
            wf_file = SinglefileData(file=handle)

        # Read the structure from the input file
        with out_folder.open("aiida.xyz", 'r') as handle:
            atoms = read(handle, format='xyz')

        # Set the wavefunction as an attribute of the output node
        wf_file.base.attributes.set("wavefunction", True)
        wf_file.base.attributes.set("formula", atoms.get_chemical_formula())

        self.out('wavefunction', wf_file)

        return ExitCode(0)
