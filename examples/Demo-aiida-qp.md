# Demo run on HCN molecule with aiida-qp2 plugin

Prepared for the TREX-CoE hackathon at the UVSQ (France).

## Initial setup


```python
%aiida
```






```python
from os import path
from pymatgen.core import Molecule
from aiida import orm, engine
from aiida.common.exceptions import NotExistent
from aiida.plugins import DataFactory
```


```python
INPUT_DIR     = 'input_files'
XYZ_FILE      = 'hcn.xyz'
EZFIO_NAME    = XYZ_FILE.replace('.xyz', '.ezfio')

#COMPUTER_NAME = 'tutor'
#CODE_NAME     = 'qp2'
COMPUTER_NAME = 'olympe'
CODE_NAME     = 'qp2_singularity'
```


```python
# Load the computer
try:
    computer = orm.load_computer(f'{COMPUTER_NAME}')
except:
    raise Exception(f'Create the {COMPUTER_NAME} computer') from NotExistent
```


```python
# Load the code
try:
    code = orm.load_code(f'{CODE_NAME}@{COMPUTER_NAME}')
except:
    raise Exception(f'Create the {CODE_NAME} code') from NotExistent
```

## Initialize the wave function file based on the atomic configuration


```python
# Create a StructureData node for the calculation
mol = Molecule.from_file(path.join(INPUT_DIR, XYZ_FILE))
structure = orm.StructureData(pymatgen_molecule=mol)

# Load existing StructureData node
# structure = load_node(pk=???)
```


```python
# BasisSet section: build a dictionary with
#   key   - label of the atom
#   value - instance of the BasisSet node corresponding to the "basis_name" basis set
BasisSet = DataFactory('gaussian.basisset')
basis_name = 'aug-cc-pVDZ'
# symbol_set is an attribute of Molecule class from pymatgen, it contains a tuple of unique atoms
basis_dict = {
    atom : BasisSet.get(element=atom, name=basis_name)
    for atom in mol.symbol_set
}
# Skip this cell if QP-native basis set is used
```


```python
# Dictionary of the QP create_ezfio parameters
# (qp_create_ezfio key is dedicated to the initialization of the wave function)
# At the moment the name of the basis set (aiida-basis-set) and ECP files is hardcoded in qp2 plugin
create_parameters = {
    'qp_create_ezfio': {
        'basis'  : 'aiida-basis-set',         # aiida-gdt basis set
        #'basis': '"6-31g"',                  # QP-native basis set
        'charge' : '0',
        'output' : EZFIO_NAME,
    }
}
```


```python
# Build the calculation
builder_init = code.get_builder()

builder_init.structure = structure
builder_init.basissets = basis_dict  # comment this line if QP-native basis set is used
builder_init.parameters = orm.Dict(dict=create_parameters)

builder_init.metadata.options.output_wf_basename = EZFIO_NAME # EZFIO directory name (to be tar.gz-ed)
builder_init.metadata.options.output_filename = 'qp.out'      # stdout goes here
builder_init.metadata.description = 'Create an EZFIO file via the aiida-qp2 plugin'
builder_init.metadata.computer = computer
builder_init.metadata.options.max_wallclock_seconds = 30 * 60
builder_init.code = code

#builder_init.metadata.dry_run = True
#builder_init.metadata.store_provenance = False
```


```python
# Run the calculation & parse the results
print('\n QP create_ezfio execution: STARTED \n')

result_init = engine.run(builder_init)

print('\n QP create_ezfio execution: FINISHED \n')
```


     QP create_ezfio execution: STARTED


     QP create_ezfio execution: FINISHED




```python
# Print some results
print('EZFIO SinglefileData object : ', result_init['output_wavefunction'])
print('EZFIO SinglefileData name   : ', result_init['output_wavefunction'].filename)
# .pk or .uuid are valid attributes for any AiiDA node (including Data nodes)
```

    EZFIO SinglefileData object :  uuid: 7ea374d3-8842-43ed-8620-274e19e649e9 (pk: 605)
    EZFIO SinglefileData name   :  hcn.ezfio.tar.gz


