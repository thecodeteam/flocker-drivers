EMC XtremIO Flocker Vagrant Enviroment
======================
This project Vagrant environment for trying EMC XtremIO Flocker intergration.

## Description
ClusterHQ/Flocker provides an efficient and easy way to connect persistent store with Docker containers. This project provides a sample vagrant environment for trying out solution.

## EMC XtremIO Flocker Intergration Block Diagram
![EMC XtremIO Flocker Intergration Block Diagram Missing] 
(https://github.com/emccorp/vagrant-xtremio-flocker/blob/master/EMCXtremIOFlocker.jpg)



## Installation
* Tested with Vagrant 1.7.2

- Clone source code from git repository
git clone https://github.com/emccorp/vagrant-xtremio-flocker.git

- Change directory
cd vagrant-xtremio-flocker

- Bring up vagrant machines
vagrant up
This shall create two ubuntu trusty64 host and install all needed iSCSI software on the host

- Check the status of nodes
vagrant status (it should print following)

Current machine states:
node1                     running (virtualbox)
node2                     running (virtualbox)

- Test login to the host
vagrant ssh node1
vagrant ssh node2
The node1 gets a preassigned ip address node1: 192.168.33.10 and node2: 192.168.33.11

- Discover iSCSI XtremIO portal on the host
vagrant ssh node1
/vagrant/Config/iSCSIDiscover <EMC XtremIO iSCSI Portal IP>
/vagrant/Config/iSCSILogin <EMC XtremIO iSCSI Portal IP>
lsssci (this should print XtremIO as one of the storage arrays)
exit
vagrant ssh node2
/vagrant/Config/iSCSIDiscover <EMC XtremIO iSCSI Portal IP>
/vagrant/Config/iSCSILogin <EMC XtremIO iSCSI Portal IP>
lsssci (this should print XtremIO as one of the storage arrays)

- Install ClusterHQ/Flocker
TBD

- Install EMC Plugin for XtremIO
TBD

## Usage Instructions
Please refer to ClusterHQ/Flocker documentation for usage. A sample deployment and application file for Cassandra server is present with this code.
- Deploying Cassandra Database on node1:
vagrant ssh node1
flocker-deploy 192.168.33.10 /vagrant/cassandra-deployment.yml /vagrant/cassandra-application.yml
The default deployment node on /vagrant/cassandra-deployment.yml is 192.168.33.10.
sudo docker ps (you should now see cassandra docker deployed)
sudo docker inspect flocker-cassandra (this shall show the volume connected, mounted as file-system on the host)

- Check status of the Cassandra node
sudo docker exec -it flocker-cassandra nodetool status (you should get output as below)
vagrant@node2-flocker:~$ sudo docker exec -it flocker--cassandra-new-1 nodetool status
Datacenter: datacenter1
=======================
Status=Up/Down
|/ State=Normal/Leaving/Joining/Moving
--  Address       Load       Tokens  Owns    Host ID                               Rack
UN  172.17.0.162  130.26 KB  256     ?       ef92d409-ee9f-4773-9ca7-bbb5df662b77  rack1

- Create sample keyspace in Cassandra database:
 * sudo docker exec -it flocker-cassandra cqlsh
 * The above shall give you a cqlsh prompt
 * Copy paste following to create database and table
 CREATE KEYSPACE EMCXtremIO WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : 0};
 CREATE TABLE EMCXtremIO.users (userid text PRIMARY KEY, first_name text, last_name text, emails set<text>, top_scores list<int>, todo map<timestamp, text>);
 
- Check the schema created
  * desc keyspace EMCXtremIO

- Migrate Cassandra database to node2:
  ClusterHQ flocker provides a way to migrate data from one node to another. The steps below migrate Cassandra from node1 to node2
  * Modify cassandra-deploy.yml file present in the root folder to specify target host at 192.168.33.11.
  * vagrant ssh node1
  * flocker-deploy /vagrant/cassandra-deploy.yml /vagrant/cassandra-application.yml
 




## Future
- Add Chap protocol support for iSCSI
- Add 

## Contribution
Create a fork of the project into your own reposity. Make all your necessary changes and create a pull request with a description on what was added or removed and details explaining the changes in lines of code. If approved, project owners will merge it.

Licensing
---------
**PLACE A COPY OF THE [APACHE LICENSE](http://emccode.github.io/sampledocs/LICENSE "LICENSE") FILE IN YOUR PROJECT**

Licensed under the Apache License, Version 2.0 (the “License”); you may not use this file except in compliance with the License. You may obtain a copy of the License at <http://www.apache.org/licenses/LICENSE-2.0>

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

Support
-------
Please file bugs and issues at the Github issues page. For more general discussions you can contact the EMC Code team at <a href="https://groups.google.com/forum/#!forum/emccode-users">Google Groups</a> or tagged with **EMC** on <a href="https://stackoverflow.com">Stackoverflow.com</a>. The code and documentation are released with no warranties or SLAs and are intended to be supported through a community driven process.
