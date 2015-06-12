#!/bin/bash
# Copyright 2015 EMC Corporation

# Use like this, sudo sh unmap_volumes.sh <volume_id> <volume_id> ...+

for i; do
   scli --unmap_volume_from_sdc --volume_id $i --all_sdcs --i_am_sure
done