## Run simple wave function-based calculation (SCF)


```python
# Pre-process output of the previous step
pk_ezfio = result_init['output_wavefunction'].pk
ezfio_file = load_node(pk=pk_ezfio)
ezfio_input_name = ezfio_file.filename.replace('.tar.gz', '')

# Dictionary of the QP calculation parameters
calc_parameters = {
    'qp_commands': [
        f'set_file {ezfio_input_name}',
        'run scf'
        ]
}
```


```python
# Build the calculation
builder_calc = code.get_builder()

builder_calc.parameters = orm.Dict(dict=calc_parameters)
builder_calc.wavefunction = ezfio_file
builder_calc.metadata.options.output_wf_basename = ezfio_input_name

builder_calc.metadata.options.output_filename = 'qp.out'            # stdout goes here
builder_calc.metadata.description = 'Run SCF calculation via the aiida-qp2 plugin'
builder_calc.metadata.computer = computer
builder_calc.metadata.options.max_wallclock_seconds = 60 * 60
builder_calc.code = code
```


```python
# Run the calculation & parse the results
print('\n QP run_scf execution: STARTED \n')

result_scf = engine.run(builder_calc)

print('\n QP run_scf execution: FINISHED \n')
```


     QP run_scf execution: STARTED


     QP run_scf execution: FINISHED




```python
# Print some results
print('EZFIO SinglefileData object : ', result_scf['output_wavefunction'])
print('EZFIO SinglefileData name   : ', result_scf['output_wavefunction'].filename)
print('SCF energy (Hartree)        : ', result_scf['output_energy'])
```

    EZFIO SinglefileData object :  uuid: bd5357b5-9335-477a-8a42-bdce1442bfef (pk: 611)
    EZFIO SinglefileData name   :  hcn.ezfio.tar.gz
    SCF energy (Hartree)        :  uuid: 024dc594-2977-4677-b0f3-018bf4a249ff (pk: 610) value: -42.098574333011


## Produce the TREXIO file from QP-native EZFIO format


```python
# Pre-process output of the previous step
pk_ezfio = result_scf['output_wavefunction'].pk
ezfio_file = load_node(pk=pk_ezfio)
ezfio_input_name = ezfio_file.filename.replace('.tar.gz', '')

output_trexio_basename = 'hcn.trexio.text'
# Dictionary of the QP export_trexio parameters
export_parameters = {
    'qp_commands': [
        f'set_file {ezfio_input_name}',
        'set trexio backend 1',             # 1 is for TREXIO_TEXT, 0 is for TREXIO_HDF5 (default)
        f'set trexio trexio_file {output_trexio_basename}',
        'run export_trexio'
        ]
}
```


```python
# Build the calculation
builder_export = code.get_builder()

builder_export.parameters = orm.Dict(dict=export_parameters)
builder_export.wavefunction = ezfio_file
builder_export.metadata.options.output_wf_basename = output_trexio_basename # IMPORTANT !

builder_export.metadata.options.output_filename = 'qp.out'            # stdout goes here
builder_export.metadata.description = 'Export TREXIO file from the QP via the aiida-qp2 plugin'
builder_export.metadata.computer = computer
builder_export.metadata.options.max_wallclock_seconds = 30 * 60
builder_export.code = code
```


```python
# Run the calculation & parse the results
print('\n QP export_trexio execution: STARTED \n')

result_export = engine.run(builder_export)

print('\n QP export_trexio execution: FINISHED \n')
```


     QP export_trexio execution: STARTED


     QP export_trexio execution: FINISHED




```python
# Print some results
print('TREXIO SinglefileData object : ', result_export['output_wavefunction'])
print('TREXIO SinglefileData name   : ', result_export['output_wavefunction'].filename)
```

    TREXIO SinglefileData object :  uuid: 48b62512-21e2-4d3e-834d-c0ce4384d2b6 (pk: 616)
    TREXIO SinglefileData name   :  hcn.trexio.text.tar.gz


## That's all, folks!
