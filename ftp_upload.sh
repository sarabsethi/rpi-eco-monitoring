#!/bin/bash

if [ ! -d ./continuous_monitoring_data ]; then
	exit 1
fi

source ftp_server_details.sh

lftp -c "set ftp:list-options -a;
set ssl-force on;
set passive-mode on;
set ssl:verify-certificate no;
set net:timeout 300;
set net:max-retries 3;
set net:reconnect-interval-base 5;
set net:reconnect-interval-multiplier 2;
open $ftp_string;
lcd ./continuous_monitoring_data/;
cd ./continuous_monitoring_data/;
mirror --reverse --Remove-source-files --only-missing --verbose"
