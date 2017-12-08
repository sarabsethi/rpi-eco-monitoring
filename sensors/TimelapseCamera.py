import datetime
import subprocess
import os

class TimelapseCamera(object):

    def __init__(self, wdir, udir, config=None):

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

        defaults = self.config()
        defaults = {var['name']: var['default'] for var in defaults}

        if config is not None and 'capture_delay' in config:
            try:
                self.capture_delay = float(config['capture_delay'])
            except ValueError:
                print("Invalid capture delay in sensor config ({}), using default."
                      " ".format(config['capture_delay']))
                self.capture_delay = defaults['capture_delay']
        else:
            self.capture_delay = defaults['capture_delay']

        # set internal variables and required class variables
        self.current_file = None
        self.wdir = wdir
        self.udir = udir
        self.server_sync_interval = self.capture_delay

    @staticmethod
    def config():
        """
        Static method defining the config options and defaults for the sensor class
        """
        return [{'name': 'capture_delay',
                 'type': float,
                 'default': 86400,
                 'prompt': 'What is the interval in seconds between images'}
                ]

    def capture_data(self):
        """
        Method to capture an image.
        """

        # Name files by capture day and time
        self.current_file = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        # Record for a specific duration
        print('\n{} - Started capture\n'.format(self.current_file))
        ofile = os.path.join(self.wdir, self.current_file)

        # Name images by capture time
        if os.path.exists('/dev/video0'):
            print('\nTaking picture - smile!\n')
            res = '2592x1944'
            # Delay and skip some frames to make sure exposure is adjusted to lighting
            cmd = 'fswebcam -D 5 -S 20 -p YUYV -r {} {}'
            subprocess.call(cmd.format(res, ofile + '.jpg'), shell=True)
        else:
            print('No camera detected')
            open(ofile + '_ERROR_no-camera-detected', 'a').close()

    def postprocess(self):
        pass

    def cleanup(self):
        pass

    def sleep(self):
        """
        Method to pause between data capture
        """
        time.sleep(self.capture_delay)
