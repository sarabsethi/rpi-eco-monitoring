#!/bin/bash

ftp_string=$1
data_dir=$2

if [ ! -d $data_dir ]; then
	exit 1
fi

data_top_folder_name=$(basename $data_dir)

lftp -c "set ftp:list-options -a;
set ssl-force on;
set passive-mode on;
set ssl:verify-certificate no;
set net:timeout 300;
set net:max-retries 3;
set net:reconnect-interval-base 5;
set net:reconnect-interval-multiplier 2;
open $ftp_string;
mirror --reverse --Remove-source-files --only-missing --verbose $data_dir $data_top_folder_name"
