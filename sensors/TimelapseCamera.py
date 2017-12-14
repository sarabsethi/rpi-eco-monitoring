import datetime
import time
import subprocess
import os
import sensors


class TimelapseCamera(object):

    def __init__(self, config=None):

        """
        A class to take photos from a still camera

        Args:
            wdir: The path to the working directory used for file processing.
            udir: The path to the final upload directory.
            config: A dictionary loaded from a config JSON file used to replace
             the default settings of the sensor.
        """

        # Initialise the sensor config, double checking the types of values. This
        # code uses the variables named and described in the config static to set
        # defaults and override with any passed in the config file.
        opts = self.options()
        opts = {var['name']: var for var in opts}

        # config options
        self.device = sensors.set_option('device', config, opts)
        self.capture_delay = sensors.set_option('capture_delay', config, opts)

        # set internal variables and required class variables
        self.current_file = None
        self.working_dir = None
        self.upload_dir = None
        self.server_sync_interval = self.capture_delay

    @staticmethod
    def options():
        """
        Static method defining the config options and defaults for the sensor class
        """
        return [{'name': 'device',
                 'type': str,
                 'default': '/dev/video0',
                 'prompt': 'What is the device name of the camera?'},
                {'name': 'capture_delay',
                 'type': float,
                 'default': 86400,
                 'prompt': 'What is the interval in seconds between images?'}
                ]

    def setup(self):
        """
        Method to check the sensor is ready for data capture
        """

        if os.path.exists(self.device):
            pass
        else:
            raise IOError('No camera device detected at {}.'.format(self.device))

    def capture_data(self, working_dir, upload_dir):
        """
        Method to capture an image.

        Args:
            working_dir: A working directory to use for file processing
            upload_dir: The directory to write the final data file to for upload.
        """
        self.working_dir = working_dir
        self.upload_dir = upload_dir

        # Name files by capture day and time
        self.current_file = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        # Record for a specific duration
        logging.info('\n{} - Started capture\n'.format(self.current_file))
        ofile = os.path.join(self.upload_dir, self.current_file)

        # Name images by capture time
        logging.info('\nTaking picture - smile!\n')
        res = '2592x1944'

        # Delay and skip some frames to make sure exposure is adjusted to lighting
        cmd = 'fswebcam -D 5 -S 20 -p YUYV -r {} {}'
        subprocess.call(cmd.format(res, ofile + '.jpg'), shell=True)

    def postprocess(self):
        pass

    def cleanup(self):
        pass

    def sleep(self):
        """
        Method to pause between data capture
        """
        time.sleep(self.capture_delay)
