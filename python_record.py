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

# set a global name for a common logger for functions using this module
LOG = 'rpi-eco-monitoring'


"""
Running the recording process uses the following functions, which users
might want to repackage in bespoke code, or which it is useful to isolate
for testing:

Sensor setup and recording
* configure_sensor(config_file) # returns a configured sensor
* record_sensor(sensor, wdir, udir, sleep=True) # initiates a single round of sampling

FTP server sync
* ftp_server_sync(ftp_config, udir) # rolling synchronisation, intended to run in thread





clean_dirs(wdir, udir) # cleans out trash in wdir and udir



"""


def configure_sensor(sensor_config):

    """
    Get a sensor from the sensor config settings
    Args:
        sensor_config: Path to the sensor configuration file
    Returns:
        An instance of a sensor class.
    """

    # start logging
    logger = logging.getLogger(LOG)

    # Get a reference to the Sensor class
    sensor_type = sensor_config['sensor_type']
    try:
        sensor_class = getattr(sensors, sensor_type)
        logger.info('Sensor type {} being configured.'.format(sensor_type))
    except AttributeError:
        logger.critical('Sensor type {} not found.'.format(sensor_type))
        sys.exit()

    # get a configured instance of the sensor
    # TODO - not sure of exception classes here?
    try:
        sensor = sensor_class(sensor_config)
        logger.info('Sensor config succeeded.'.format(sensor_type))
    except ValueError as e:
        logger.critical('Sensor config failed.'.format(sensor_type))
        raise e

    # If it passes config, does it pass setup.
    if sensor.setup():
        logger.info('Sensor setup succeeded')
    else:
        logger.critical('Sensor setup failed.')
        sys.exit()

    return sensor


def record_sensor(sensor, working_dir, upload_dir, sleep=True):

    """
    Function to run the common sensor record loop. The sleep between
    sensor recordings can be turned off
    Args:
        sensor: A sensor instance
        working_dir: The working directory to be used by the sensor
        upload_dir: The upload directory root to use for completed files
        sleep: Boolean - should the sensor sleep be used.
    """

    logger = logging.getLogger(LOG)

    # Create daily folders to hold files during this recording session
    start_date = time.strftime('%Y-%m-%d')
    session_working_dir = os.path.join(working_dir, start_date)
    session_upload_dir = os.path.join(upload_dir, start_date)

    try:
        if not os.path.exists(session_working_dir):
            os.makedirs(session_working_dir)
    except OSError:
        logging.critical('Could not create working directory for '
                         'recording: {}'.format(session_working_dir))
        sys.exit()

    try:
        if not os.path.exists(session_upload_dir):
            os.makedirs(session_upload_dir)
    except OSError:
        logging.critical('Could not create upload directory for '
                         'recording: {}'.format(session_working_dir))
        sys.exit()

    # Capture data from the sensor
    sensor.capture_data(working_dir=session_working_dir, upload_dir=session_upload_dir)

    # Postprocess the raw data in a separate thread
    postprocess_t = threading.Thread(target=sensor.postprocess)
    postprocess_t.start()

    # Let the sensor sleep
    if sleep:
        sensor.sleep()


def exit_handler(signal, frame):
    """
    Function to allow the thread loops to be shut down
    :param signal:
    :param frame:
    :return:
    """

    logger = logging.getLogger(LOG)
    logger.info('SIGINT detected, shutting down')
    # set the event to signal threads
    die.set()

