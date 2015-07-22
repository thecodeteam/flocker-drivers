scaleio-flocker
---------------

![Alt text](/examples/flocker-scaleio-TestEnv.png?raw=true "Environment Diagram")

# Description

This Vagrant environment and Vagrantfile helps create a three-VM EMC ScaleIO lab setup, with Flocker built from source, on CentOS 7

# Usage

- **Tested with Vagrant 1.7.2**
- **Tested with CentOS 7**
- Scripts have been maunually run on a 3 node Amazon AWS cluster runing CentOS 7 AMI as well, though this is not automated in the current repo with ```--provider``` flag

Get the source
```
git clone https://github.com/emccorp/vagrant-scaleio-flocker

cd vagrant-scaleio-flocker
```

Copy the RPMS into the source directory
[You can download ScaleIO Here](http://www.emc.com/products-solutions/trial-software-download/scaleio.htm)
```
cp EMC-ScaleIO-callhome-1.31-243.0.el7.x86_64.rpm E MC-ScaleIO-sdc-1.31-243.0.el7.x86_64.rpm
EMC-ScaleIO-gateway-1.31-243.0.noarch.rpm  EMC-ScaleIO-sds-1.31-243.0.el7.x86_64.rpm
EMC-ScaleIO-gui-1.31-243.0.noarch.rpm  EMC-ScaleIO-tb-1.31-243.0.el7.x86_64.rpm
EMC-ScaleIO-lia-1.31-243.0.el7.x86_64.rpm EMC-ScaleIO-mdm-1.31-243.0.el7.x86_64.rpm
```

Copy the certs (if needed) into source/certs
```
cp CompanySSL.crt CompanyCA.crt certs/
```

# Start vagrant
**Note, this takes a while to install, because we're installing a new kernel and ZFS, hopefully we'll be able to use custom boxes to streamline this in the near future**
```
vagrant up
```

# Examples

Your 3 Nodes containing ScaleIO + Flocker will be on a private address space
in virtualbox. The example at the time of running this used vboxnet1 192.168.50.1/24

The plugin (https://github.com/emccorp/scaleio-flocker-driver) should come installed in this
environment, as well as cluster certificates and services started. 

Services that need to be started are
- (all nodes) **flocker-dataset-agent**
- (all nodes) **flocker-container-agent**
- (at least on one node) **flocker-control**

```
version: 1
control-service:
  hostname: "control-service"
dataset:
  backend: "scaleio_flocker_driver"
  username: "admin"
  password: "Scaleio123"
  mdm: "192.168.50.12"
  protection_domain: "pdomain"
  ssl: True
```

Here is a fig file (mongo-application.yml) (you can find this in this repo as well under ./examples)

```
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

```
"version": 1
"nodes":
 "192.168.50.11": ["mongodbserver", "mongodbconn"]
 "192.168.50.12": []
 "192.168.50.13": []
```

Run the example
```
flocker-deploy mongo-deployment-1node.yml mongo-application.yml 
```

**You should be able to see the volumes on the node (tb == 192.168.50.11)**
```
[root@tb flocker-emc]# /bin/emc/scaleio/drv_cfg --query_vols
Retrieved 1 volume(s)
VOL-ID aea92e8700000000 MDM-ID 62a34bc20b360b1c
```

You should be able go to a web browser 192.168.50.11:8080 and see the app is connected to MongoDB 

![Alt text](/examples/connected.png?raw=true)

Also view the containers on the node (Image shows 192.168.50.11)

![Alt text](/examples/bothcontainers.png?raw=true)

Here is a deployment file (mongo-deployment-2node.yml)

```
"version": 1
"nodes":
 "192.168.50.11": ["mongodbconn"]
 "192.168.50.12": ["mongodbserver"]
 "192.168.50.13": []
```

Run the example to move the app
```
flocker-deploy mongo-deployment-2node.yml mongo-application.yml 
```

You should be able go to a web browser 192.168.50.11:8080 and see the app is NOT connected to MongoDB while MongoDB is moving, this is temporary, you may look at the log to see the connection status for ```flocker--mongodbconn```

![Alt text](/examples/cannot_connect.png?raw=true)

You should see 1 container on each host after the ```mongodbserver``` is migrated.

(Image shows 192.168.50.11)

![Alt text](/examples/mongoconnonly.png?raw=true)

(Image shows 192.168.50.12)

![Alt text](/examples/mongodbonly.png?raw=true)

After the mongodbserver is succesfully migrated, You should be able go to a web browser 192.168.50.11:8080 and see the app is again connected to MongoDB.

You should also see the volume has moved to the new host.

**You should be able to see the volumes on the node (mdm1 == 192.168.50.12)**
```
[root@mdm1 flocker-emc]# /bin/emc/scaleio/drv_cfg --query_vols
Retrieved 1 volume(s)
VOL-ID aea92e8700000000 MDM-ID 62a34bc20b360b1c
```

# Cluster

Each node in the cluster will house the ScaleIO tooling, SDC/SDS for
volume access, Docker and Flocker in the above example, you can see this
sshing into any node and follow the below

```
vagrant ssh <tb|mdm1|mdm2>

```

```
[vagrant@tb ~]$ sudo docker ps
CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS               NAMES
```

```
[vagrant@tb ~]$ sudo zpool status
  pool: flocker
 state: ONLINE
  scan: none requested
config:

	NAME                      STATE     READ WRITE CKSUM
	flocker                   ONLINE       0     0     0
	  /opt/flocker/pool-vdev  ONLINE       0     0     0

errors: No known data errors

[vagrant@tb ~]$ sudo zpool list
NAME      SIZE  ALLOC   FREE    CAP  DEDUP  HEALTH  ALTROOT
flocker  9.94G   124K  9.94G     0%  1.00x  ONLINE  -

```

Show ScaleIO Cluster Information

```
[vagrant@tb ~]$ sudo /bin/emc/scaleio/drv_cfg --query_vols
Retrieved 1 volume(s)
VOL-ID 2f93fa7700000000 MDM-ID 4267f11a3b9d8194

[vagrant@tb ~]$  exit
you@yourmachine:~ vagrant ssh mdm1
[vagrant@mdm1 ~]$ sudo scli --login --username admin --password Scaleio123
Logged in. User role is Administrator. System ID is 4267f11a3b9d8194
[vagrant@mdm1 ~]$ sudo scli --queary_all
System Info:
	Product:  EMC ScaleIO Version: R1_31.243.0
	ID:      4267f11a3b9d8194

License info:
	Installation ID: 32228409739fd8c3
	SWID: 
	Maximum capacity: Unlimited
	Usage time left: 30 days (Initial License)
	Enterprise features: Enabled
	The system was activated 0 days ago

System settings:
	Volumes are not obfuscated by default
	Capacity alert thresholds: High: 80, Critical: 90
	Thick volume reservation percent: 0
	MDM restricted SDC mode: disabled

Query all returned 1 Protection Domain:
Protection Domain pdomain (Id: ed5448c100000000) has 1 storage pools, 0 Fault Sets, 3 SDS nodes, 1 volumes and 112.0 GB (114688 MB) available for volume allocation
Operational state is Active

Storage Pool default (Id: 92fd353300000000) has 1 volumes and 112.0 GB (114688 MB) available for volume allocation
	The number of parallel rebuild/rebalance jobs: 2
	Rebuild is enabled and using Limit-Concurrent-IO policy with the following parameters:
	 Number of concurrent IOs per device: 1
	Rebalance is enabled and using Favor-Application-IO policy with the following parameters:
	 Number of concurrent IOs per device: 1, Bandwidth limit per device: 10240 KB per second
	Zero padding is disabled
	Spare policy: 10% out of total
	Uses RAM Read Cache
	RAM Read Cache write handling mode is 'passthrough'


SDS Summary:
	Total 3 SDS Nodes
	3 SDS nodes have membership state 'Joined'
	3 SDS nodes have connection state 'Connected'
	276.4 GB (283026 MB) total capacity
	232.8 GB (238340 MB) unused capacity
	0 Bytes snapshots capacity
	16.0 GB (16384 MB) in-use capacity
	0 Bytes thin capacity
	16.0 GB (16384 MB) protected capacity
	0 Bytes failed capacity
	0 Bytes degraded-failed capacity
	0 Bytes degraded-healthy capacity
	0 Bytes unreachable-unused capacity
	0 Bytes active rebalance capacity
	0 Bytes pending rebalance capacity
	0 Bytes active fwd-rebuild capacity
	0 Bytes pending fwd-rebuild capacity
	0 Bytes active bck-rebuild capacity
	0 Bytes pending bck-rebuild capacity
	0 Bytes rebalance capacity
	0 Bytes fwd-rebuild capacity
	0 Bytes bck-rebuild capacity
	0 Bytes active moving capacity
	0 Bytes pending moving capacity
	0 Bytes total moving capacity
	27.6 GB (28302 MB) spare capacity
	16.0 GB (16384 MB) at-rest capacity
	0 Bytes decreased capacity

	Primary-reads                            0 IOPS 0 Bytes per-second
	Primary-writes                           0 IOPS 0 Bytes per-second
	Secondary-reads                          0 IOPS 0 Bytes per-second
	Secondary-writes                         0 IOPS 0 Bytes per-second
	Backward-rebuild-reads                   0 IOPS 0 Bytes per-second
	Backward-rebuild-writes                  0 IOPS 0 Bytes per-second
	Forward-rebuild-reads                    0 IOPS 0 Bytes per-second
	Forward-rebuild-writes                   0 IOPS 0 Bytes per-second
	Rebalance-reads                          0 IOPS 0 Bytes per-second
	Rebalance-writes                         0 IOPS 0 Bytes per-second

Volumes summary:
	1 thick-provisioned volume. Total size: 8.0 GB (8192 MB)
```

# Caveats

Working with vagrant's insecure private key working correctly, flocker-deploy should
not ask for a password as long as you run the below command from you CLI node

```
[ -e "${SSH_AUTH_SOCK}" ] || eval $(ssh-agent) && ssh-add ~/.vagrant.d/insecure_private_key
```

Test that this is working correctly against the tb node.
(It should response unknown because we built flocker-node from source?)
```
you@yourmachine:~ ssh root@192.168.50.11 flocker-reportstate --version
unknown
```

# Future

- Automate environment to use custom vagrant boxes to speed up deployment
- Don't install from source, rather install from official packages
- Automate certificate creation and service startup for flocker+scaleio driver

# License

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


