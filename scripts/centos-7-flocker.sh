#!/bin/bash

#INST=$1
#if [ ! -d $INST ]; then
#        echo "Need internal or external"
#        echo "centos-7-install.sh install | external"
#        exit(1)
#fi

yum install -y docker
sed -i 's/OPTIONS=\(.*\)/OPTIONS=\1 -H tcp:\/\/0.0.0.0:4243 -H unix:\/\/\/var\/run\/docker.sock/g' /etc/sysconfig/docker
# SystemCTL complains about single quotes and won't start
sed -i "s/OPTIONS='--selinux-enabled'/OPTIONS=--selinux-enabled/g" /etc/sysconfig/docker
# Device mapper Base isnt exported with old version, need to update.
yum update -y device-mapper-libs
service docker restart

# enable root login, key authentication will still need to be setup
sed -i 's/PermitRootLogin .*/PermitRootLogin yes/g' /etc/ssh/sshd_config
service sshd restart

# Add EMC certs
yum install ca-certificates
update-ca-trust enable
cp /vagrant/certs/EMC*.crt /etc/pki/ca-trust/source/anchors/
update-ca-trust extract

# install zfs for flocker

# via http://zfsonlinux.org/epel.html (Doesnt work?)
#yum localinstall --nogpgcheck https://download.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
#yum localinstall --nogpgcheck http://archive.zfsonlinux.org/epel/zfs-release.el7.noarch.rpm
#yum install -y kernel-devel zfs

# // TODO use $INST to trigger one install or ther other.

#*****************************************************************
# Need to fetch RPMS insecurely before install with EMC networks *
#*****************************************************************
# This changes often, thats what it seems like atleast, need to monitor change.
yum install -y --nogpgcheck https://download.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
wget --no-check-certificate ftp://ftp.muug.mb.ca/mirror/fedora/epel/7/x86_64/d/dkms-2.2.0.3-30.git.7c3e7c5.el7.noarch.rpm
yum localinstall -y --nogpgcheck dkms-2.2.0.3-30.git.7c3e7c5.el7.noarch.rpm
#wget --no-check-certificate ftp://ftp.muug.mb.ca/mirror/centos/7.0.1406/os/x86_64/Packages/kernel-devel-3.10.0-123.el7.x86_64.rpm
yum install -y --nogpgcheck /vagrant/rpms/kernel-devel-3.10.0-123.el7.x86_64.rpm
#wget --no-check-certificate ftp://ftp.muug.mb.ca/mirror/centos/7.0.1406/os/x86_64/Packages/kernel-headers-3.10.0-123.el7.x86_64.rpm
yum install -y --nogpgcheck /vagrant/rpms/kernel-headers-3.10.0-123.el7.x86_64.rpm
yum localinstall -y --nogpgcheck http://archive.zfsonlinux.org/epel/zfs-release.el7.noarch.rpm
yum install -y zfs

#**************************************
# Below works outside of EMC Firewall *
#**************************************
# This changes often, thats what it seems like atleast, need to monitor change.
#yum install -y --nogpgcheck https://download.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
#yum localinstall -y --nogpgcheck ftp://rpmfind.net/linux/epel/7/x86_64/d/dkms-2.2.0.3-30.git.7c3e7c5.el7.noarch.rpm
#yum install -y --nogpgcheck ftp://mirror.switch.ch/pool/4/mirror/scientificlinux/7.0/x86_64/os/Packages/kernel-devel-3.10.0-123.el7.x86_64.rpm
#yum install -y --nogpgcheck ftp://mirror.switch.ch/pool/4/mirror/scientificlinux/7.0/x86_64/os/Packages/kernel-headers-3.10.0-123.el7.x86_64.rpm
#yum localinstall -y --nogpgcheck http://archive.zfsonlinux.org/epel/zfs-release.el7.noarch.rpm
#yum install -y zfs

# prepare env to install flocker
yum install -y git gcc python-devel
curl "https://bootstrap.pypa.io/get-pip.py" -o "/opt/get-pip.py"
python /opt/get-pip.py
pip install --upgrade pip
yum install -y git

# create zfs pool
mkdir -p /opt/flocker
truncate --size 10G /opt/flocker/pool-vdev
zpool create flocker /opt/flocker/pool-vdev

