# EMC VMAX Plugin for ClusterHQ/flocker

## Installation

**Tested on ubuntu 14.04**

Make sure you have Flocker already installed. If not visit  [Install Flocker](https://docs.clusterhq.com/en/1.8.0/install/install-client.html)

**_Be sure to use /opt/flocker/bin/python as this will install the driver into the right python environment_**

Install OpenStack Cinder
```bash
git clone -b stable/liberty https://github.com/openstack/cinder.git
sudo /opt/flocker/bin/pip install ./cinder/
```

Install VMAX Flocker plugin
```bash
git clone https://github.com/emccode/flocker-drivers
sudo /opt/flocker/bin/pip install ./flocker-drivers/vmax/
```

You can optionally verify the correct packages are installed.
```bash
 /opt/flocker/bin/pip show emc-vmax-flocker-plugin
---
Metadata-Version: 1.1
Name: emc-vmax-flocker-plugin
Version: 0.9.1
Summary: EMC VMAX Backend Plugin for ClusterHQ/Flocker 
Home-page: https://github.com/emccode/flocker-drivers/vmax
Author: Kevin Rodgers
Author-email: kevin.rodgers@emc.com
License: Apache 2.0
Location: /opt/flocker/lib/python2.7/site-packages
Requires: bitmath, eliot, oslo.concurrency, oslo.config, oslo.i18n, oslo.serialization, oslo.utils, pywbem, redis, testtools, Twisted, zope.interface
```

1) Install OpeniSCSI and other required libraries<br>
On Ubuntu
```bash
sudo apt-get update
sudo apt-get -y install open-iscsi scsitools lsscsi
sudo apt-get -y install libpq-dev
```
On Centos
```bash
sudo yum -y install iscsi-initiator-utils lsscsi sg3_utils
sudo yum -y install libpqxx-devel
```

2) Install redis<br>
On Ubuntu
```bash
sudo apt-get -y install redis-server
```
On Centos
```bash
sudo yum -y install redis
```

3) Install EMC inq utility
```bash
sudo wget \
    ftp://ftp.emc.com/pub/symm3000/inquiry/v8.1.1.0/inq.LinuxAMD64 \
    -O /usr/local/bin/inq
sudo chmod +x /usr/local/bin/inq
```
4) Edit redis.conf and set listen (bind) address<br>
    bind <host-ip-address> 127.0.0.1 or simply bind *

5) Add vmax flocker plugin to agent.yml

    "dataset":
      "backend": "emc_vmax_flocker_plugin"
      "config_file": "/etc/flocker/vmax3.conf"
      "database": "<your redis server IP>"
      "protocol": "iSCSI"
      "hosts":
        - "host": "<short name>"
          "initiator": "iqn.1994-05.com.redhat:583d44b98a1b"
        - "host": "<short name>"
          "initiator": "iqn.1994-05.com.redhat:319a849586e9"
      "profiles":
        - "name": "gold"
          "backend": "GOLD"
        - "name": "silver"
          "backend": "SILVER"
        - "name": "bronze"
          "backend": "BRONZE"

6) Create VMAX config_file (/etc/flocker/vmax3.conf)

    [DEFAULT]
    lock_path=/var/lib/flocker
    use_syslog=True
    use_stderr=False
    debug=False
    syslog_log_facility=LOG_LOCAL3
    log_dir=/var/lib/flocker
    log_level=INFO
    enabled_backends=GOLD.SILVER.BRONZE

    #
    # VMAX-3 GOLD type that uses VMAX iSCSI Driver
    #
    [GOLD]
    volume_driver=cinder.volume.drivers.emc.emc_vmax_iscsi.EMCVMAXISCSIDriver
    cinder_emc_config_file=/etc/flocker/cinder_emc_config_ISCSI_GOLD.xml
    volume_backend_name=GOLD_BE

    #
    # VMAX-3 SILVER type that uses VMAX iSCSI Driver
    #
    [SILVER]
    volume_driver=cinder.volume.drivers.emc.emc_vmax_iscsi.EMCVMAXISCSIDriver
    cinder_emc_config_file=/etc/flocker/cinder_emc_config_ISCSI_SILVER.xml
    volume_backend_name=SILVER_BE

    #
    # VMAX-3 BRONZE type that uses VMAX iSCSI Driver
    #
    [BRONZE]
    volume_driver=cinder.volume.drivers.emc.emc_vmax_iscsi.EMCVMAXISCSIDriver
    cinder_emc_config_file=/etc/flocker/cinder_emc_config_ISCSI_BRONZE.xml
    volume_backend_name=BRONZE_BE

7) Create cinder_emc_config_file files specified in VMAX configuration file (cinder_emc_config_ISCSI_BRONZE.xml)

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

8) Run trial unit tests

Set agent.yml location for test suite
```bash
export VMAX_CONFIG_FILE=/etc/flocker/agent.yml
```

Run the login test
```bash
/opt/flocker/bin/trial \
    emc_vmax_flocker_plugin.test_emc_vmax.EMCVmaxBlockDeviceAPIImplementationTests.test_login
```

You should see the below if all was successful
```bash
PASSED (successes=1)
```


## Future
- Add these functions depending on necessity
  - FC SAN Support
- Clean up the code
  - Address ```#TODO``` items

## Contribution
Create a fork of the project into your own repository. Make all your necessary changes and create a pull request with a description on what was added or removed and details explaining the changes in lines of code. If approved, project owners will merge it.

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
