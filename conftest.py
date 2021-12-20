# -*- coding: utf-8 -*-
"""pytest fixtures for simplified testing."""
from __future__ import absolute_import
import pytest

pytest_plugins = ['aiida.manage.tests.pytest_fixtures']


@pytest.fixture(scope='function', autouse=True)
def clear_database_auto(clear_database):  # pylint: disable=unused-argument
    """Automatically clear database in between tests."""


# TODO: Change default path to something more general
@pytest.fixture(scope='function')
def qp2_code(aiida_local_code_factory):
    """Get a qp2 code.
    """
    return aiida_local_code_factory(executable='/home/evgeny/qp2/bin/qpsh',
                                    entry_point='qp2')
