#!/bin/bash
yum install -y docker
sed -i 's/OPTIONS=\(.*\)/OPTIONS=\1 -H tcp:\/\/0.0.0.0:4243 -H unix:\/\/\/var\/run\/docker.sock/g' /etc/sysconfig/docker
service docker restart

# enable root login, key authentication will still need to be setup
sed -i 's/PermitRootLogin .*/PermitRootLogin yes/g' /etc/ssh/sshd_config
service sshd restart

# install zfs for flocker

# via http://zfsonlinux.org/epel.html (Doesnt work?)
#yum localinstall --nogpgcheck https://download.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
#yum localinstall --nogpgcheck http://archive.zfsonlinux.org/epel/zfs-release.el7.noarch.rpm
#yum install -y kernel-devel zfs

#KERNEL_RELEASE=`uname -r`
# This changes often, thats what it seems like atleast, need to monitor change.
yum install -y https://download.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
#yum upgrade -y
yum localinstall -y --nogpgcheck ftp://rpmfind.net/linux/epel/7/x86_64/d/dkms-2.2.0.3-30.git.7c3e7c5.el7.noarch.rpm
#yum install -y kernel-devel-$KERNEL_RELEASE kernel-headers-$KERNEL_RELEASE
#yum install -y kernel-devel kernel-headers
yum install -y ftp://mirror.switch.ch/pool/4/mirror/scientificlinux/7.0/x86_64/os/Packages/kernel-devel-3.10.0-123.el7.x86_64.rpm
yum install -y ftp://mirror.switch.ch/pool/4/mirror/scientificlinux/7.0/x86_64/os/Packages/kernel-headers-3.10.0-123.el7.x86_64.rpm
#rm -f /lib/modules/$KERNEL_RELEASE/build 
#ln -s /usr/src/kernels/$KERNEL_RELEASE.x86_64 /lib/modules/$KERNEL_RELEASE/build
yum localinstall -y --nogpgcheck http://archive.zfsonlinux.org/epel/zfs-release.el7.noarch.rpm
yum install -y zfs

# install flocker
yum install -y git gcc python-devel
curl "https://bootstrap.pypa.io/get-pip.py" -o "/opt/get-pip.py"
python /opt/get-pip.py
pip install --upgrade pip
yum install -y git
#pip install --quiet https://storage.googleapis.com/archive.clusterhq.com/downloads/flocker/Flocker-0.3.0-py2-none-any.whl

# create zfs pool
mkdir -p /opt/flocker
truncate --size 1G /opt/flocker/pool-vdev
zpool create flocker /opt/flocker/pool-vdev

