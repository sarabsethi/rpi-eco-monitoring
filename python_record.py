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

# set a global name for a common logging for functions using this module
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

Utility
* clean_dirs(wdir, udir) # cleans out trash in wdir and udir
"""


def configure_sensor(sensor_config):

    """
    Get a sensor from the sensor config settings
    Args:
        sensor_config: Path to the sensor configuration file
    Returns:
        An instance of a sensor class.
    """

    # Get a reference to the Sensor class
    sensor_type = sensor_config['sensor_type']
    try:
        sensor_class = getattr(sensors, sensor_type)
        logging.info('Sensor type {} being configured.'.format(sensor_type))
    except AttributeError:
        logging.critical('Sensor type {} not found.'.format(sensor_type))
        sys.exit()

    # get a configured instance of the sensor
    # TODO - not sure of exception classes here?
    try:
        sensor = sensor_class(sensor_config)
        logging.info('Sensor config succeeded.'.format(sensor_type))
    except ValueError as e:
        logging.critical('Sensor config failed.'.format(sensor_type))
        raise e

    # If it passes config, does it pass setup.
    if sensor.setup():
        logging.info('Sensor setup succeeded')
    else:
        logging.critical('Sensor setup failed.')
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
    logging.info('Capturing data from sensor')
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

    logging.info('SIGINT detected, shutting down')
    # set the event to signal threads
    raise StopMonitoring


class StopMonitoring(Exception):
    """
    This is a custom exception that gets thrown by the exit handler
    when SIGINT is detected. It allows a loop within a try/except block
    to break out and set the event to shutdown cleanly
    """
    
    pass


def ftp_server_sync(sync_interval, ftp_config, upload_dir, die):

    """
    Function to synchronize the upload data folder with the FTP server

    Parameters:
        sync_interval: The time interval between synchronisation connections
        ftp_config: A dictionary holding the FTP configuration
        upload_dir: The upload directory to synchronise (top level, not the device specific subdirectory)
        die: A threading event to terminate the ftp server sync
    """

    # Build ftp string from configured details
    if ftp_config['use_ftps']:
        ftp_config['protocol'] = 'ftps'
    else:
        ftp_config['protocol'] = 'ftp'

    ftp_string = '{protocol}://{uname}:{pword}@{host}'.format(**ftp_config)

    # keep running while the die is not set
    while not die.is_set():

        start = time.time()

        # Update time from internet
        logging.info('Updating time from internet before ftp sync')
        subprocess.call('bash ./bash_update_time.sh', shell=True)

        logging.info('Started FTP sync at {}'.format(datetime.now()))
        subprocess.call('bash ./ftp_upload.sh {} {}'.format(ftp_string, upload_dir), shell=True)
        logging.info('Finished FTP sync at {}'.format(datetime.now()))

        # wait until the next sync interval
        wait = sync_interval - (time.time() - start)
        while wait < 0:
            wait += sync_interval
        logging.info('Waiting {} secs to next sync'.format(wait))
        time.sleep(wait)


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


def continuous_recording(sensor, working_dir, upload_dir, die):

    """
    Runs a loop over the sensor sampling process
    Args:
        sensor: A instance of one of the sensor classes
        working_dir: Path to the working directory for recording
        upload_dir: Path to the final directory used to upload processed files
        die: A threading event to terminate the ftp server sync
    """

    # Start recording
    while not die.is_set():

        record_sensor(sensor, working_dir, upload_dir, sleep=True)


def record(config_file, logfile_name, log_dir='logs'):

    """
    Function to setup, run and log continuous sampling from the sensor.

    Args:
        config_file: The JSON config file to use to set up.
        logfile_name: The filename that the logs from this run should be stored to
        log_dir: A directory to be used for logging. Existing log files
        found in will be moved to upload.
    """

    # Start logging immediately. The log_dir can't be included in config
    # because we're not loading config until after logging has started.

    # Create the logs directory and file if needed
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    logfile = os.path.join(log_dir,logfile_name)
    if not os.path.exists(logfile):
        open(logfile, 'w+')

    # Add handlers to logging so logs are sent to stdout and the file
    logging.getLogger().setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    logging.getLogger().addHandler(ch)
    hdlr = logging.FileHandler(filename=logfile)
    logging.getLogger().addHandler(hdlr)

    # Load the cpu_serial from environment variable
    try:
        cpu_serial = os.environ['PI_ID']
    except KeyError:
        logging.error('No environment variable set for cpu_serial')
        cpu_serial = 'CPU_SERIAL_ERROR'

    start_time = datetime.now().strftime("%Y%m%d_%H%M")

    logging.info('Start of continuous sampling: {}'.format(start_time))

    # Log current git commit information
    p = subprocess.Popen(['git', 'log', '-1', '--format="%H"'], stdout=subprocess.PIPE)
    (stdout, _) = p.communicate()
    logging.info('Current git commit hash: {}'.format(stdout.strip()))

    # Load the config file
    try:
        config = json.load(open(config_file))
        logging.info('Config file found')
    except IOError:
        logging.critical('Config file not found')
        sys.exit()

    try:
        ftp_config = config['ftp']
        sensor_config = config['sensor']
        offline_mode = config['offline_mode']
        working_dir = config['sys']['working_dir']
        upload_dir = config['sys']['upload_dir']
        reboot_time = config['sys']['reboot_time']
        logging.info('Config loaded')
    except KeyError:
        logging.info('Failed to load config')
        sys.exit()

    # Schedule restart at reboot time, running in a separate process
    logging.info('Scheduling restart for {}'.format(reboot_time))
    cmd = '(sudo shutdown -c && shutdown -r {}) &'.format(reboot_time)
    subprocess.call(cmd, shell=True)

    # Check working directory
    if os.path.exists(working_dir) and os.path.isdir(working_dir):
        logging.info('Using {} as working directory'.format(working_dir))
    else:
        try:
            os.makedirs(working_dir)
            logging.info('Created {} as working directory'.format(working_dir))
        except OSError:
            logging.critical('Could not create {} as working directory'.format(working_dir))
            sys.exit()

    # Check for / create an upload directory with a specific folder for
    # output from this raspberry pi.
    upload_dir = os.path.join(upload_dir)
    upload_dir_pi = os.path.join(upload_dir, 'live_data', cpu_serial)
    if os.path.exists(upload_dir_pi) and os.path.isdir(upload_dir_pi):
        logging.info('Using {} as upload directory'.format(upload_dir_pi))
    else:
        try:
            os.makedirs(upload_dir_pi)
            logging.info('Created {} as upload directory'.format(upload_dir_pi))
        except OSError:
            logging.critical('Could not create {} as upload directory'.format(upload_dir_pi))
            sys.exit()

    # Clean directories
    clean_dirs(working_dir,upload_dir)

    # move any existing logs into the upload folder for this pi
    try:
        upload_dir_logs = os.path.join(upload_dir_pi, 'logs')
        if not os.path.exists(upload_dir_logs):
            os.makedirs(upload_dir_logs)

        existing_logs = [f for f in os.listdir(log_dir) if f.endswith('.log') and f != logfile_name]
        for log in existing_logs:
            os.rename(os.path.join(log_dir, log),
                      os.path.join(upload_dir_logs, log))
            logging.info('Moved {} to upload'.format(log))
    except OSError:
        # not critical - can leave logs in the log_dir
        logging.error('Could not move existing logs to upload.')

    # Now get the sensor
    sensor = configure_sensor(sensor_config)

    # Set up the threads to run and an event handler to allow them to be shutdown cleanly
    die = threading.Event()
    signal.signal(signal.SIGINT, exit_handler)
    
    if not offline_mode:
        sync_thread = threading.Thread(target=ftp_server_sync, args=(sensor.server_sync_interval,
                                                                     ftp_config, upload_dir, die))
    
    record_thread = threading.Thread(target=continuous_recording, args=(sensor, working_dir,
                                                                    upload_dir_pi, die))

    # Initialise background thread to do remote sync of the root upload directory
    # Failure here does not preclude data capture and might be temporary so log
    # errors but don't exit.
    try:
        # start the recorder
        logging.info('Starting continuous recording at {}'.format(datetime.now()))
        record_thread.start()
        
        if offline_mode:
            logging.info('Running in offline mode - no FTP synchronisation')
        else:
            # wait a while to allow make the two threads run out of sync
            time.sleep(sensor.server_sync_interval/2)
            # start the FTP sync
            sync_thread.start()
            logging.info('Starting FTP server sync every {} seconds at {}'.format(sensor.server_sync_interval, datetime.now()))
        
        # now run a loop that will continue with a small grain until
        # an interrupt arrives, this is necessary to keep the program live
        # and listening for interrupts
        while True:
            time.sleep(1)
    except StopMonitoring:
        # We've had an interrupt signal, so tell the threads to shutdown,
        # wait for them to finish and then exit the program
        die.set()
        record_thread.join()
        if not offline_mode:
            sync_thread.join()
        
        logging.info('Recording and sync shutdown, exiting at {}'.format(datetime.now()))


if __name__ == "__main__":

    # run record with three arguements - the path to the config file, the log directory and the log
    record(sys.argv[1], sys.argv[2], sys.argv[3])
