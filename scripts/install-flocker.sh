#!/bin/bash

# Installs Flocker from Source
USER=""
SIO_PLUGIN="https://github.com/emccorp/scaleio-flocker-driver"
FLOCKER_SRC="https://github.com/ClusterHQ/flocker"

FLOCKER_SRC_DIR="/opt/flocker/flocker"
PLUGIN_SRC_DIR="/opt/flocker/scaleio-flocker-driver"

git clone $FLOCKER_SRC $FLOCKER_SRC_DIR
# Comment out until public
#git clone $PLUGIN_SRC $PLUGIN_SRC_DIR

pip install virtualenv

# we actually dont want this, because it make it impossible
# for interactive sessions of flocker to know about the venv
# virtualenv venv && source venv/bin/activate

pip install --upgrade  eliot
pip install --upgrade  machinist
pip install --upgrade pyyaml
pip install bitmath
pip install service_identity
yum -yy install openssl openssl-devel libffi-devel
cd $SRC_DIR && python $SRC_DIR/setup.py install
pip install -qq -e .[dev]

# ScaleIO Driver needs scaleio-py
# eventually will be pip installable
cd /opt/flocker
git clone https://github.com/swevm/scaleio-py.git
cd scaleio-py
python setup.py install

# Install ScaleIO Driver
# (Comment out until public)
#cd /opt/flocker/scaleio-flocker-driver
#python setup.py install

# scaleio-py instals 2.5.1, flocker can't use over 2.5.0
pip uninstall requests
pip install 'requests==2.4.3'

# flocker specific directory
mkdir /etc/flocker
chmod 0700 /etc/flocker

# You still need to create node certs and API
# user certs manually.
# 4  flocker-ca create-node-certificate
# 5  cp 132ebcea-b19b-4452-8e4d-b59754a56c63.crt /etc/flocker/node.crt
# 6  cp 132ebcea-b19b-4452-8e4d-b59754a56c63.key /etc/flocker/node.key
# 7  flocker-ca create-api-certificate user
if [ "$HOSTNAME" = tb.scaleio.local ]; then
    printf '%s\n' "on the tb host"
    cd /opt/flocker/flocker/
    flocker-ca initialize mycluster
    flocker-ca create-control-certificate tb.scaleio.local
    cp control-tb.scaleio.local.crt /etc/flocker/control-service.crt
    cp control-tb.scaleio.local.key /etc/flocker/control-service.key
    cp cluster.crt /etc/flocker/cluster.crt
    chmod 0600 /etc/flocker/control-service.key
    

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
