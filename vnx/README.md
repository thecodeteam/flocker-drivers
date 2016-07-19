# EMC VNX Plugin for ClusterHQ/flocker

## Installation

**Tested on ubuntu 14.04**

Make sure you have Flocker already installed. If not, visit [Install Flocker](https://docs.clusterhq.com/en/1.8.0/install/install-client.html)

**_Be sure to use /opt/flocker/bin/python as this will install the driver into the right python environment_**

Install VNX Flocker plugin
```bash
git clone https://github.com/emccode/flocker-drivers
sudo /opt/flocker/bin/pip install ./flocker-drivers/vnx
```

You can optionally verify the correct packages are installed.
```bash
/opt/flocker/bin/pip show emc-vnx-flocker-plugin
------------------------------------------------
Metadata-Version: 1.1
Name: emc-vnx-flocker-plugin
Version: 0.1
Summary: EMC VNX Plugin for ClusterHQ/Flocker
Home-page: https://github.com/emccode/flocker-drivers/vnx
Author: Jay Xu
Author-email: jay.xu@emc.com
License: Apache 2.0
Location: /opt/flocker/lib/python2.7/site-packages
Requires: bitmath, eliot, eventlet, monotonic, pyrsistent, retrying, six, storops, Twisted, zope.interface
```

1) Multipath setup
Enabling multi-path volume access is recommended for robust data access. The major configuration includes
On Ubuntu
```bash
sudo apt-get update
sudo apt-get -y install multipath-tools sysfsutils utils 
```
On RedHat
```bash
sudo yum -y install device-mapper-multipath sysfsutils sg3_utils
```

For multipath-tools, here is an EMC recommended sample of /etc/multipath.conf
```
blacklist {
        # Skip the files under /dev that are definitely not FC/iSCSI devices
        # Different system may need different customization
        devnode "^(ram|raw|loop|fd|md|dm-|sr|scd|st)[0-9]*"
        devnode "^hd[a-z][0-9]*"
        devnode "^cciss!c[0-9]d[0-9]*[p[0-9]*]"

        # Skip LUNZ device from VNX
        device {
            vendor "DGC"
            product "LUNZ"
            }
    }

    defaults {
        user_friendly_names no
        flush_on_last_del yes
    }

    devices {
        # Device attributed for EMC CLARiiON and VNX series ALUA
        device {
            vendor "DGC"
            product ".*"
            product_blacklist "LUNZ"
            path_grouping_policy group_by_prio
            path_selector "round-robin 0"
            path_checker emc_clariion
            features "1 queue_if_no_path"
            hardware_handler "1 alua"
            prio alua
            failback immediate
        }
    }
```

2) Add VNX flocker plugin to agent.yml

    "dataset":
      "backend": "emc_vnx_flocker_plugin"
      "ip": IP address of VNX storage
      "user": User name to login VNX storage
      "password": Password to login VNX storage
      "navicli_path": NaviSecCli absolute path
      "navicli_security_file": Path for NaviSecCli security file
      "storage_pools"": Storage pool names which split with the comma
      "multipath": True to enable multipath. By default, multipath is enabled.
      "proto": iSCSI or FC. The default protocol is iSCSI.
      "host_ip": IP address of Flocker agent Node. 
__Note:__
     
* The option `navicli_path`, `navicli_security_file`, `storage_pools`, `multipath`, `proto` and `host_ip` are optional.    
* `host_ip` is used for iSCSI initiator auto-registration. Otherwise the user has to register initiator manually.

3) Run trial unit tests

Set agent.yml location for test suite
```bash
export VNX_CONFIG_FILE=/etc/flocker/agent.yml
```

Run the test
```bash
/opt/flocker/bin/trial emc_vnx_flocker_plugin.test_emc_vnx.test_plugin
```

You should see the below if all was successful
```bash
PASSED (successes=1)
```


## Contribution
Create a fork of the project into your own repository. Make all your necessary changes and create a pull request with a description on what was added or removed and details explaining the changes in lines of code. If approved, project owners will merge it.

Licensing
---------
**EMC will not provide legal guidance on which open source license should be used in projects. We do expect that all projects and contributions will have a valid open source license, or align to the appropriate license for the project/contribution.** 

Copyright [2016] [EMC Corporation]

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
Please file bugs and issues at the Github issues page. For more general discussions you can contact the Flocker team at <a href="https://groups.google.com/forum/#!forum/flocker-users"> Google Groups</a> or tagged with **EMC** on <a href="https://stackoverflow.com">Stackoverflow.com</a>. The code and documentation are released with no warranties or SLAs and are intended to be supported through a community driven process. 