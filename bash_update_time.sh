#!/bin/bash

# Update time from internet
sudo timeout 300s ntpdate ntp.ubuntu.com

if (($? == 124)); then
  printf "updating time timed out after 5 minutes"
fi

sudo /etc/init.d/ntp start
