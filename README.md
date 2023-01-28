
README GENERATOR
================
This package is based on the oca-gen-addon-readme from the OCA/maintainer-tools.git repo
wich is licensed AGPL-3

This is a small utility that generates high quality README for our odoo modules we
in an automated way.

The sections of the final README are organized in fragments. They must be put inside a
readme folder respecting this structure.

    tony_stark_module
    ├── views
    ├── readme
    |   ├── CONFIGURE.rst
    |   ├── CONTRIBUTORS.rst
    |   ├── CREDITS.rst
    |   ├── DESCRIPTION.rst
    |   ├── HISTORY.rst
    |   ├── INSTALL.rst
    |   ├── READMAP.rst
    |   └── USAGE.rst
    ├── reports
    ├── static
    └── views

eg. To generate the final README for each module of the repository we can say (if we are stand in the repository root)

    gen-readme --repo-name=stark-enterprises --branch=16.0 --addon-dir="$PWD"

The result is a fully pypi compilant README.rst in the root of each module of the repo


Installation
------------

    sudo pip install gen_odoo_readme

see proyect in https://pypi.org/project/gen-odoo-readme/

Use el comando gen-readme --help para obtener esta ayuda

    Usage: gen-readme [OPTIONS]

    Options:
    --org-name TEXT             Organization name  [required]
    --repo-name TEXT            Repository name, eg. server-tools.  [required]
    --branch TEXT               Odoo series. eg 11.0.  [required]
    --addons-dir DIRECTORY      Directory containing several addons, the README
                                will be generated for all installable addons
                                found there.  [required]
    --gen-html / --no-gen-html  Generate index html file.
    --help                      Show this message and exit.

Recomendation
-------------

We recommend to set a small make_readme.sh file in each repo as this

    #!/usr/bin/env bash
    #################################
    # Generate the odoo README.rst documentacion for each module in
    # the current repository.
    # you must install this: pip install gen-odoo-readme

    gen-readme \
        --org-name quilsoft-org \
        --repo-name tony_star \
        --branch 16.0 \
        --addons-dir "$PWD"
