#!/bin/bash

# Update time from internet
sudo /etc/init.d/ntp stop
sudo timeout 300s sntp -s 24.56.178.140

if (($? == 124)); then
  printf "updating time timed out after 5 minutes"
fi

sudo /etc/init.d/ntp start
