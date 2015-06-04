# Copyright (c) 2015 -  EMC Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure(2) do |config|

  config.vm.define "node1" do |node1|
   node1.vm.box = "ubuntu/trusty64"
   node1.vm.provision :shell, path: "./Config/bootstrap.sh"
   node1.vm.provider "virtualbox" do |vb| 
	vb.customize ["modifyvm", :id, "--memory", "8192"]	
   end
   node1.vm.network "private_network", ip: "192.168.33.10"   
   node1.vm.hostname = "node1-flocker"   
  end


  config.vm.define "node2" do |node2|
   node2.vm.box = "ubuntu/trusty64"
   node2.vm.provision :shell, path: "./Config/bootstrap.sh"
   node2.vm.provider "virtualbox" do |vb| 
	vb.customize ["modifyvm", :id, "--memory", "8192"]	
   end
   node2.vm.network "private_network", ip: "192.168.33.11"   
   node2.vm.hostname = "node2-flocker"   
  end
end
