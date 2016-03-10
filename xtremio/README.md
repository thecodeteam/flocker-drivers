EMC XtremIO Flocker Plugin
======================

## EMC XtremIO Flocker Intergration Block Diagram
![EMC XtremIO Flocker Intergration Block Diagram Missing]
(https://github.com/emccode/flocker-drivers/blob/master/demo/xtremio/EMCXtremIOFlocker.jpg)
## Installation
- Install OpeniSCSI
    * Ubuntu<br>
   ```bash
    sudo apt-get update
    sudo apt-get install -y open-iscsi
    sudo apt-get install -y lsscsi
    sudo apt-get -y install scsitools
    ```
    * Centos<br>
    ```bash
    sudo yum -y install iscsi-initiator-utils
    sudo yum -y install lsscsi
    sudo yum -y install sg3_utils
    ```
- Multipathing Installation
    * Ubuntu<br>
   ```bash
    sudo modprobe dm-multipath
    cp multipath.conf /etc/multipath.conf
    systemctl start multipathd
   ```
    * Centos<br>
   ```bash
    sudo apt-get multipath-tools
    cp multipath.conf /etc/multipath.conf
   ```
- Discover iSCSI XtremIO portal on the host<br>
   ```bash
    iscsiadm -m discoverydb -t st -p ${XtremIO iSCSI Portal IP/hostname}:3260 --discover
    ```
- Login iSCSI data port<br>
   ```bash
   scsiadm -m node  -p ${XtremIO iSCSI Portal IP/hostname} --login
   ```
- Install ClusterHQ/Flocker<br>
Refer to ubuntu install notes -> https://docs.clusterhq.com/en/0.4.0/
- Install EMC Plugin for XtremIO

   ```bash
    git clone https://github.com/emccode/flocker-drivers
    cd xtremio
    sudo /opt/flocker/bin/python setup.py install
    ```

## Usage Instructions
To start the plugin on a node, a configuration file must exist on the node at /etc/flocker/agent.yml. This should be as follows, replacing ${xms_ip}, ${xms_user} & ${xms_password} with the ip/hostname, username and password of XtremIO XMS port:
```bash
control-service: {hostname: '192.168.33.10', port: 4524}
dataset: {backend: emc_xtremio_flocker_plugin}
version: 1
dataset:
backend: emc_xtremio_flocker_plugin
   xms_ip: ${xms_ip}
   xms_user: ${xms_user}
   xms_password: ${xms_password}
```
A sample vagrant environment help
Please refer to ClusterHQ/Flocker documentation for usage. A sample deployment and application can be found at https://github.com/emccode/flocker-drivers/demo/xtremio

## Future
- Add Chap protocol support for iSCSI
- Add

## Contribution
Create a fork of the project into your own reposity. Make all your necessary changes and create a pull request with a description on what was added or removed and details explaining the changes in lines of code. If approved, project owners will merge it.

## Running Tests

Sample vagrant environment can be found at: https://github.com/emccode/flocker-drivers/demo/xtremio

Setup the config file (edit values for your environment)
```bash
export XMS_CONFIG_FILE=//etc/flocker/xio_config_file.yml
vi /etc/flocker/xio_config_file.yml
XIO:
  XMS_USER: ${XMS_USERNAME}
  XMS_PASS: ${XMS_PASSWORD}
  XMS_IP: ${XMS_IP}
```
Run the tests
```bash
sudo -E trial test_emc_xtremio
```
You should see the below if all was succesfull

Licensing
---------
**EMC will not provide legal guidance on which open source license should be used in projects. We do expect that all projects and contributions will have a valid open source license, or align to the appropriate license for the project/contribution**

Copyright [2015] [EMC Corporation]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Support
-------
Please file bugs and issues at the Github issues page. For more general discussions you can contact the Flocker team at <a href="https://groups.google.com/forum/#!forum/flocker-users">Google Groups</a> or tagged with **EMC** on <a href="https://stackoverflow.com">Stackoverflow.com</a>. The code and documentation are released with no warranties or SLAs and are intended to be supported through a community driven process.
