EMC ScaleIO Plugin for ClusterHQ/flocker
======================

![EMC ScaleIO Flocker Intergration] 
(https://github.com/emccorp/vagrant-scaleio-flocker/blob/master/examples/bare-env.png)

This is a plugin driver for the [Flocker](https://clusterhq.com/) project which delivers Fast, local, persistent storage for Docker containers, Multi-host container management, Database migrations, and Flexible shared storage (SAN, NAS or block) for Docker when you want it

## Description
Flocker can help orchestrate and provision storage to your clustered docker container microservices applications. Use cases include -->
- Seamlessly Running Stateful Microservices
  - Run Databases in Containers
        - MongoDB, Cassandra, Postgres, MySQL, and more! 
- Generally orchestrate and schedule your container applications across a cluster that optionally provides flexible shared storage when you need it.
- Use it with [Docker Native Extensions](https://github.com/ClusterHQ/flocker-docker-plugin)

## Installation

**Tested on CentOS 7**

Make sure you have Flocker already installed. If not visit  [Install Flocker](https://docs.clusterhq.com/en/1.0.0/using/installing/index.html)

```bash
git clone https://github.com/emccorp/scaleio-flocker-driver
cd scaleio-flocker-driver/
sudo python setup.py install
```

You can optionally verify the correct packages are installed.
```bash
 pip list | grep -i scaleio
scaleio-flocker-driver (1.0)
ScaleIO-py (0.3.3-3)
```

Then copy the example agent.yml that was created

```bash
cp /etc/flocker/example_sio_agent.yml /etc/flocker/agent.yml
vi /etc/flocker/agent.yml
```

Change the necessary options in the yml file for you environment. A full list of available options is below

```bash
version: 1
control-service:
  hostname: "<Insert IP/Hostname of Flocker-Control Service>"
dataset:
  backend: "scaleio_flocker_driver"
  username: "<Insert ScaleIO Username>"
  password: "<Insert ScaleIO gateway User Password>"
  mdm: "<Insert Scaleio Gateway MDM's IP Address>"
  protection_domain: "<Protection Domain>" (Defaults to "default") 
  storage_pool: "<Storage Pool>" (Defaults to "default")
  certificate: "</path/to/cert>" (Unsupported Right now)
  ssl: <True | False> (Defaults to True)
  debug: "<Debug LEVEL>" (Where LEVEL = DEBUG | CRITICAL, WARNING, FATAL, etc)
```

## Running Tests

Setup the config file (edit values for your environment)
```bash
export SCALEIO_CONFIG_FILE="/etc/flocker/scaleio_test.config"
vi /etc/flocker/scaleio_test.config
```

Run the tests
```bash
trial scaleio_flocker_driver.test_emc_sio
```

You should see the below if all was succesfull
```bash
PASSED (successes=28)
```

Make sure you [Install Flocker-Node](https://docs.clusterhq.com/en/0.4.0/gettingstarted/index.html#flocker-node) on every node you want the driver to run on, then make sure flocker services are running before using the CLI examples below.

## Usage Instructions

For detailed environment on how to run this, go see the [ScaleIO + Flocker Vagrant Environment](https://github.com/wallnerryan/scaleio-flocker)

Here is a fig file (mongo-application.yml) (you can find this in this repo as well under ./examples)

```bash
"version": 1
"applications":
  "mongodbserver":
    "image": "clusterhq/mongodb"
    "volume":
      "mountpoint": "/data/db"
      "maximum_size": "8589934592"
    "ports":
    - "internal": 27017
      "external": 27017
  "mongodbconn":
    "image": "wallnerryan/mongoconn"
    "ports":
    - "internal": 8080
      "external": 8080
```

Here is a deployment file (mongo-deployment-1node.yml)

```bash
"version": 1
"nodes":
 "192.168.50.11": ["mongodbserver", "mongodbconn"]
 "192.168.50.12": []
 "192.168.50.13": []
```

Run the example
```bash
flocker-deploy mongo-deployment-1node.yml mongo-application.yml 
```

**You should be able to see the volumes on the node (tb == 192.168.50.11)**
```bash
[root@flocker-node]# /bin/emc/scaleio/drv_cfg --query_vols
Retrieved 1 volume(s)
VOL-ID aea92e8700000000 MDM-ID 62a34bc20b360b1c
```

You should be able go to a web browser 192.168.50.11:8080 and see the app is connected to MongoDB 

Also view the containers on the node (Image shows 192.168.50.11)

Here is a deployment file (mongo-deployment-2node.yml)

```bash
"version": 1
"nodes":
 "192.168.50.11": ["mongodbconn"]
 "192.168.50.12": ["mongodbserver"]
 "192.168.50.13": []
```

Run the example to move the app
```bash
flocker-deploy mongo-deployment-2node.yml mongo-application.yml 
```

You should be able go to a web browser 192.168.50.11:8080 and see the app is NOT connected to MongoDB while MongoDB is moving, this is temporary, you may look at the log to see the connection status for ```flocker--mongodbconn```

You should see 1 container on each host after the ```mongodbserver``` is migrated.

After the mongodbserver is succesfully migrated, You should be able go to a web browser 192.168.50.11:8080 and see the app is again connected to MongoDB.

You should also see the volume has moved to the new host.

**You should be able to see the volumes on the node (mdm1 == 192.168.50.12)**
```bash
[root@flocker-node]# /bin/emc/scaleio/drv_cfg --query_vols
Retrieved 1 volume(s)
VOL-ID aea92e8700000000 MDM-ID 62a34bc20b360b1c
```

## Future

- Add these functions depending on necessity
  - ScaleIO 1.30 Support
  - ~~ScaleIO 1.32 Support~~
  - Test ScaleIO 1.32 (Currently Limited Testing)
  - Certification Verification
  - Enhanced Feature sets for volume in Flocker
  - Verify Other OS's
- Clean up the code
  - Address ```#TODO``` items
  - Optimize check_login bug/work around
  - Optimize block device cleanup in test suite

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
