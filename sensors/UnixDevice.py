import uuid
import time
import os
import subprocess
import sensors

class UnixDevice(object):
    """
    Sensor class for using getting data from a unix device. This is a simple class
    for testing the code architecture on any unix like operating system and as a
    template for other sensors.
    """

    def __init__(self, config=None):
        """
        Init method for the sensor class, taking the contents of the config
        options and using that to populate the Sensor specific settings. This
        method should just handle setting config options and any checking of
        resources needed to capture data should be in the setup() method.

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
        self.sample_size = sensors.set_option('sample_size', config, opts)
        self.sample_rate = sensors.set_option('sample_rate', config, opts)
        self.total_samples = sensors.set_option('total_samples', config, opts)
        self.capture_delay = sensors.set_option('capture_delay', config, opts)

        # starting values for other class variables
        self.start_time = None
        self.uncompressed_file = None
        self.working_dir = None
        self.upload_dir = None
        self.server_sync_interval = 3600

    @staticmethod
    def options():
        """
        Simple static method defining the config options and defaults. The use of a list
        here is to provide a static order in which the options are set using the configuration
        setup.py script.
        """

        return [{'name': 'device',
                 'default': '/dev/urandom',
                 'type': str,
                 'prompt': 'Which unix device should be sampled?'},
                {'name': 'sample_size',
                 'default': 16,
                 'type': int,
                 'prompt': 'How many bytes should be read?'},
                {'name': 'sample_rate',
                 'default': 10,
                 'type': int,
                 'prompt': 'How many seconds should elapse between samples?'},
                {'name': 'total_samples',
                 'default': 5,
                 'type': int,
                 'prompt': 'How many samples in total should be taken in a single data capture?'},
                {'name': 'capture_delay',
                 'default': 10,
                 'type': int,
                 'prompt': 'What is the delay in seconds between data captures?'}
                ]

    def setup(self):
        """
        This method is called only once when the recorder starts to make sure that the
        required resources are available. This is typically checking on command line
        resources and maybe that a device is available.

        Returns:
            A logical indicating if the Sensor setup is good to sample from.
        """
        if os.path.exists(self.device):
            return True
        else:
            raise OSError('Device {} not found'.format(self.device))

    def capture_data(self, working_dir, upload_dir):
        """
        Method to capture data from the device. This method can either create the
        final file or create an intermediate file and then hand off to the
        compress method, allowing sample to run again whilst compress is run
        in the background.

        Args:
            working_dir: A working directory to use for file processing
            upload_dir: The directory to write the final data file to for upload.
        Returns:
            Generates a completed sample file
        """

        # set the working directory and upload directory
        self.working_dir = working_dir
        self.upload_dir = upload_dir

        self.uncompressed_file = os.path.join(self.working_dir, uuid.uuid4().hex)

        outfile = open(self.uncompressed_file, 'wb')
        datastream = open(self.device, 'rb')

        self.start_time = time.gmtime()
        n_samples = 0

        while n_samples < self.total_samples:
            # read the data and append to the file
            now = time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime())
            data = datastream.read(self.sample_size)
            outfile.write('{}: {}\n'.format(now, data))

            # wait and increment the counter
            time.sleep(self.sample_rate)
            n_samples += 1

        # tidy up and hand off to post processing
        outfile.close()
        datastream.close()

    def postprocess(self):
        """
        A method to postprocess the sample file.

        In this case, this is simple compression, but if no
        postprocessing is used then this method can simply pass and
        the sample method should add the file to the upload folder.
        Otherwise sample should create a temporary file and postprocess
        also needs to handle staging the file to the upload folder.
        """

        zipfile = 'final_{}.zip'.format(time.strftime('%d%m%Y_%H%M%S', self.start_time))

        subprocess.call(["zip", os.path.join(self.upload_dir, zipfile), self.uncompressed_file])
        os.remove(self.uncompressed_file)

    def sleep(self):
        """
        A method to pause the Sensor between samples.
        """
        time.sleep(self.capture_delay)
