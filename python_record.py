import os
import sys
import time
import subprocess
import shutil
import signal
import threading
from datetime import datetime
import json
import sensors
import logging


def exit_handler(signal, frame):
    """
    Function to tidy up when the record function is interrupted by SIGINT.
    :param signal:
    :param frame:
    :return:
    """
    print('On my way out!')
    die.set()
    cleanup_tempfiles()
    sensor.cleanup()
    sys.exit()


def ftp_server_sync(sync_interval, ftp_config, upload_dir, die):

    """
    Function to synchronize the upload data folder with the FTP server

    Parameters:
        sync_interval: The time interval between synchronisation connections
        ftp_config: A dictionary holding the FTP configuration
        udir: The upload directory to synchronise
        die: A threading event to terminate the ftp server sync
    """

    # Build ftp string from configured details
    if ftp_config['use_ftps']:
        ftp_config['protocol'] = 'ftps'
    else:
        ftp_config['protocol'] = 'ftp'

    ftp_string = '{protocol}://{uname}:{pword}@{host}'.format(**ftp_config)

    # Sleep for half interval so server sync is out of phase with the data capturing
    time.sleep(sync_interval/2)

    # keep running while the
    while not die.is_set():
        # Update time from internet
        logging.info('Updating time from internet before ftp sync')
        subprocess.call('bash ./bash_update_time.sh', shell=True)

        logging.info('Started FTP sync')
        subprocess.call('bash ./ftp_upload.sh {} {}'.format(ftp_string, upload_dir), shell=True)
        logging.info('\nFinished FTP sync\n')

        # Perform next sync out of phase with data capturing (accounting for the
        # time taken to perform last upload)
        sync_t = latest_start_t + (sync_interval/2)
        wait_t = sync_t - time.time()
        while wait_t < 0:
            wait_t += sync_interval

        print('\nWaiting {} secs to next sync\n'.format(wait_t))
        time.sleep(wait_t)


def clean_dirs(working_dir, upload_dir):
    """
    Function to tidy up the directory structure, any files left in the working
    directory and any directories in upload emptied by FTP mirroring

    Args
        working_dir: Path to the working directory
        upload_dir: Path to the upload directory
    """
    logging.info('Cleaning up working directory')
    shutil.rmtree(working_dir, ignore_errors=True)

    # Remove empty directories in the upload directory, from bottom up
    for subdir, dirs, files in os.walk(upload_dir, topdown=False):
        if not os.listdir(subdir):
            logging.info('Removing empty upload directory: {}'.format(subdir))
            shutil.rmtree(subdir, ignore_errors=True)


def record(config_file, logfile):

    """
    Main function to run the sensor sampling and FTP sync.
    Args:
        config_file: Path to the sensor configuration file
        logfile: Path to the logfile to use
    """

    # configure logging

    logging.basicConfig(filename=logfile, level=logging.INFO)

    stderrLogger=logging.StreamHandler()
    stderrLogger.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    logging.getLogger().addHandler(stderrLogger)

    logging.info('Start of recording')

    # Print current system time
    logging.info('System time is {}'.format(datetime.now()))

    # Print current git commit information
    logging.info('Current git commit info:')
    p = subprocess.Popen(['git', 'log', '-1'], stdout=subprocess.PIPE)
    (stdout, _) = p.communicate()
    logging.info(stdout)

    # Read the config file and get the parts
    try:
        config = json.load(open(config_file))
        ftp_config = config['ftp']
        sensor_config = config['sensor']
        sensor_type = sensor_config['sensor_type']
        working_dir = config['sys']['working_dir']
        upload_dir = config['sys']['upload_dir']
        logging.info('Configuration loaded')
    except (IOError, KeyError):
        logging.error('Failed to load config')
        sys.exit()

    # Load the cpu_serial from environment variable
    try:
        cpu_serial = os.environ['PI_ID']
    except(KeyError):
        logging.error('No environment variable set for cpu_serial')
        cpu_serial = 'CPU_SERIAL_ERROR'

    # Check working directories
    if os.path.exists(working_dir) and os.path.isdir(working_dir):
        logging.info('Using {} as working directory'.format(working_dir))
    else:
        try:
            os.makedirs(working_dir)
            logging.info('Created {} as working directory'.format(working_dir))
        except OSError:
            logging.error('Could not create {} as working directory'.format(working_dir))
            sys.exit()

    # Check for / create an upload directory with a specific folder for
    # output from this raspberry pi.
    upload_dir_pi = os.path.join(upload_dir, cpu_serial)
    if os.path.exists(upload_dir_pi) and os.path.isdir(upload_dir_pi):
        logging.info('Using {} as upload directory'.format(upload_dir_pi))
    else:
        try:
            os.makedirs(upload_dir_pi)
            logging.info('Created {} as working directory'.format(upload_dir_pi))
        except OSError:
            logging.error('Could not create {} as working directory'.format(upload_dir_pi))
            sys.exit()

    # Get a reference to the Sensor class
    try:
        sensor_class = getattr(sensors, sensor_type)
        logging.info('Sensor type {} being configured.'.format(sensor_type))
    except AttributeError:
        logging.error('Sensor type {} not found.'.format(sensor_type))
        sys.exit()

    # get a configured instance of the sensor
    # TODO - not sure of exception classes here?
    try:
        sensor = sensor_class(sensor_config)
        logging.info('Sensor config succeeded.'.format(sensor_type))
    except ValueError as e:
        logging.error('Sensor config failed.'.format(sensor_type))
        raise e

    # If it passes config, does it pass setup.
    if sensor.setup():
        logging.info('Sensor setup succeeded')
    else:
        logging.error('Sensor setup failed.')
        sys.exit()

    # Tidy up the directories
    clean_dirs(working_dir, upload_dir)

    # Initialise background thread to do remote sync of the root upload directory
    # Failure here does not preclude data capture and might be temporary so log
    # errors but don't exit.
    try:
        die = threading.Event()
        sync_thread = threading.Thread(target=ftp_server_sync, args=(sensor.server_sync_interval,
                                                                     ftp_config, upload_dir, die))
        sync_thread.start()
        logging.info('Starting server sync every {} seconds'.format(sensor.server_sync_interval))
    except:
        logging.error('Failed to start server sync, data will still be collected')

    # Setup exit handler
    signal.signal(signal.SIGINT, exit_handler)

    # Schedule restart at 2am (does in separate process)
    logging.info('Scheduling restart for 2am')
    subprocess.call('(sudo shutdown -c && sudo shutdown -r 02:00) &', shell=True)

    # Start recording
    while True:

        # Record start time so we know to time sync halfway through
        latest_start_t = time.time()

        # Create daily folders to hold files during this recording session
        start_date = time.strftime('%Y-%m-%d')
        session_working_dir = os.path.join(working_dir, start_date)
        session_upload_dir = os.path.join(upload_dir_pi, start_date)

        if not os.path.exists(session_working_dir):
            os.makedirs(session_working_dir)

        if not os.path.exists(session_upload_dir):
            os.makedirs(session_upload_dir)

        # Capture data from the sensor
        sensor.capture_data(working_dir=session_working_dir, upload_dir=session_upload_dir)

        # Postprocess the raw data in a separate thread
        postprocess_t = threading.Thread(target=sensor.postprocess)
        postprocess_t.start()

        # Let the sensor sleep
        sensor.sleep()


if __name__ == "__main__":

    # simply run record with two arguments for the config file and
    record(sys.argv[1], sys.argv[2])
