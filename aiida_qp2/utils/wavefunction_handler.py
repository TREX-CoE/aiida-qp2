# -*- coding: utf-8 -*-

"""
This module contains the wavefunction handler funcion
"""

from aiida.engine import calcfunction
from aiida.orm import List, SinglefileData
from aiida_qp2.utils.ezfio import ezfio
import tempfile
import tarfile
import os

@calcfunction
def wavefunction_handler(wavefunction, operations):
    """
    This function handles the wavefunction
    """

    _WF_NAME = "wavefunction.wf.tar.gz"

    changed = False
    data = []

    with tempfile.TemporaryDirectory() as temp_dir:
        wf_path = os.path.join(temp_dir, _WF_NAME)
        with open(wf_path, 'wb') as handle, \
             wavefunction.open(mode='rb') as wavefunction_handle:
            handle.write(wavefunction_handle.read())
        # untar the wavefunction
        with tarfile.open(wf_path, 'r:gz') as tar:
            tar.extractall(temp_dir)
        ezfio_path = os.path.join(temp_dir, "aiida.ezfio")
        ezfio.set_file(ezfio_path)
        for t, k, v in operations.get_list():
            if t == "get":
                method = getattr(ezfio, f"{t}_{k}", None)
                if method:
                    data.append([k, method()])
            if t == "set":
                method = getattr(ezfio, f"{t}_{k}", None)
                if method:
                    method(v)
                    changed = True
        if changed:
            with tarfile.open(wf_path, 'w:gz') as tar:
                tar.add(ezfio_path, arcname="aiida.ezfio")
            with open(wf_path, 'rb') as handle:
                wavefunction = SinglefileData(file=handle)


    ret = {"data": List(list=data)}

    if changed:
        ret["wavefunction"] = wavefunction

    return ret