def ftp_server_sync(sync_interval, ftp_config, upload_dir, die):

    """
    Function to synchronize the upload data folder with the FTP server

    Parameters:
        sync_interval: The time interval between synchronisation connections
        ftp_config: A dictionary holding the FTP configuration
        upload_dir: The upload directory to synchronise
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
        logging.INFO('Updating time from internet before ftp sync')
        subprocess.call('bash ./bash_update_time.sh', shell=True)

        logging.info('Started FTP sync')
        subprocess.call('bash ./ftp_upload.sh {} {}'.format(ftp_string, upload_dir), shell=True)
        logging.INFO('\nFinished FTP sync\n')

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

    logger = logging.getLogger(__name__)
    logger.critical('Cleaning up working directory')
    shutil.rmtree(working_dir, ignore_errors=True)

    # Remove empty directories in the upload directory, from bottom up
    for subdir, dirs, files in os.walk(upload_dir, topdown=False):
        if not os.listdir(subdir):
            logger.info('Removing empty upload directory: {}'.format(subdir))
            shutil.rmtree(subdir, ignore_errors=True)


def continuous_recording(sensor, working_dir, upload_dir):

    """
    Runs a loop over the sensor sampling process
    Args:
        config_file: Path to the sensor configuration file
        logfile: Path to the logfile to use
    """


    # Start recording
    while True:
        pass


def record(config_file, log_dir='/log'):

    """
    Function to setup, run and log continuous sampling from the sensor.

    Args:
        config_file: The JSON config file to use to set up.
        log_dir: A directory to be used for logging. Existing log files
        found in will be moved to upload.
    """

    # Get variables for the logfile. The log_dir can't be included in config
    # because we're not loading config until after logging has started.
    cpu_serial = os.getenv('PI_ID')
    start_time = datetime.now().strftime("%Y%m%d_%H%M")
    logfile = os.path.join(log_dir, 'rpi_eco_{}_{}.log'.format(cpu_serial, start_time))

    logger = logging.getLogger(LOG)
    logging.basicConfig(filename=logfile, level=logging.INFO)
    logger.info('Start of continuous sampling: {}'.format(start_time))

    # Log current git commit information
    p = subprocess.Popen(['git', 'log', '-1', '--format="%H"'], stdout=subprocess.PIPE)
    (stdout, _) = p.communicate()
    logger.info('Current git commit hash: {}'.format(stdout.strip()))

    # Load the config file
    try:
        config = json.load(open(config_file))
        logger.info('Config file found')
    except IOError:
        logger.critical('Config file not found')
        sys.exit()

    try:
        ftp_config = config['ftp']
        sensor_config = config['sensor']
        working_dir = config['sys']['working_dir']
        upload_dir = config['sys']['upload_dir']
        reboot_time = config['sys']['reboot_time']
        logger.info('Config loaded')
    except KeyError:
        logger.info('Failed to load config')
        sys.exit()

    # Check working directory
    if os.path.exists(working_dir) and os.path.isdir(working_dir):
        logger.info('Using {} as working directory'.format(working_dir))
    else:
        try:
            os.makedirs(working_dir)
            logger.info('Created {} as working directory'.format(working_dir))
        except OSError:
            logger.critical('Could not create {} as working directory'.format(working_dir))
            sys.exit()

    # Check for / create an upload directory with a specific folder for
    # output from this raspberry pi.
    upload_dir_pi = os.path.join(upload_dir, cpu_serial)
    if os.path.exists(upload_dir_pi) and os.path.isdir(upload_dir_pi):
        logger.info('Using {} as upload directory'.format(upload_dir_pi))
    else:
        try:
            os.makedirs(upload_dir_pi)
            logger.info('Created {} as upload directory'.format(upload_dir_pi))
        except OSError:
            logger.critical('Could not create {} as upload directory'.format(upload_dir_pi))
            sys.exit()

    # TODO - clean directories

    # move any existing logs into the upload folder for this pi
    try:
        upload_dir_logs = os.path.join(upload_dir_pi, 'logs')
        if not os.path.exists(upload_dir_logs):
            os.makedirs(upload_dir_logs)

        existing_logs = [f for f in os.listdir(log_dir) if f.startswith('rpi_eco_') and
                         f.endswith('.log') and f != logfile]
        for log in existing_logs:
            os.rename(os.path.join(log_dir, log),
                      os.path.join(upload_dir_logs, log))
            logger.info('Moved {} to upload'.format(log))
    except OSError:
        # not critical - can leave logs in the log_dir
        logger.error('Could not move existing logs to upload.')

    # Now get the sensor
    sensor = configure_sensor(sensor_config)

    # Create a threading event to pass termination events to threads
    # and an event handler to set the event.
    die = threading.Event()
    signal.signal(signal.SIGINT, exit_handler)

    # Schedule restart at reboot time, running in a separate process
    logger.info('Scheduling restart for {}'.format(reboot_time))
    cmd = '(sudo shutdown -c && sudo shutdown -r {}) &'.format(reboot_time)
    subprocess.call(cmd, shell=True)

    # Initialise background thread to do remote sync of the root upload directory
    # Failure here does not preclude data capture and might be temporary so log
    # errors but don't exit.
    try:
        sync_thread = threading.Thread(target=ftp_server_sync, args=(sensor.server_sync_interval,
                                                                     ftp_config, upload_dir, die))
        sync_thread.start()
        logger.info('Starting server sync every {} seconds'.format(sensor.server_sync_interval))
    except:
        logger.error('Failed to start server sync, data will still be collected')



if __name__ == "__main__":

    # simply run  continuous sampling using the config file and
    record(sys.argv[1], sys.argv[2])
