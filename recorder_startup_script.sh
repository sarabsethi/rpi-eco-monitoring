#!/bin/bash

printf '############################################\nStart of ecosystem monitoring startup script\n############################################\n'

# just as a back up schedule a reboot for 24 hours (in case something goes wrong before scheduling the 2am reboot)
(sudo shutdown -r +1440) &

# Restart udev to simulate hotplugging of 3G dongle
sudo service udev stop
sudo service udev start

tries=0
max_tries=30
while true; do
	timeout 2s wget -q --spider http://google.com
	if [ $? -eq 0 ]; then
		printf "Online\n"
    break
	else
	    printf "Offline\n"
	fi
	printf 'Waiting for internet connection before continuing ('$max_tries' tries max)\n'
	sleep 1
	let tries=tries+1
	if [[ $tries -eq $max_tries ]] ;then
		break
	fi
done

# Change to correct folder
cd /home/pi/rpi-eco-monitoring

# Update time from internet
sudo bash ./bash_update_time.sh

# Start ssh-agent so password not required
eval $(ssh-agent -s)

# Pull latest code from repo
last_sha=$(git rev-parse HEAD)
#git pull
git fetch origin
branch=$(git branch | sed -n -e 's/^\* \(.*\)/\1/p')
git reset --hard origin/$branch
printf 'Pulled from github\n'
now_sha=$(git rev-parse HEAD)

# Check if this file has changed - reboot if so
changed_files="$(git diff-tree -r --name-only --no-commit-id $last_sha $now_sha)"
echo "$changed_files" | grep --quiet "recorder_startup_script" && sudo reboot

# Add in current date and time to log files
currentDate=$(date +"%Y-%m-%d_%H.%M")
sed -i '1s/^/NEW BOOT TIME: '$currentDate'\n\n/' *_log.txt

# Check the config exists
config_file="./config.json"
if [ ! -f $config_file ]; then
    echo "Config file not found! Run \'python setup.py\' to generate one";
    exit 1
fi

# export the raspberry pi serial number to an environment variable
export PI_ID=$(python discover_serial.py)

# the file in which to store to store the logging from this run
logdir='logs'
logfile_name="rpi_eco_"$PI_ID"_"$currentDate".log"

# Start recording script
printf 'End of startup script\n'
sudo -E python -u python_record.py $config_file $logfile_name $logdir
