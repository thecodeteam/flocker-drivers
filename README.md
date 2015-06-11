EMC XtremIO Flocker Plugin
======================
The plugin for EMC XtremIO Flocker integration.

## Description
ClusterHQ/Flocker provides an efficient and easy way to connect persistent store with Docker containers. This project provides a plugin to provision resillient storage from EMC XtremIO.

## EMC XtremIO Flocker Intergration Block Diagram
![EMC XtremIO Flocker Intergration Block Diagram Missing] 
(https://github.com/emccorp/vagrant-xtremio-flocker/blob/master/EMCXtremIOFlocker.jpg)
## Installation
- Install OpeniSCSI 
    * Ubuntu<br>
    sudo apt-get update <br>
    sudo apt-get install -y open-iscsi<br>
    sudo apt-get install -y lsscsi<br>
    sudo apt-get -y install scsitools
    * Centos<br>
    sudo yum -y install iscsi-initiator-utils<br>
    sudo yum -y install lsscsi<br>
    sudo yum -y install sg3_utils<br>
- Discover iSCSI XtremIO portal on the host<br>
    iscsiadm -m discoverydb -t st -p ${XtremIO iSCSI Portal IP/hostname}:3260 --discover
- Login iSCSI data port<br> 
scsiadm -m node  -p ${XtremIO iSCSI Portal IP/hostname} --login
- Install ClusterHQ/Flocker<br>
Refer to ubuntu install notes -> https://docs.clusterhq.com/en/0.4.0/
- Install EMC Plugin for XtremIO<br>
    * git clone https://github.com/emccorp/xtremio-flocker-driver
    * sudo python setup.py install

## Usage Instructions
To start the plugin on a node, a configuration file must exist on the node at /etc/flocker/agent.yml. This should be as follows, replacing ${xms_ip}, ${xms_user} & ${xms_password} with the ip/hostname, username and password of XtremIO XMS port:
control-service: {hostname: '192.168.33.10', port: 4524}<br>
dataset: {backend: emc_xtremio_flocker_plugin} <br>
version: 1 <br>
dataset: <br>
backend: emc_xtremio_flocker_plugin <br> 
xms_ip: ${xms_ip} <br>
xms_user: ${xms_user} <br> 
xms_password: ${xms_password} <br>

A sample vagrant environment help 
Please refer to ClusterHQ/Flocker documentation for usage. A sample deployment and application can be found at https://github.com/emccorp/vagrant-xtremio-flocker 

## Future
- Add Chap protocol support for iSCSI
- Add 

## Contribution
Create a fork of the project into your own reposity. Make all your necessary changes and create a pull request with a description on what was added or removed and details explaining the changes in lines of code. If approved, project owners will merge it.

Support
-------
