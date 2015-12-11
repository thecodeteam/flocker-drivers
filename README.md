![EMC VMAX Flocker Intergration] 
This is a plugin driver for the [Flocker](https://clusterhq.com/) project which delivers Fast, local, persistent storage for Docker containers, Multi-host container management, Database migrations, and Flexible shared storage (SAN, NAS or block) for Docker when you want it

## Description Flocker can help orchestrate and provision storage to your clustered docker container microservices applications. Use cases include --> - Seamlessly Running Stateful Microservices

        Run Databases in Containers
                MongoDB, Cassandra, Postgres, MySQL, and more!

    Generally orchestrate and schedule your container applications across a cluster that optionally provides flexible shared storage when you need it.
    Use it with [Docker Native Extensions](https://github.com/ClusterHQ/flocker-docker-plugin)

## Installation

**Tested on CentOS 7**

Make sure you have Flocker already installed. If not visit  [Install Flocker](https://docs.clusterhq.com/en/1.8.0/install/install-client.html)

**_Be sure to use /opt/flocker/bin/python as this will install the driver into the right python environment_**

Install required libraries
```bash
sudo apt-get -y install libpq-dev
```

Install using python
```bash
git clone https://github.com/emccorp/vmax-flocker-driver
cd vmax-flocker-driver/
sudo /opt/flocker/bin/python setup.py install
```

**_Be sure to use /opt/flocker/bin/pip as this will install the driver into the right python environment_**

Install using pip
```bash
git clone https://github.com/emccorp/vmax-flocker-driver
cd vmax-flocker-driver/
/opt/flocker/bin/pip install vmax-flocker-driver/
```

You can optionally verify the correct packages are installed.
```bash
 pip show emc-vmax-flocker-plugin
```
Metadata-Version: 2.0
Name: emc-vmax-flocker-plugin
Version: 1.0
Summary: EMC VMAX Backend Plugin for ClusterHQ/Flocker
Home-page: https://github.com/emccorp/vmax-flocker-driver
Author: Kevin Rodgers
Author-email: kevin@rodgersworld.com
License: Apache 2.0
Location: /opt/flocker/lib/python2.7/site-packages
Requires:


1) Install OpeniSCSI
    * Ubuntu<br>
```bash
    sudo apt-get update
    sudo apt-get -y install open-iscsi
    sudo apt-get -y install lsscsi
    sudo apt-get -y install scsitools
```
    * Centos<br>
```bash
    sudo yum -y install iscsi-initiator-utils
    sudo yum -y install lsscsi
    sudo yum -y install sg3_utils
```

2) Install redis
    * Ubuntu<br>
```bash
    sudo apt-get -y install redis-server
```
    * Centos<br>
```bash
    sudo yum -y install redis   --or--
```

3) Install EMC inq utility
```bash
    sudo wget ftp://ftp.emc.com/pub/symm3000/inquiry/v8.1.1.0/inq.LinuxAMD64 -O /usr/local/bin/inq
    sudo chmod +x /usr/local/bin/inq
```
4) Edit redis.conf and set listen address
    bind 10.10.0.XX 127.0.0.1

5) Add vmax flocker plugin to agent.yml

    "dataset":
      "backend": "emc_vmax_flocker_plugin"
      "lockdir": "/tmp"
      "database": "<your redis server IP>"
      "min_allocation": 15
      "protocol": "iSCSI"
      "hosts":
        - "host": "<short name>"
          "initiator": "iqn.1994-05.com.redhat:583d44b98a1b"
        - "host": "<short name>"
          "initiator": "iqn.1994-05.com.redhat:319a849586e9"

6) Create /etc/cinder/cinder_emc_config.xml

    <?xml version="1.0" encoding="UTF-8"?>
    <EMC>
      <EcomServerIp>10.10.0.XX</EcomServerIp>
      <EcomServerPort>5988</EcomServerPort>
      <EcomUserName>username</EcomUserName>
      <EcomPassword>password</EcomPassword>
      <PortGroups>
        <PortGroup>iSCSI_port_group</PortGroup>
      </PortGroups>
      <Array>12-Character-Symm-Id</Array>
      <Pool>Fast-Pool</Pool>
    </EMC>

7) Run trial unit tests

Set agent.yml location for test suite
```bash
export VMAX_CONFIG_FILE=/etc/flocker/agent.yml
```

Run the login test
```bash
/opt/flocker/bin/trial emc_vmax_flocker_plugin.test_emc_vmax.EMCVmaxBlockDeviceAPIImplementationTests.test_login
```

You should see the below if all was succesfull
```bash
PASSED (successes=1)
```

## Future

- Add these functions depending on necessity
  - VMAX-3 Support
  - FC SAN Support
- Clean up the code
  - Address ```#TODO``` items

## Contribution
Create a fork of the project into your own reposity. Make all your necessary changes and create a pull request with a description on what was added or removed and details explaining the changes in lines of code. If approved, project owners will merge it.

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
