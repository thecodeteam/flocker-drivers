# EMC Unity Plugin for ClusterHQ/Flocker

## Installation

**Tested on ubuntu 14.04**

Make sure you have Flocker already installed. If not, visit [Install Flocker](https://docs.clusterhq.com/en/1.8.0/install/install-client.html)

**_Be sure to use /opt/flocker/bin/python as this will install the driver into the right python environment_**

Install Unity Flocker plugin
```bash
git clone https://github.com/emccode/flocker-drivers
sudo /opt/flocker/bin/pip install ./flocker-drivers/unity
```

You can optionally verify the correct packages are installed.
```bash
/opt/flocker/bin/pip show emc-unity-flocker-plugin
---
Metadata-Version: 1.1
Name: emc-unity-flocker-plugin
Version: 0.1
Summary: EMC Unity Plugin for ClusterHQ/Flocker
Home-page: https://github.com/emccode/flocker-drivers/unity
Author: Jay Xu
Author-email: jay.xu@emc.com
License: Apache 2.0
Location: /opt/flocker/lib/python2.7/site-packages
Requires: bitmath, eliot, eventlet, monotonic, pyrsistent, retrying, six, storops, Twisted, zope.interface
```

1) Multipath setup
Enabling multipath volume access is recommended for robust data access. The major configuration includes
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

2) In order to enable profile-base volume creation, please configure the pools with capability profile through Unity Unisphere GUI first.

Here is an example to create a gold pool with gold profile:
      
    * Launch 'Create Pool Wizard' 
    * Set a pool name 'gold_pool', and then click Next.
    * Select an available tier 'Extreme Performance Tier', and then click Next.
    * Click Next.
    * Enable the checkbox 'Create VMWare Capability Profile for the Pool', set a profile name 'gold_profile'. And then click Next.
    * Set the Usage Tags as 'flocker-gold', and then click Next.
    * Click Finish.
__Note:__

* The tag 'flocker_gold' is mapped to gold profile defined in ClusterHQ/Flocker. Similarly, the tag 'flocker_silver'/'flocker_bronze' are mapped to silver/bronze profile defined in ClusterHQ/Flocker. The user can create the different pools with the different tiers to map with the profiles defined in ClusterHQ
* Multiple pools could be mapped to the same capability profile and the volume will be created on the pool which has the biggest capacity. 

3) Add unity Flocker plugin to agent.yml

    "dataset":
      "backend": "emc_unity_flocker_plugin"
      "ip"": IP address of Unity
      "user"": User name to login Unity
      "password"": Password to login Unity
      "storage_pools": Storage pools to create volume
      "multipath": True to enable multipath. By default, multipath is enabled.
      "proto": iSCSI or FC. The default protocol is iSCSI.
__Note:__
     
* The option `storage_pools`, `multipath`, `proto` are optional.

4) Run trial unit tests

Set agent.yml location for test suite
```bash
export UNITY_CONFIG_FILE=/etc/flocker/agent.yml
# Optional: turn off the urllib InsecureRequestWarning
export PYTHONWARNINGS="ignore:Unverified HTTPS request"
```

Run the test
```bash
/opt/flocker/bin/trial emc_unity_flocker_plugin.test_emc_unity.test_plugin
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