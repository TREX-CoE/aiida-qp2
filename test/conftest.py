# -*- coding: utf-8 -*-
"""
For pytest
initialise a text database and profile
"""

import pytest

pytest_plugins = ['aiida.manage.tests.pytest_fixtures']


@pytest.fixture(scope='function', autouse=True)
def clear_database_auto(aiida_profile_clean):
    """Automatically clear database in between tests."""
    pass
