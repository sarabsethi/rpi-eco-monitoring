import json
import os
import readline

# Process user input and return value
def process_input(prompt,current_val):
    user_input = raw_input("{} (blank = {}): ".format(prompt,current_val))
    if user_input.lower() is 'y':
        user_input = True
    elif user_input.lower() is 'n':
        user_input = False
    elif user_input is '':
        user_input = current_val

    # If value is numerical convert to float
    try:
        user_input = float(user_input)
    except ValueError:
        pass

    return user_input

# merge two dicts, b values take priority where there are clashes
def merge_dicts(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

# Setup default config values
audio_opts_default = {'delay_between_captures':0,'record_length':1200,'compress_data':1}
timelapse_opts_default = {'delay_between_captures':1800}
config_default = {'sensor':{'type':'USBSoundcardMic','options':audio_opts_default},'ftp':{'username':'user','password':'pass','hostname':'host','use_ftps':1}}

# Load current config values from file if previously setup
config_file = 'config.json'
if os.path.exists(config_file):
    config_from_file = json.load(open(config_file))

    # Replace the default config vals with those in the file
    config = merge_dicts(config_default,config_from_file)
else:
    config = config_default

print('Hello! Follow these instructions to perform a one-off set up of your ecosystem monitoring unit\n')

print('First lets do the sensor setup...')
valid_sensor = False
initial_sensor_type = config['sensor']['type']

###############################
# Edit this below part when you have implemented a new sensor type
available_sensor_types = ['USBSoundcardMic','TimelapseCamera']
while not valid_sensor:
    config['sensor']['type'] = process_input('Which type of sensor are you using? Options are {} '.format(available_sensor_types),config['sensor']['type'])
    if config['sensor']['type'].lower() == 'USBSoundcardMic'.lower():
        valid_sensor = True
        config['sensor']['options']['record_length'] = process_input('Length in secs of each recorded audio file',config['sensor']['options']['record_length'])
        config['sensor']['options']['compress_data'] = process_input('Compress audio data to mp3 format before uploading? 1 or 0',config['sensor']['options']['compress_data'])
        config['sensor']['options']['delay_between_captures'] = process_input('Delay in secs between audio recordings',config['sensor']['options']['delay_between_captures'])

    elif config['sensor']['type'].lower() == 'TimelapseCamera'.lower():
        valid_sensor = True
        config['sensor']['options'] = timelapse_opts_default
        config['sensor']['options']['delay_between_captures'] = process_input('Delay between image captures',config['sensor']['options']['delay_between_captures'])
    else:
        print('Sorry \'{}\' is not a valid sensor type'.format(config['sensor']['type']))
        config['sensor']['type'] = initial_sensor_type

###############################


print('\nNow let\'s do the FTP server details...')
config['ftp']['username'] = process_input('FTP server username',config['ftp']['username'])
config['ftp']['password'] = process_input('FTP server password',config['ftp']['password'])
config['ftp']['hostname'] = process_input('FTP server hostname',config['ftp']['hostname'])
config['ftp']['use_ftps'] = process_input('Use FTPS or FTP? 1 for FTPS, 0 for FTP',config['ftp']['use_ftps'])

with open(config_file, 'w') as fp:
    json.dump(config, fp, indent=4)

print('\nAll done!')
