# Prologin SADM

SADM stands for *System ADMinistration*. This is the
[Prologin](https://prologin.org) contest finals infrastructure.

This repository contains:

  * the core SADM Python package: Python implementation of various internal
    services and Django websites
  * the configuration files for these services
  * a collection of scripts to set up the infrastructure, for both production
    machines and development using containers
  * various dependencies packaged as Archlinux packages
  * documentation on how to deploy this infrastructure and develop on it

Please refer to the full documentation: <https://prologin-sadm.readthedocs.io/>

## Contributing

### Python style

SADM uses [black](https://github.com/psf/black) to format its python code and
[flake8](https://flake8.pycqa.org/) to enforce the style guide. Before
submitting, please make sure that your code is properly formatted and
documented!

### Pre-commit

SADM provides a [pre-commit](https://pre-commit.com/]) configuration for you to
check your changes before submitting them.

To setup `pre-commit`, run:

```sh
$ pip install -r requirements-dev.txt
$ pre-commit install
```

This will run black over the code to be committed and if anything changes the
pre-commit will fail. Simply try again and the re-formatted code will be
committed.
