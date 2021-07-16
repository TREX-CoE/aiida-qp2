# -*- coding: utf-8 -*-
"""
Parsers provided by qp2.

Register parsers via the "aiida.parsers" entry point in setup.json.
"""

from os.path import join as path_join

from aiida.engine import ExitCode
from aiida.parsers.parser import Parser
from aiida.plugins import CalculationFactory
from aiida.common import exceptions
from aiida.orm import Float, RemoteData
from aiida.orm import load_computer

QpCalculation = CalculationFactory('qp2')


class QpParser(Parser):
    """
    Parser class for parsing output of calculation.
    """
    def __init__(self, node):
        """
        Initialize Parser instance

        Checks that the ProcessNode being passed was produced by a QpCalculation.

        :param node: ProcessNode of calculation
        :param type node: :class:`aiida.orm.ProcessNode`
        """
        super().__init__(node)
        if not issubclass(node.process_class, QpCalculation):
            raise exceptions.ParsingError('Can only parse QpCalculation')

    def parse(self, **kwargs):  # pylint: disable=too-many-locals
        """
        Parse outputs, store results in database.

        :returns: an exit code, if parsing fails (or nothing if parsing succeeds)
        """
        output_filename = self.node.get_option('output_filename')

        try:
            out_folder = self.retrieved
        except exceptions.NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        # Check that folder content is as expected
        files_retrieved = self.retrieved.list_object_names()
        files_expected = [output_filename]
        # Note: set(A) <= set(B) checks whether A is a subset of B
        if not set(files_expected) <= set(files_retrieved):
            self.logger.error("Found files '{}', expected to find '{}'".format(
                files_retrieved, files_expected))
            return self.exit_codes.ERROR_MISSING_OUTPUT_FILES

        # OPTIONAL output part. Can be adapted to produce output_parameters Dict with output quantities
        # Open the output_filename file and parse it (e.g. look for the computer SCF energy)
        self.logger.info("Parsing '{}'".format(output_filename))
        with self.retrieved.open(output_filename, 'r') as f_out:
            scf_en_found = False

            for line in f_out:
                if 'SCF energy' in line:
                    data = line.split()
                    scf_en_found = True

            if scf_en_found:
                energy = Float(float(data[-1]))
                self.out('output_energy', energy)
            # TEMPORARILY disable this exit code to check qp_create_ezfio
            #else:
            #    return self.exit_codes.ERROR_MISSING_ENERGY

        # The ezfio tar.gz file is the REQUIRED output of the qp2 calculation
        # i.e. it should always be detected and stored (see below)

        # Get the ezfio basename and job UUID from the input parameters
        output_ezfio_base = self.node.get_option('output_ezfio_basename')
        uuid = self.node.uuid  #pylint: disable=protected-access
        short_uuid = uuid[:8]  #pylint: disable=protected-access
        # Build full name and path for the output ezfio tarball
        output_ezfio_name = f'{output_ezfio_base}_{short_uuid}.tar.gz'
        abs_path_ezfio = path_join(
            out_folder._repository._get_base_folder().abspath,  #pylint: disable=protected-access
            output_ezfio_name)
        # Get the remote computer name and load the computer (required for RemoteData output node)
        computer_label = self.node.get_option('computer')
        remote_computer = load_computer(label=computer_label)
        # Create a RemoteData node corresponding to the output ezfio tarball
        remote_ezfio = RemoteData(remote_path=abs_path_ezfio,
                                  computer=remote_computer)
        # Set the `output_ezfio` node
        self.out('output_ezfio', remote_ezfio)

        return ExitCode(0)
