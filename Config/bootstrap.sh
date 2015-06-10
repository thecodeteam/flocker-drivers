# Copyright (c) 2015 -  EMC Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

#!/usr/bin/env bash



# Install necessary iscsi software
sudo apt-get update
sudo apt-get install -y open-iscsi
sudo apt-get install -y lsscsi
sudo apt-get -y install scsitools

# Install other dependencies
sudo apt-get install -y git
sudo wget -qO- https://get.docker.io/gpg | sudo apt-key add -
sudo sh -c "echo deb http://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list"
sudo apt-get update
sudo apt-get install -y -q lxc-docker
sudo apt-get install -y gcc python2.7 python-virtualenv python2.7-dev python-pip
#sudo pip install machinist==0.2.0
#sudo pip install eliot==0.7.1
#sudo pip install python-keystoneclient==1.4.0
#sudo apt-get install -y libffi-dev
#sudo apt-get install -y libssl-dev
#sudo pip install pyasn1


# Make necessary configuration for iSCSI
if ! [ -L /etc/iscsi/iscsid.conf ]; then
	mv -f /etc/iscsi/iscsid.conf /tmp
	cp /vagrant/Config/iscsid.conf /etc/iscsi/iscsid.conf
fi

# Print out the initiator name
if ! [ -L /etc/iscsi/initiatorname.iscsi ]; then
	cat /etc/iscsi/initiatorname.iscsi
fi
