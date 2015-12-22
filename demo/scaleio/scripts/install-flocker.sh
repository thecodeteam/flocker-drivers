#!/bin/bash
# Copyright 2015 EMC Corporation

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
# Flocker ports
firewall-cmd --permanent --zone=public --add-port=4523/tcp
firewall-cmd --permanent --zone=public --add-port=4524/tcp

firewall-cmd --reload

# Add mdm (gateway) node to /etc/hosts
if [ "$HOSTNAME" = tb.scaleio.local ]; then
  sed -i '/::1/d' /etc/hosts
  sed -i -e 's/127.0.0.1/192.168.50.11/g' /etc/hosts
  echo "192.168.50.12  mdm1.scaleio.local mdm1" >> /etc/hosts
  echo "192.168.50.13  mdm2.scaleio.local mdm2" >> /etc/hosts
fi

if [ "$HOSTNAME" = mdm1.scaleio.local ]; then
  echo "192.168.50.11  tb.scaleio.local tb" >> /etc/hosts
  echo "192.168.50.13  mdm2.scaleio.local mdm2" >> /etc/hosts
fi

if [ "$HOSTNAME" = mdm2.scaleio.local ]; then
  echo "192.168.50.11  tb.scaleio.local tb" >> /etc/hosts
  echo "192.168.50.12  mdm1.scaleio.local mdm1" >> /etc/hosts
fi

# Prepare Flocker (flocker creates this as well I think)
mkdir /etc/flocker
chmod 0700 /etc/flocker

# Get
FLOCKERVERSION="1.0.0"
mkdir /opt/flocker
cd /opt/flocker
mkdir flocker-$FLOCKERVERSION
cd flocker-$FLOCKERVERSION/
wget -nv https://clusterhq-archive.s3.amazonaws.com/python/Flocker-$FLOCKERVERSION-py2-none-any.whl

# Installs Flocker
yum -yy install epel-release openssl openssl-devel libffi-devel python-virtualenv libyaml clibyaml-devel
yum install -yy sshpass


#Flocker Node
wget https://clusterhq-archive.s3.amazonaws.com/centos/clusterhq-release.el7.centos.noarch.rpm
yum install -yy clusterhq-release.el7.centos.noarch.rpm
yum install -yy clusterhq-flocker-node


if [ "$HOSTNAME" = tb.scaleio.local ]; then
  echo 'y' | cp /vagrant/files/flocker-control.service /usr/lib/systemd/system/
  systemctl enable flocker-control
fi
echo 'y' | cp /vagrant/files/flocker-container-agent.service /usr/lib/systemd/system/
echo 'y' | cp /vagrant/files/flocker-dataset-agent.service /usr/lib/systemd/system/
systemctl enable flocker-dataset-agent
systemctl enable flocker-container-agent

# Flocker CLI
virtualenv --python=/usr/bin/python2.7 flocker-cli
/opt/flocker/flocker-$FLOCKERVERSION/flocker-cli/bin/pip install --upgrade pip
/opt/flocker/flocker-$FLOCKERVERSION/flocker-cli/bin/pip install /opt/flocker/flocker-$FLOCKERVERSION/Flocker-$FLOCKERVERSION-py2-none-any.whl

# Constants for where code lives
SIO_PLUGIN="https://github.com/emccode/flocker-drivers"
# Clone in ScaleIO Plugin
cd /opt/flocker/
/usr/bin/git clone $SIO_PLUGIN

# Install ScaleIO Driver
cd /opt/flocker/flocker-drivers/scaleio
/opt/flocker/bin/python setup.py install

# Configure Agent YML
cp /etc/flocker/example_sio_agent.yml /etc/flocker/agent.yml
sed -i  's/^  hostname\: \"control-service\"/  hostname\: \"tb.scaleio.local\"/g' /etc/flocker/agent.yml
sed -i  's/^  mdm\: \"192.168.100.1\"/  mdm\: \"mdm1.scaleio.local\"/g' /etc/flocker/agent.yml

