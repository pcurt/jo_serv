# jo_serv

JO server source code

- [Development Quickstart](#development-quickstart)
- [Installation](#installation)
  - [From a release archive](#from-a-release-archive)
  - [From sources](#from-sources)
- [Usage](#usage)

## Development Quickstart

A quickstart guide/cheatsheet is [available here](./Quickstart.md), that lists the useful commands when developing this package.

## Installation

The two following methods will install this project as an executable callable directly from your terminal.

Note that you should ideally run these `pip` commands in an active [virtualenv](https://docs.python.org/3/library/venv.html), and not in your system Python install.

### From a release archive

To install jo_serv, download the latest release archive fom Github, and run this command in your terminal:

``` sh
pip install jo_serv-0.1.0-py3-none-any.whl
# or
pip install jo_serv-0.1.0.tar.gz
```

### From sources

The sources for jo_serv can be downloaded from the [Github repo](https://github.com/pcurt/jo_serv).

Start by cloning the repository:

``` sh
git clone https://github.com/pcurt/jo_serv
```

Then enter the cloned directory (with `cd jo_serv/`), and install the project with:

``` sh
pip install .
```

## Usage

Describe here how to use this Python package: CLI options and flags, API when imported by another package, etc.
