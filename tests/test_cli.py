# -*- coding: utf-8 -*-
""" Tests for command line interface.

"""
from click.testing import CliRunner
from aiida.plugins import DataFactory

from qp2.cli import list_, export


# pylint: disable=attribute-defined-outside-init
class TestDataCli:
    """Test verdi data cli plugin."""
    def setup_method(self):
        """Prepare nodes for cli tests."""
        DiffParameters = DataFactory('qp2')
        self.parameters = DiffParameters({'ignore-case': True})
        self.parameters.store()
        self.runner = CliRunner()

    def test_data_diff_list(self):
        """Test 'verdi data qp2 list'

        Tests that it can be reached and that it lists the node we have set up.
        """
        result = self.runner.invoke(list_, catch_exceptions=False)
        assert str(self.parameters.pk) in result.output

    def test_data_diff_export(self):
        """Test 'verdi data qp2 export'

        Tests that it can be reached and that it shows the contents of the node
        we have set up.
        """
        result = self.runner.invoke(export, [str(self.parameters.pk)],
                                    catch_exceptions=False)
        assert 'ignore-case' in result.output