# Create certs
cd /etc/flocker/
if [ "$HOSTNAME" = tb.scaleio.local ]; then
    printf '%s\n' "on the tb host"
    /opt/flocker/flocker-$FLOCKERVERSION/flocker-cli/bin/flocker-ca initialize mycluster
    /opt/flocker/flocker-$FLOCKERVERSION/flocker-cli/bin/flocker-ca create-control-certificate tb.scaleio.local
    cp control-tb.scaleio.local.crt /etc/flocker/control-service.crt
    cp control-tb.scaleio.local.key /etc/flocker/control-service.key
    # cluster.crt is created here already
    #cp cluster.crt /etc/flocker/cluster.crt
    chmod 0600 /etc/flocker/control-service.key

    # We have three nodes in the cluster.
    /opt/flocker/flocker-$FLOCKERVERSION/flocker-cli/bin/flocker-ca create-node-certificate
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.crt' | xargs -I {} cp {} /etc/flocker/node1.crt
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.key' | xargs -I {} cp {} /etc/flocker/node1.key
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.crt' | xargs rm
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.key' | xargs rm


    /opt/flocker/flocker-$FLOCKERVERSION/flocker-cli/bin/flocker-ca create-node-certificate
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.crt' | xargs -I {} cp {} /etc/flocker/node2.crt
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.key' | xargs -I {} cp {} /etc/flocker/node2.key
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.crt' | xargs rm
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.key' | xargs rm


    /opt/flocker/flocker-$FLOCKERVERSION/flocker-cli/bin/flocker-ca create-node-certificate
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.crt' | xargs -I {} cp {} /etc/flocker/node3.crt
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.key' | xargs -I {} cp {} /etc/flocker/node3.key
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.crt' | xargs rm
    ls -1 . | egrep '[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?-[A-Za-z0-9]*?.key' | xargs rm
fi

# Create User and API certs
# Create an API certificate for the plugin
if [ "$HOSTNAME" = mdm1.scaleio.local ]; then
    sshpass -p 'vagrant'  scp -o StrictHostKeyChecking=no root@tb:/etc/flocker/cluster.* /etc/flocker/
fi
if [ "$HOSTNAME" = mdm2.scaleio.local ]; then
    sshpass -p 'vagrant'  scp -o StrictHostKeyChecking=no root@tb:/etc/flocker/cluster.* /etc/flocker/
fi

if [ "$HOSTNAME" = tb.scaleio.local ]; then
    # Run flocker-ca for plugin/user
    /opt/flocker/flocker-$FLOCKERVERSION/flocker-cli/bin/flocker-ca create-api-certificate plugin

    # Create a general purpose user api cert
    /opt/flocker/flocker-$FLOCKERVERSION/flocker-cli/bin/flocker-ca create-api-certificate vagrantuser
fi

# Docker needs to reload iptables after this.
service docker restart

#Install flocker-docker-pluginc
yum -y install gcc
yum install -y python-pip build-essential

# Install CLI Tools and Flocker Docker Plugin into its own virtual environment
# due to treq and twisted overlapping dependencies
virtualenv --python=/usr/bin/python2.7 /opt/flocker/flocker-$FLOCKERVERSION/flocker-tools
/opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/bin/pip install --upgrade pip
/opt/flocker/flocker-$FLOCKERVERSION//flocker-tools/bin/pip install 'twisted==15.3.0'
/opt/flocker/flocker-$FLOCKERVERSION//flocker-tools/bin/pip install "treq==15.0.0"
/opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/bin/pip install git+https://github.com/wallnerryan/flocker-docker-plugin.git
/opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/bin/pip install git+https://github.com/wallnerryan/unofficial-flocker-tools.git

systemctl stop docker
rm -Rf /var/lib/docker

# Do we always want the latest, or just keep 1.8-dev exp=true somewhere else.
yum install -y wget
wget -nv https://experimental.docker.com/builds/Linux/x86_64/docker-latest -O /bin/docker
chmod +x /bin/docker

sed -i 's/.*other_args=.*/OPTIONS=-s vfs -H tcp\:\/\/0.0.0.0\:4243 -H unix\:\/\/\/var\/run\/docker.sock/' /etc/sysconfig/docker
sed -i 's/.*OPTIONS=.*/OPTIONS=-s vfs -H tcp\:\/\/0.0.0.0\:4243 -H unix\:\/\/\/var\/run\/docker.sock/' /etc/sysconfig/docker


