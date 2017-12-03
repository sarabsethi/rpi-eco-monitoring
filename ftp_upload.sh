#!/bin/bash

ftp_string=$1
data_top_folder_name=$2

if [ ! -d './'$data_top_folder_name ]; then
	exit 1
fi

lftp -c "set ftp:list-options -a;
set ssl-force on;
set passive-mode on;
set ssl:verify-certificate no;
set net:timeout 300;
set net:max-retries 3;
set net:reconnect-interval-base 5;
set net:reconnect-interval-multiplier 2;
open $ftp_string;
mirror --reverse --Remove-source-files --only-missing --verbose $data_top_folder_name $data_top_folder_name"
