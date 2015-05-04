#!/bin/bash

# Installs Flocker from Source
USER=""
EMC_SRC="-b feat_scaleio_emc https://github.com/ClusterHQ/flocker-emc"
PUB_SRC="https://github.com/ClusterHQ/flocker"

SRC_DIR="/opt/flocker/flocker"

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
pip install --upgrade pyyaml
yum -yy install openssl openssl-devel libffi-devel
cd $SRC_DIR && python $SRC_DIR/setup.py install
pip install -qq -e .[dev]

# ScaleIO Driver needs scaleio-py
cd /opt/flocker
git clone https://github.com/swevm/scaleio-py.git
cd scaleio-py
python setup.py install


# Flocker ports need to be open
systemctl enable firewalld
systemctl start firewalld
firewall-cmd --add-icmp-block=echo-request 
firewall-cmd --permanent --direct --add-rule ipv4 filter FORWARD 0 -j ACCEPT
firewall-cmd --direct --add-rule ipv4 filter FORWARD 0 -j ACCEPT
# Docker port
firewall-cmd --permanent --zone=public --add-port=4243/tcp
# ScaleIO ports needs to be open
firewall-cmd --permanent --zone=public --add-port=6611/tcp
firewall-cmd --permanent --zone=public --add-port=9011/tcp
firewall-cmd --permanent --zone=public --add-port=7072/tcp
firewall-cmd --permanent --zone=public --add-port=443/tcp
firewall-cmd --permanent --zone=public --add-port=22/tcp
firewall-cmd --reload

# Docker needs to reload iptables after this.
service docker restart


# Add insecure private key for access
mkdir /root/.ssh
touch /root/.ssh/authorized_keys
echo "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA6NF8iallvQVp22WDkTkyrtvp9eWW6A8YVr+kz4TjGYe7gHzIw+niNltGEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEDo3MlTBckFXPITAMzF8dJSIFo9D8HfdOV0IAdx4O7PtixWKn5y2hMNG0zQPyUecp4pzC6kivAIhyfHilFR61RGL+GPXQ2MWZWFYbAGjyiYJnAmCP3NOTd0jMZEnDkbUvxhMmBYSdETk1rRgm+R4LOzFUGaHqHDLKLX+FIPKcF96hrucXzcWyLbIbEgE98OHlnVYCzRdK8jlqm8tehUc9c9WhQ== vagrant insecure public key" > /root/.ssh/authorized_keys
