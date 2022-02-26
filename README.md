[![Build Status](https://github.com/TREX-CoE/aiida-qp2/workflows/ci/badge.svg?branch=master)](https://github.com/q-posev/aiida-qp2/actions)
[![PyPI version](https://badge.fury.io/py/aiida-qp2.svg)](https://badge.fury.io/py/aiida-qp2)

# aiida-qp2

AiiDA plugin for [Quantum Package 2.0](https://github.com/QuantumPackage/qp2) (QP2).

This plugin is the modified output of the
[AiiDA plugin cutter](https://github.com/aiidateam/aiida-plugin-cutter),
intended to help developers get started with their AiiDA plugins.

## Repository contents

* [`aiida_qp2/`](aiida_qp2/): The main source code of the plugin package
  * [`calculations.py`](aiida_qp2/calculations.py): A new `QP2Calculation` `CalcJob` class
  * [`parsers.py`](aiida_qp2/parsers.py): A new `Parser` for the `QP2Calculation`
* [`docs/`](docs/): A documentation template. The [ReadTheDocs documentation](https://trex-coe.github.io/aiida-qp2/) is built and deployed on the `gh-pages` branch.
* [`examples/`](examples/): Examples of how to submit a calculation using this plugin
* [`LICENSE`](LICENSE): License for your plugin
* [`MANIFEST.in`](MANIFEST.in): Configure non-Python files to be included for publication on [PyPI](https://pypi.org/)
* [`README.md`](README.md): This file
* [`setup.json`](setup.json): Plugin metadata for registration on [PyPI](https://pypi.org/) and the [AiiDA plugin registry](https://aiidateam.github.io/aiida-registry/) (including entry points)
* [`setup.py`](setup.py): Installation script for pip / [PyPI](https://pypi.org/)
* [`.pre-commit-config.yaml`](.pre-commit-config.yaml): Configuration of [pre-commit hooks](https://pre-commit.com/) that sanitize coding style and check for syntax errors. Enable via `pip install -e .[pre-commit] && pre-commit install`
* [`.github/`](.github/): [Github Actions](https://github.com/features/actions) configuration
  * [`ci.yml`](.github/workflows/ci.yml): runs tests and builds documentation at every new commit
  * [`publish-on-pypi.yml`](.github/workflows/publish-on-pypi.yml): automatically deploy git tags to PyPI


## Features

* Initialize a wave function file (EZFIO) based on `StructureData` instance and `qp_create_ezfio` dictionary.
This step can optionally use `BasisSet` and/or `Pseudopotential` nodes produced by the
[`aiida-gaussian-datatypes`](https://github.com/addman2/aiida-gaussian-datatypes/tree/development_trvb) plugin.
* Run calculations (e.g. HF, CIPSI) in a given order according to the `qp_commands` list. Some pre- or post-processing (e.g. `shell` scripting) is also possible by providing a list of commands in `qp_prepend` or `qp_append` keys of the `parameters` Dict, respectively.
* Export TREXIO file from the QP-native EZFIO format.


## Installation

```shell
pip install aiida-qp2
verdi quicksetup  # better to set up a new profile
verdi plugin list aiida.calculations  # should now show your calclulation plugins
```

## Usage

 See [`Demo-aiida-qp.md`](examples/Demo-aiida-qp.md) and `.py` files in the [`examples/`](examples/) directory.

For instance, the `example_trexio_from_xyz.py` is the 3-step workflow using the plugin.

```shell
verdi daemon start     # make sure the daemon is running
cd examples
python example_trexio_from_xyz.py   # prepare and submit the calculation
verdi process list -a  # check record of calculation
```

1. Create the EZFIO wave function file from the `hcn.xyz` file using a given basis set.
2. Run SCF calculation using the previously created wave function and parse the output file looking for the Hartree-Fock energy.
3. Export TREXIO wave function file by converting EZFIO format using `TREXIO_TEXT` back end.


## Development

```shell
git clone https://github.com/TREX-CoE/aiida-qp2 .
cd aiida-qp2
pip install -e .[pre-commit]  # install extra dependencies
pre-commit install  # install pre-commit hooks
```

## License

MIT

## Contact

posenitskiy@irsamc.ups-tlse.fr

scemama@irsamc.ups-tlse.fr
