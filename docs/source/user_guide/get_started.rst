===============
Getting started
===============

This page should contain a short guide on what the plugin does and
a short example on how to use the plugin.

Installation
++++++++++++

Use the following commands to install the plugin::

    git clone https://github.com/q-posev/aiida-qp2 .
    cd aiida-qp2
    pip install -e .  # also installs aiida, if missing (but not postgres)
    #pip install -e .[pre-commit,testing] # install extras for more features
    verdi quicksetup  # better to set up a new profile
    verdi calculation plugins  # should now show your calclulation plugins

Then use ``verdi code setup`` with the ``aiida_qp2`` input plugin
to set up an AiiDA code for qp2.

Usage
+++++

A quick demo of how to submit a calculation::

    verdi daemon start         # make sure the daemon is running
    cd examples
    verdi run test_submit.py        # submit test calculation
    verdi calculation list -a  # check status of calculation

Available calculations
++++++++++++++++++++++

.. aiida-calcjob:: QP2Calculation
    :module: aiida_qp2.calculations
