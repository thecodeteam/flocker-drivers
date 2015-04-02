scaleio-flocker
---------------

![alt tag](https://raw.github.com/wallneryan/scaleio-flocker/examples/flocker-scaleio-TestEnv.png)

# Description

Vagrantfile to create a three-VM EMC ScaleIO lab setup, with Flocker build from source, on CentOS 7

# Usage

Get the source
```
git pull https://github.com/wallnerryan/scaleio-flocker

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
   - "80:8080"
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
[vagrant@tb ~]$ 
```

```
[vagrant@tb ~]$ sudo /bin/emc/scaleio/drv_cfg --query_vols
Retrieved 0 volume(s)
```