systemctl start docker

# Docker Plugin Service
if [ "$HOSTNAME" = tb.scaleio.local ]; then
    echo '[Unit]
    Description=flocker-plugin - flocker-docker-plugin job file

    [Service]
    Environment=FLOCKER_CONTROL_SERVICE_BASE_URL=https://tb.scaleio.local:4523/v1
    Environment=MY_NETWORK_IDENTITY=192.168.50.11
    ExecStart=/opt/flocker/flocker-'$FLOCKERVERSION'/flocker-tools/bin/flocker-docker-plugin

    [Install]
    WantedBy=multi-user.target' >> /etc/systemd/system/flocker-docker-plugin.service

    # rename node crt
    echo 'y' |  mv /etc/flocker/node1.crt /etc/flocker/node.crt
    echo 'y' |  mv /etc/flocker/node1.key /etc/flocker/node.key

    # rename user crt
    echo 'y' |  mv /etc/flocker/vagrantuser.crt /etc/flocker/user.crt
    echo 'y' |  mv /etc/flocker/vagrantuser.key /etc/flocker/user.key

    sed -i 's/twistd\,/\"\/opt\/flocker\/flocker-'$FLOCKERVERSION'\/flocker-tools\/bin\/twistd\"\,/' /opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/bin/flocker-docker-plugin
    echo 'y' | cp /vagrant/files/adapter.py /opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/lib/python2.7/site-packages/flockerdockerplugin/adapter.py
    echo 'y' | cp /vagrant/files/client.py /opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/lib/python2.7/site-packages/unofficial_flocker_tools/txflocker/client.py

    cd /opt/flocker/
    git clone https://github.com/wallnerryan/unofficial-flocker-tools
    # The below fix did not work as intended, leave it here as it is a reminder that GUI will
    # say "pending" on volumes that are actually attached
    #echo 'y' | cp /vagrant/files/client.py /opt/flocker/unofficial-flocker-tools/unofficial_flocker_tools/txflocker/client.py
    cd unofficial-flocker-tools/web
    docker build -t clusterhq/experimental-volumes-gui .

fi

