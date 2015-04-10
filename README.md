scaleio-flocker
---------------

![Alt text](/examples/flocker-scaleio-TestEnv.png?raw=true "Environment Diagram")

# Description

Vagrantfile to create a three-VM EMC ScaleIO lab setup, with Flocker build from source, on CentOS 7

# Usage

*Tested with Vagrant 1.7.2

Get the source
```
git clone https://github.com/wallnerryan/scaleio-flocker

cd scaleio-flocker
```

Copy the RPMS into the source directory
```
cp EMC-ScaleIO-callhome-1.31-243.0.el7.x86_64.rpm E MC-ScaleIO-sdc-1.31-243.0.el7.x86_64.rpm
EMC-ScaleIO-gateway-1.31-243.0.noarch.rpm  EMC-ScaleIO-sds-1.31-243.0.el7.x86_64.rpm
EMC-ScaleIO-gui-1.31-243.0.noarch.rpm  EMC-ScaleIO-tb-1.31-243.0.el7.x86_64.rpm
EMC-ScaleIO-lia-1.31-243.0.el7.x86_64.rpm EMC-ScaleIO-mdm-1.31-243.0.el7.x86_64.rpm
```

Copy the certs (if needed) into source/certs
```
cp EMCSSL.crt EMCCA.crt certs/
```

# Start vagrant
```
vagrant up
```

# Tested

With CentOS 7, ZFS, and Flocker Public Git Source


# Examples

Your 3 Nodes containing ScaleIO + Flocker will be on a private address space
in virtualbox. The example at the time of running this used vboxnet1 192.168.50.1/24

Here is a fig file (fig.yml)

```
web:
  image: clusterhq/flask
  links:
   - "redis:redis"
  ports:
   - "80:80"
redis:
  image: dockerfile/redis
  ports:
   - "6379:6379"
  volumes: ["/data"]
```

Here is a deployment file (deployment-node1.yml)

```
"version": 1
"nodes":
  "192.168.50.11": ["web", "redis"]
  "192.168.50.12": []
  "192.168.50.13": []
```

Run the example
```
flocker-deploy deployment-node1.yml fig.yml
```

Here is a deployment file (deployment-node3.yml)

```
"version": 1
"nodes":
  "192.168.50.11": ["web"]
  "192.168.50.12": []
  "192.168.50.13": ["redis"]
```

Run the example to move the app
```
flocker-deploy deployment-node3.yml fig.yml
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

# REST API

We can test the Gateway REST API for scaleio in this environment as well. Follow
the below instructions to do so.

Get the rest api test source and enter the directory

```
git clone https://git.lss.emc.com/scm/floc/scaleio-rest.git
cd scaleio-rest
```

Next, set the IP of mdm1 to an environment var
then we need to run a login, then thet tests

```
export SERVERIP="192.168.50.12"
python test/login.py 
INFO:rest_tests:ScaleIO request: https://192.168.50.12:443/api/login
INFO:urllib3.connectionpool:Starting new HTTPS connection (1): 192.168.50.12
INFO:rest_tests:Login response: "YWRtaW46MTQyNzk5NzMyMTY3MDplYjEzZTZkOGYyZTBkZmQ2N2Y1YmEwMGMyZWIwYWFmNw"

Now run: export SCALEIOPASS="YWRtaW46MTQyNzk5NzMyMTY3MDplYjEzZTZkOGYyZTBkZmQ2N2Y1YmEwMGMyZWIwYWFmNw"

```

As it says, export the new password

```
export SCALEIOPASS="YWRtaW46MTQyNzk5NzMyMTY3MDplYjEzZTZkOGYyZTBkZmQ2N2Y1YmEwMGMyZWIwYWFmNw"
```

Now we can run the tests

```
python test/get_volumes.py | python -m json.tool
INFO:rest_tests:ScaleIO request: https://192.168.50.12:443/api/types/Volume/instances/
INFO:urllib3.connectionpool:Starting new HTTPS connection (1): 192.168.50.12
[
    {
        "ancestorVolumeId": null,
        "consistencyGroupId": null,
        "creationTime": 1427961975,
        "id": "2f93fa7700000000",
        "isObfuscated": false,
        "links": [
            {
                "href": "/api/instances/Volume::2f93fa7700000000",
                "rel": "self"
            },
            {
                "href": "/api/instances/Volume::2f93fa7700000000/relationships/Statistics",
                "rel": "/api/Volume/relationship/Statistics"
            },
            {
                "href": "/api/instances/VTree::db168d6300000000",
                "rel": "/api/parent/relationship/vtreeId"
            },
            {
                "href": "/api/instances/StoragePool::92fd353300000000",
                "rel": "/api/parent/relationship/storagePoolId"
            }
        ],
        "mappedScsiInitiatorInfo": null,
        "mappedSdcInfo": [
            {
                "limitBwInMbps": 0,
                "limitIops": 0,
                "sdcId": "3c7a7c8b00000000",
                "sdcIp": "192.168.50.11"
            },
            {
                "limitBwInMbps": 0,
                "limitIops": 0,
                "sdcId": "3c7a7c8d00000002",
                "sdcIp": "192.168.50.13"
            },
            {
                "limitBwInMbps": 0,
                "limitIops": 0,
                "sdcId": "3c7a7c8c00000001",
                "sdcIp": "192.168.50.12"
            }
        ],
        "mappingToAllSdcsEnabled": false,
        "name": "vol1",
        "sizeInKb": 8388608,
        "storagePoolId": "92fd353300000000",
        "useRmcache": true,
        "volumeType": "ThickProvisioned",
        "vtreeId": "db168d6300000000"
    }
]
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
