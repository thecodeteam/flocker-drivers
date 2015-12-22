#!/bin/bash
# Copyright 2015 EMC Corporation

yum install -y docker
sed -i 's/OPTIONS=\(.*\)/OPTIONS=\1 -H tcp:\/\/0.0.0.0:4243 -H unix:\/\/\/var\/run\/docker.sock/g' /etc/sysconfig/docker
# SystemCTL complains about single quotes and won't start
sed -i 's/OPTIONS='--selinux-enabled'/OPTIONS=--selinux-enabled/g' /etc/sysconfig/docker

# Device mapper Base isnt exported with old version, need to update.
yum update -y device-mapper-libs
service docker restart

# enable root login, key authentication will still need to be setup
sed -i 's/PermitRootLogin .*/PermitRootLogin yes/g' /etc/ssh/sshd_config
service sshd restart

# Add EMC certs
yum install ca-certificates
update-ca-trust enable
cp /vagrant/certs/*.crt /etc/pki/ca-trust/source/anchors/
update-ca-trust extract

# prepare env to install flocker
yum install -y git gcc python-devel
curl "https://bootstrap.pypa.io/get-pip.py" -o "/opt/get-pip.py"
python /opt/get-pip.py
pip install --upgrade pip
yum install -y git