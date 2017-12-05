import os
import time
import subprocess
import shutil
import signal
from datetime import datetime
import json
from pprint import pprint

print('Start of recording script...')

# Print current git commit information
print('Current git commit info:')
subprocess.call('git log -1',shell=True)

# Print current system time
print('System time is {}'.format(datetime.now()))

# Make sure in the correct dir (so paths all make sense)
dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir_path)

# Schedule restart at 2am (does in separate process)
print('Scheduling restart for 2am')
subprocess.call('(sudo shutdown -c && sudo shutdown -r 02:00) &',shell=True)

# Clear the temporary files
working_folder = './tmp_data'
def cleanup_tempfiles():
    print('Cleaning up temporary files')
    shutil.rmtree(working_folder, ignore_errors=True)

# Clean up when script is exited
user_quit = False
def exit_handler(signal, frame):
    print('On my way out!')
    user_quit = True
    cleanup_tempfiles()
    sensor.cleanup()
    os._exit(0)

# Setup exit handler
signal.signal(signal.SIGINT, exit_handler)

# Extract Raspberry Pi serial from cpuinfo file
def getserial():
    cpuserial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo','r')
        for line in f:
             if line[0:6]=='Serial':
                cpuserial = line[10:26]
        f.close()
    except:
        cpuserial = "ERROR000000000"
    return cpuserial

# Sync local files with remote server
def server_sync_loop(sync_interval,ftp_details,data_top_folder_name):
    # Build ftp string from configured details
    if ftp_details['use_ftps']:
        start = 'ftps://'
    else:
        start = 'ftp://'
    ftp_string = '{}{}:{}@{}'.format(start,ftp_details['username'],ftp_details['password'],ftp_details['hostname'])

    # Sleep for half interval so server sync is out of phase with the data capturing
    time.sleep(sync_interval/2)

    while 1:
        # Update time from internet
        print('\nUpdating time from internet before ftp sync')
        subprocess.call('bash ./bash_update_time.sh',shell=True)

        print('\nStarted FTP sync\n')
        subprocess.call('bash ./ftp_upload.sh {} {}'.format(ftp_string,data_top_folder_name), shell=True)
        print('\nFinished FTP sync\n')

        # Check if user has quit
        if user_quit==True:
            break

        # Perform next sync out of phase with data capturing (accounting for the time taken to perform last upload)
        sync_t = latest_start_t + (sync_interval/2)
        wait_t = sync_t - time.time()
        while wait_t < 0:
            wait_t += sync_interval

        print('\nWaiting {} secs to next sync\n'.format(wait_t))
        time.sleep(wait_t)

# Set final folder to hold recorded files waiting to be synced
serial = getserial()
data_top_folder_name = 'continuous_monitoring_data'
final_folder = './{}/RPiID-{}'.format(data_top_folder_name,serial)

# Remove any temporary files left behind
cleanup_tempfiles()

###############################
# Edit this below part when you have implemented a new sensor type

# Sensor classes
from USBSoundcardMic import *
from TimelapseCamera import *

# Read config file and initialise appropriate sensor
config = json.load(open('config.json'))

opts = config['sensor']['options']
delay_between_captures = opts['delay_between_captures']
print('delay_between_captures {}'.format(delay_between_captures))
server_sync_interval = delay_between_captures

# Do specific sensor initialisation
if config['sensor']['type'].lower() == 'USBSoundcardMic'.lower():
    sensor = USBSoundcardMic(opts['record_length'],opts['compress_data'])
    # For audio, sync timings should depend on recorded file length
    server_sync_interval += opts['record_length']
    print('Using USBSoundcardMic sensor')
elif config['sensor']['type'].lower() == 'TimelapseCamera'.lower():
    sensor = TimelapseCamera()
    print('Using TimelapseCamera sensor')
else:
    print('MAJOR ERROR: sensor type {} not found. Run \'python setup.py\' to fix config file'.format(config['sensor']['type']))
    exit()

###############################

# Remove empty directories that may be left behind, from bottom up
for subdir, dirs, files in os.walk(final_folder,topdown=False):
    if not os.listdir(subdir):
        print('removing empty directory: {}'.format(subdir))
        shutil.rmtree(subdir, ignore_errors=True)

# Initialise background thread to do remote sync
sync_thread = Thread(target=server_sync_loop, args=(server_sync_interval,config['ftp'],data_top_folder_name,))
sync_thread.start()

while 1:
    # Record start time so we know to time sync halfway through
    latest_start_t = time.time()

    # Folders to hold files
    startDate = time.strftime('%Y-%m-%d')
    temp_day_folder = '{}/{}'.format(working_folder,startDate)
    final_day_folder = '{}/{}'.format(final_folder,startDate)
    if not os.path.exists(temp_day_folder):
        os.makedirs(temp_day_folder)
    if not os.path.exists(final_day_folder):
        os.makedirs(final_day_folder)

    # Capture data from the sensor
    raw_data_fname,final_fname_no_ext = sensor.capture_data(temp_day_folder,final_day_folder)

    # Postprocess the raw data in a separate thread
    postprocess_t = Thread(target=sensor.postprocess, args=(raw_data_fname,final_fname_no_ext,))
    postprocess_t.start()


    time.sleep(delay_between_captures)
