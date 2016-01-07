EMC XtremIO Flocker Vagrant Enviroment
======================
This project Vagrant environment for trying EMC XtremIO Flocker intergration.

## Description
ClusterHQ/Flocker provides an efficient and easy way to connect persistent store with Docker containers. This project provides a sample vagrant environment for trying out solution.
## EMC XtremIO Flocker Intergration Block Diagram
![EMC XtremIO Flocker Intergration Block Diagram Missing]
(https://github.com/emccode/flocker-drivers/blob/master/demo/xtremio/EMCXtremIOFlocker.jpg)
## Installation
Tested with Vagrant 1.7.2
- Clone source code from git repository
```bash
    git clone https://github.com/emccode/flocker-drivers.git
```
- Change directory
```bash
    cd flocker-drivers/demo/xtremio
```
- Bring up vagrant machines
```bash
   vagrant up
```
This shall create two ubuntu trusty64 host and install all needed iSCSI software on the host
- Test login to the host<br>
```bash
    vagrant ssh node1
    vagrant ssh node2
```
The nodes get preassigned ip addresses 192.168.33.10 for node1 and 192.168.33.11 for node2
- Discover iSCSI XtremIO portal on the host on node1 and node2
```bash
        /vagrant/Config/iSCSIDiscover <EMC XtremIO iSCSI Portal IP>
        /vagrant/Config/iSCSILogin <EMC XtremIO iSCSI Portal IP>
        lsssci
```
- Install ClusterHQ/Flocker<br>
 Refer to ubuntu install notes -> https://docs.clusterhq.com/
- Install EMC Plugin for XtremIO
    * Clone EMX XtremIO Flocker Plugin in the same directory as vagrant images
  ```bash
        git clone https://github.com/emccode/flocker-drivers
  ```
    * Run plugin install on two nodes - node1 and node2
  ```bash
        cd /vagrant/flocker-drivers/xtremio
        sudo python setup.py install
  ```
- Enable Plugin<br>
    To start the plugin on a node, a configuration file must exist on the node at /etc/flocker/agent.yml. This should be     as follows, replacing ${xms_ip}, ${xms_user} & ${xms_password} with the ip/hostname, username and password of XtremIO XMS port:<br><br>
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
## Usage Instructions
Please refer to ClusterHQ/Flocker documentation for usage. <br>

A sample deployment and application file for Cassandra server is present with this code.<br>
- Deploying Cassandra Database on node1
```bash
    vagrant ssh node1
    flocker-deploy 192.168.33.10 /vagrant/cassandra-deployment.yml /vagrant/cassandra-application.yml
```
The default deployment node on /vagrant/cassandra-deployment.yml is 192.168.33.10.
```bash
    sudo docker ps (you should now see cassandra docker deployed)
    sudo docker inspect flocker--cassandra
```
The above shall show the volume connected, mounted as file-system on the host
- Check status of the Cassandra node
```bash
    sudo docker exec -it flocker--cassandra nodetool status (you should get output as below)
    sudo docker exec -it flocker--cassandra nodetool status
```
- Create sample keyspace in Cassandra database:
```bash
    sudo docker exec -it flocker--cassandra cqlsh
```

The above gives you a cqlsh prompt. Copy paste following to create database and table

```bash
    CREATE KEYSPACE EMCXtremIO WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : 0};
    CREATE TABLE EMCXtremIO.users (userid text PRIMARY KEY, first_name text);
```
- Check the created schema
```bash
    desc keyspace EMCXtremIO
```
- Migrate Cassandra database to node2<br>
  ClusterHQ flocker provides a way to migrate data from one node to another
    * Modify cassandra-deploy.yml file present in the root folder to specify target host at 192.168.33.11.
```bash
    vagrant ssh node1
    flocker-deploy /vagrant/cassandra-deploy.yml /vagrant/cassandra-application.yml
    sudo docker exec -it flocker--cassandra cqlsh
    desc keyspace EMCXtremIO
```
- Protecting Cassandra Node with Docker<br>
  EMC XtremIO comes Snapshotting capabilities which can be extended to Docker Cassandra for supporting application consistent snapshots
```bash
    sudo docker exec -it flocker-cassandra nodetool snapshot
```
EMC XtremIO Snapshots using XtremIOSnap: https://github.com/evanbattle/XtremIOSnap

```bash
    python ./XtremIOSnap.py ${xms ip address} ${xms_username} ${xms_password} --f --snap=${flocker cluster id}
```
Snapshot in folder with _snapshots now exists on XtremIO. The flocker cluster id can be found by referencing folder name on EMC XtremIO.
```bash
        sudo docker exec -it flocker-cassandra nodetool clearsnapshot<br>
```
## Future
- Add Chap protocol support for iSCSI
- Add Multipathning support

## Contribution
Create a fork of the project into your own reposity. Make all your necessary changes and create a pull request with a description on what was added or removed and details explaining the changes in lines of code. If approved, project owners will merge it.
