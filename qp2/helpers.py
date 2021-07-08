# -*- coding: utf-8 -*-
""" Helper functions for automatically setting up computer & code.
Helper functions for setting up

 1. An AiiDA localhost computer
 2. A "diff" code on localhost

Note: Point 2 is made possible by the fact that the ``diff`` executable is
available in the PATH on almost any UNIX system.
"""
import tempfile
import shutil
from aiida.orm import Computer, Code
from aiida.common.exceptions import NotExistent

LOCALHOST_NAME = 'localhost-test'

executables = {
    'qp2': 'diff',
}


def get_path_to_executable(executable):
    """ Get path to local executable.
    :param executable: Name of executable in the $PATH variable
    :type executable: str
    :return: path to executable
    :rtype: str
    """
    path = shutil.which(executable)
    if path is None:
        raise ValueError(
            "'{}' executable not found in PATH.".format(executable))
    return path


def get_computer(name=LOCALHOST_NAME, workdir=None):
    """Get AiiDA computer.
    Loads computer 'name' from the database, if exists.
    Sets up local computer 'name', if it isn't found in the DB.

    :param name: Name of computer to load or set up.
    :param workdir: path to work directory
        Used only when creating a new computer.
    :return: The computer node
    :rtype: :py:class:`aiida.orm.Computer`
    """

    try:
        computer = Computer.objects.get(label=name)
    except NotExistent:
        if workdir is None:
            workdir = tempfile.mkdtemp()

        computer = Computer(
            label=name,
            description='localhost computer set up by aiida_diff tests',
            hostname=name,
            workdir=workdir,
            transport_type='local',
            scheduler_type='direct')
        computer.store()
        computer.set_minimum_job_poll_interval(0.)
        computer.configure()

    return computer


def get_code(entry_point, computer):
    """Get local code.
    Sets up code for given entry point on given computer.

    :param entry_point: Entry point of calculation plugin
    :param computer: (local) AiiDA computer
    :return: The code node
    :rtype: :py:class:`aiida.orm.Code`
    """

    try:
        executable = executables[entry_point]
    except KeyError as exc:
        raise KeyError(
            "Entry point '{}' not recognized. Allowed values: {}".format(
                entry_point, list(executables.keys()))) from exc

    codes = Code.objects.find(filters={'label': executable})  # pylint: disable=no-member
    if codes:
        return codes[0]

    path = get_path_to_executable(executable)
    code = Code(
        input_plugin_name=entry_point,
        remote_computer_exec=[computer, path],
    )
    code.label = executable
    return code.store()
