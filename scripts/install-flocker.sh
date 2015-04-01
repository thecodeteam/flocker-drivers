#!/bin/bash

# Installs Flocker from Source

EMC_SRC="https://wallnr@git.lss.emc.com/scm/floc/flocker.git"
PUB_SRC="https://github.com/ClusterHQ/flocker"

SRC_DIR="/opt/flocker/"

# TODO install from local EMC Source
# //TODO

# Clone public flocker source for now.
git clone $PUB_SRC $SRC_DIR

pip install virtualenv

# we actually dont want this, because it make it impossible
# for interactive sessions of flocker to know about the venv
# virtualenv venv && source venv/bin/activate

pip install --upgrade  eliot
pip install --upgrade  machinist
python $SRC_DIR/flocker/setup.py install

