========
Tutorial
========

This page contains a simple tutorial for ``aiida-qp2`` plugin.

What we want to achieve
+++++++++++++++++++++++

Initialize the wave function file
---------------------------------

Create an EZFIO ``SinglefileData`` node from the existing ``StructureData`` instance using ``qp_create_ezfio`` dictionary::


        # Load the required AiiDA modules
        from aiida import orm, engine
        from aiida.common.exceptions import NotExistent

        # QP-related parameters
        ezfio_basename = 'hcn.ezfio'
        create_parameters = {
            'qp_create_ezfio': {
                'basis'  : '"6-31g"',      # QP-native basis set
                'charge' : '0',
                'output' : ezfio_basename
            }
        }

        # AiiDA-related parameters

        # Load the code
        try:
            code = orm.load_code('qp@localost')
        except:
            raise Exception(f'Create the qp2 code') from NotExistent

        # Build the calculation
        builder = code.get_builder()

        # Replace <StructureData_name> with the name of your StructureData object
        structure = load_node(pk=<StructureData_name>.pk)
        builder.structure = structure
        builder.parameters = orm.Dict(dict=create_parameters)
        # EZFIO directory name (to be tar.gz-ed)
        builder.metadata.options.output_wf_basename = ezfio_basename

        # Run the calculation & parse the results
        result = engine.run(builder)

        # Print the name of the output wave function (EZFIO) file
        print('EZFIO SinglefileData name   : ', result['output_wavefunction'].filename)


Note: it is possible to create a ``StructureData`` node from the XYZ atomic configuration file. For example, using the ``Molecule`` class of the ``pymatgen`` package::

        from pymatgen.core import Molecule
        mol = Molecule.from_file('hcn.xyz')
        structure = orm.StructureData(pymatgen_molecule=mol)

Perform calculations
--------------------

Use the previously created wave function file to run SCF (or any other type of QP-supported) calculation according to the ``qp_commands`` list::

        # QP-related parameters
        calc_parameters = {
            'qp_commands': [
                f'set_file {ezfio_basename}',
                'run scf'
                ]
        }

        # AiiDA-related parameters
        builder_scf = code.get_builder()

        builder_scf.parameters = orm.Dict(dict=calc_parameters)
        builder_scf.wavefunction = result['output_wavefunction']
        builder_scf.metadata.options.output_wf_basename = ezfio_basename

        # Run the calculation & parse the results
        result_scf = engine.run(builder_scf)

        # Print the computed SCF energy
        print('SCF energy (Hartree)        : ', result_scf['output_energy'])


The final result
+++++++++++++++++++++++

You have created a wave function file using parameters provided in ``qp_create_ezfio`` dict. You have then computed the SCF energy with Quantum Package via the ``aiida-qp2`` plugin using the ``qp_commands`` list. All input and output nodes have been stored in the data provenance and can be queried for.
