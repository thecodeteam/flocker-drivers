#!/bin/bash

# **For this to work, all volumes, but the default volume should be removed**
# This script was used to recover from the cluster saying "not enough thin capacity"

# Remove default volume
ssh root@192.168.50.12 scli --unmap_volume_from_sdc --volume_name vol1 --all_sdcs --i_am_sure
ssh root@192.168.50.12 scli --remove_volume --volume_name vol1 --i_am_sure

# Remove
ssh root@192.168.50.12 scli --remove_sds --sds_ip 192.168.50.11 
ssh root@192.168.50.12 scli --remove_sds --sds_ip 192.168.50.12
ssh root@192.168.50.12 scli --remove_sds --sds_ip 192.168.50.13

# Replenish the SDS devices
ssh root@192.168.50.11 rm -rf /home/vagrant/scaleio2
ssh root@192.168.50.11 truncate -s 200GB /home/vagrant/scaleio3
ssh root@192.168.50.12 rm -rf /home/vagrant/scaleio2
ssh root@192.168.50.12 truncate -s 200GB /home/vagrant/scaleio3
ssh root@192.168.50.13 rm -rf /home/vagrant/scaleio2
ssh root@192.168.50.13 truncate -s 200GB /home/vagrant/scaleio3

# Re-add the SDS's
ssh root@192.168.50.12 scli --add_sds --sds_ip 192.168.50.13 --device_path /home/vagrant/scaleio2 --sds_name sds3 --protection_domain_name pdomain
ssh root@192.168.50.12 scli --add_sds --sds_ip 192.168.50.12 --device_path /home/vagrant/scaleio2 --sds_name sds2 --protection_domain_name pdomain
ssh root@192.168.50.12 scli --add_sds --sds_ip 192.168.50.11 --device_path /home/vagrant/scaleio2 --sds_name sds1 --protection_domain_name pdomain