if [ "$HOSTNAME" = mdm1.scaleio.local ]; then
    echo '[Unit]
    Description=flocker-plugin - flocker-docker-plugin job file

    [Service]
    Environment=FLOCKER_CONTROL_SERVICE_BASE_URL=https://tb.scaleio.local:4523/v1
    Environment=MY_NETWORK_IDENTITY=192.168.50.12
    ExecStart=/opt/flocker/flocker-'$FLOCKERVERSION'/flocker-tools/bin/flocker-docker-plugin

    [Install]
    WantedBy=multi-user.target' >> /etc/systemd/system/flocker-docker-plugin.service

    sed -i 's/twistd\,/\"\/opt\/flocker\/flocker-'$FLOCKERVERSION'\/flocker-tools\/bin\/twistd\"\,/' /opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/bin/flocker-docker-plugin
    echo 'y' | cp /vagrant/files/adapter.py /opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/lib/python2.7/site-packages/flockerdockerplugin/adapter.py
    echo 'y' | cp /vagrant/files/client.py /opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/lib/python2.7/site-packages/unofficial_flocker_tools/txflocker/client.py

    # Get certificates
    sshpass -p 'vagrant'  scp -o StrictHostKeyChecking=no root@tb:/etc/flocker/*.crt /etc/flocker/
    sshpass -p 'vagrant'  scp -o StrictHostKeyChecking=no root@tb:/etc/flocker/*.key /etc/flocker/

    # rename node crt
    echo 'y' |  mv /etc/flocker/node2.crt /etc/flocker/node.crt
    echo 'y' |  mv /etc/flocker/node2.key /etc/flocker/node.key
fi

if [ "$HOSTNAME" = mdm2.scaleio.local ]; then
    echo '[Unit]
    Description=flocker-plugin - flocker-docker-plugin job file

    [Service]
    Environment=FLOCKER_CONTROL_SERVICE_BASE_URL=https://tb.scaleio.local:4523/v1
    Environment=MY_NETWORK_IDENTITY=192.168.50.13
    ExecStart=/opt/flocker/flocker-'$FLOCKERVERSION'/flocker-tools/bin/flocker-docker-plugin

    [Install]
    WantedBy=multi-user.target' >> /etc/systemd/system/flocker-docker-plugin.service

    # Get certificates
    sshpass -p 'vagrant' scp -o StrictHostKeyChecking=no root@tb:/etc/flocker/*.crt /etc/flocker/
    sshpass -p 'vagrant' scp -o StrictHostKeyChecking=no root@tb:/etc/flocker/*.key /etc/flocker/

    # rename node crt
    echo 'y' |  mv /etc/flocker/node3.crt /etc/flocker/node.crt
    echo 'y' |  mv /etc/flocker/node3.key /etc/flocker/node.key

    # Start flocker servicesi

    # TB
    sshpass -p 'vagrant' ssh -o StrictHostKeyChecking=no root@tb systemctl restart flocker-control
    sshpass -p 'vagrant' ssh -o StrictHostKeyChecking=no root@tb systemctl restart flocker-container-agent
    sshpass -p 'vagrant' ssh -o StrictHostKeyChecking=no root@tb systemctl restart flocker-dataset-agent
    # Retart docker incase flocker wipes DOCKER chainc
    sshpass -p 'vagrant' ssh -o StrictHostKeyChecking=no root@tb systemctl restart docker

    # MDM1
    sshpass -p 'vagrant' ssh -o StrictHostKeyChecking=no root@mdm1 systemctl restart flocker-container-agent
    sshpass -p 'vagrant' ssh -o StrictHostKeyChecking=no root@mdm1 systemctl restart flocker-dataset-agent

    # Retart docker incase flocker wipes DOCKER chainc
    sshpass -p 'vagrant' ssh -o StrictHostKeyChecking=no root@mdm1 systemctl restart docker

    # MDM2
    systemctl restart flocker-container-agent
    systemctl restart flocker-dataset-agent

    # Retart docker incase flocker wipes DOCKER chainc
    systemctl restart docker

    # Start the flocker docker plugin on mdm2
    # this is because scaleio is setup after mdm2
    # We can start on others too.
    sed -i 's/twistd\,/\"\/opt\/flocker\/flocker-'$FLOCKERVERSION'\/flocker-tools\/bin\/twistd\"\,/' /opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/bin/flocker-docker-plugin
    echo 'y' | cp /vagrant/files/adapter.py /opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/lib/python2.7/site-packages/flockerdockerplugin/adapter.py
    echo 'y' | cp /vagrant/files/client.py /opt/flocker/flocker-$FLOCKERVERSION/flocker-tools/lib/python2.7/site-packages/unofficial_flocker_tools/txflocker/client.py
    systemctl start flocker-docker-plugin

    # Finally run the GUI
    # TODO deploy with flocker-deploy? IPTables complains because flocker manages it.
    sshpass -p vagrant ssh -o StrictHostKeyChecking=no root@tb docker run --name experimental-volumes-gui \
       -d -p 8888:80 \
       -e CONTROL_SERVICE=192.168.50.11 \
       -e USERNAME=user \
       -e CERTS_PATH=/ \
       -v /etc/flocker/user.key:/user.key \
       -v /etc/flocker/user.crt:/user.crt \
       -v /etc/flocker/cluster.crt:/cluster.crt \
       clusterhq/experimental-volumes-gui

fi

# Add insecure private key for access
mkdir /root/.ssh
touch /root/.ssh/authorized_keys
echo "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA6NF8iallvQVp22WDkTkyrtvp9eWW6A8YVr+kz4TjGYe7gHzIw+niNltGEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEDo3MlTBckFXPITAMzF8dJSIFo9D8HfdOV0IAdx4O7PtixWKn5y2hMNG0zQPyUecp4pzC6kivAIhyfHilFR61RGL+GPXQ2MWZWFYbAGjyiYJnAmCP3NOTd0jMZEnDkbUvxhMmBYSdETk1rRgm+R4LOzFUGaHqHDLKLX+FIPKcF96hrucXzcWyLbIbEgE98OHlnVYCzRdK8jlqm8tehUc9c9WhQ== vagrant insecure public key" > /root/.ssh/authorized_keys
