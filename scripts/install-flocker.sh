#!/bin/bash

# Installs Flocker from Source

EMC_SRC="https://wallnr@git.lss.emc.com/scm/floc/flocker.git"
PUB_SRC="https://github.com/ClusterHQ/flocker"

SRC_DIR="/opt/flocker"

cd $SRC_DIR
pip install virtualenv && virtualenv venv && source venv/bin/activate
pip install --upgrade  eliot
pip install --upgrade  machinist
python setup.py install

