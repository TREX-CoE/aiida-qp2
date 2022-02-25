[![Build Status](https://github.com/TREX-CoE/aiida-qp2/workflows/ci/badge.svg?branch=master)](https://github.com/q-posev/aiida-qp2/actions)
[![Docs status](https://readthedocs.org/projects/aiida-qp2/badge)](http://aiida-qp2.readthedocs.io/)
[![PyPI version](https://badge.fury.io/py/aiida-qp2.svg)](https://badge.fury.io/py/aiida-qp2)

# aiida-qp2

AiiDA plugin for the Quanum Package 2.0 (QP2).

This plugin is the modified output of the
[AiiDA plugin cutter](https://github.com/aiidateam/aiida-plugin-cutter),
intended to help developers get started with their AiiDA plugins.

## Repository contents

* [`qp2/`](qp2/): The main source code of the plugin package
  * [`calculations.py`](qp2/calculations.py): A new `QP2Calculation` `CalcJob` class
  * [`parsers.py`](qp2/parsers.py): A new `Parser` for the `QP2Calculation`
* [`docs/`](docs/): A documentation template ready for publication on [Read the Docs](http://aiida-qp2.readthedocs.io/en/latest/)
* [`examples/`](examples/): Examples of how to submit a calculation using this plugin
* [`tests/`](tests/): Basic regression tests using the [pytest](https://docs.pytest.org/en/latest/) framework (submitting a calculation, ...). Install `pip install -e .[testing]` and run `pytest`.
* [`.github/`](.github/): [Github Actions](https://github.com/features/actions) configuration
  * [`ci.yml`](.github/workflows/ci.yml): runs tests, checks test coverage and builds documentation at every new commit
  * [`publish-on-pypi.yml`](.github/workflows/publish-on-pypi.yml): automatically deploy git tags to PyPI.
* [`.pre-commit-config.yaml`](.pre-commit-config.yaml): Configuration of [pre-commit hooks](https://pre-commit.com/) that sanitize coding style and check for syntax errors. Enable via `pip install -e .[pre-commit] && pre-commit install`
* [`.readthedocs.yml`](.readthedocs.yml): Configuration of documentation build for [Read the Docs](https://readthedocs.org/)
* [`LICENSE`](LICENSE): License for your plugin
* [`MANIFEST.in`](MANIFEST.in): Configure non-Python files to be included for publication on [PyPI](https://pypi.org/)
* [`README.md`](README.md): This file
* [`conftest.py`](conftest.py): Configuration of fixtures for [pytest](https://docs.pytest.org/en/latest/)
* [`pytest.ini`](pytest.ini): Configuration of [pytest](https://docs.pytest.org/en/latest/) test discovery
* [`setup.json`](setup.json): Plugin metadata for registration on [PyPI](https://pypi.org/) and the [AiiDA plugin registry](https://aiidateam.github.io/aiida-registry/) (including entry points)
* [`setup.py`](setup.py): Installation script for pip / [PyPI](https://pypi.org/)


## Features

* Initialize wave function files (EZFIO) based on `StructureData` instance and `qp_create_ezfio` dictionary.
This step can optionally use `BasisSet` and/or `Pseudopotential` nodes produced by the
[`aiida-gaussian-datatypes plugin`](https://github.com/addman2/aiida-gaussian-datatypes/tree/development_trvb).
* Run calculations (e.g. HF, CIPSI) in a particular order according to the `qp_commands` list. Some pre- or post-processing is also possible by providing a list of commands in `qp_prepend` or `qp_append` keys of the `parameters` Dict, respectively.
* Export TREXIO files from QP


## Installation

```shell
pip install aiida-qp2
verdi quicksetup  # better to set up a new profile
verdi plugin list aiida.calculations  # should now show your calclulation plugins
```

## Usage

 See [`Demo-aiida-qp.md`](examples/Demo-aiida-qp.md) and `.py` files in the `examples` directory

For instance, the `example_trexio_from_xyz.py` is an example of 3-step workflow using the plugin.

```shell
verdi daemon start     # make sure the daemon is running
cd examples
python example_trexio_from_xyz.py   # prepare and submit the calculation
verdi process list -a  # check record of calculation
```

1. Create the EZFIO wave function file from the `hcn.xyz` file using a given basis set.
2. Run SCF calculation using previously create wave function and parses the output file looking for the Hartree-Fock energy
3. Export TREXIO wave function file by converting EZFIO format using `TREXIO_TEXT` back end


## Development

```shell
git clone https://github.com/q-posev/aiida-qp2 .
cd aiida-qp2
pip install -e .[pre-commit,testing]  # install extra dependencies
pre-commit install  # install pre-commit hooks
```

## License

MIT

## Contact

posenitskiy@irsamc.ups-tlse.fr
scemama@irsamc.ups-tlse.fr
