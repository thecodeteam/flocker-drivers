#!/bin/bash

# Use like this sudo sh rm_volumes.sh <volume_id> <volume_id> ...+

for i; do
   scli --remove_volume --volume_id $i --i_am_sure
done
