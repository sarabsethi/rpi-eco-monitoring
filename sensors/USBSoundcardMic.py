import time
import subprocess
import os
import sensors
import logging
from sensors.SensorBase import SensorBase

class USBSoundcardMic(SensorBase):

    def __init__(self, config=None):

        """
        A class to record audio from a USB Soundcard microphone.

        Args:
            config: A dictionary loaded from a config JSON file used to replace
            the default settings of the sensor.
        """

        # Initialise the sensor config, double checking the types of values. This
        # code uses the variables named and described in the config static to set
        # defaults and override with any passed in the config file.
        opts = self.options()
        opts = {var['name']: var for var in opts}

        self.record_length = sensors.set_option('record_length', config, opts)
        self.compress_data = sensors.set_option('compress_data', config, opts)
        self.capture_delay = sensors.set_option('capture_delay', config, opts)

        # set internal variables and required class variables
        self.working_file = 'currentlyRecording.wav'
        self.current_file = None
        self.working_dir = None
        self.upload_dir = None
        self.server_sync_interval = self.record_length + self.capture_delay

    @staticmethod
    def options():
        """
        Static method defining the config options and defaults for the sensor class
        """
        return [{'name': 'record_length',
                 'type': int,
                 'default': 1200,
                 'prompt': 'What is the time in seconds of the audio segments?'},
                {'name': 'compress_data',
                 'type': str,
                 'default': 'True',
                 'prompt': 'Should the audio data be compressed from WAV to VBR mp3?'},
                {'name': 'capture_delay',
                 'type': int,
                 'default': 0,
                 'prompt': 'How long should the system wait between audio samples?'}
                ]

    def setup(self):

        try:
            # Load alsactl file - increased microphone volume level
            subprocess.call('alsactl --file ./audio_sensor_scripts/asound.state restore', shell=True)
            return True
        except:
            raise EnvironmentError

    def capture_data(self, working_dir, upload_dir):
        """
        Method to capture raw audio data from the USB Soundcard Mic

        Args:
            working_dir: A working directory to use for file processing
            upload_dir: The directory to write the final data file to for upload.
        """

        # populate the working and upload directories
        self.working_dir = working_dir
        self.upload_dir = upload_dir

        # Name files by start time and duration
        start_time = time.strftime('%H-%M-%S')
        self.current_file = '{}_dur={}secs'.format(start_time, self.record_length)

        # Record for a specific duration
        logging.info('\n{} - Started recording\n'.format(self.current_file))
        wfile = os.path.join(self.working_dir, self.working_file)
        ofile = os.path.join(self.working_dir, self.current_file)
        try:
            cmd = 'sudo arecord --device hw:1,0 --rate 44100 --format S16_LE --duration {} {}'
            subprocess.call(cmd.format(self.record_length, wfile), shell=True)
            self.uncomp_file = ofile + '.wav'
            os.rename(wfile, self.uncomp_file)
        except Exception:
            logging.info('Error recording from audio card. Creating dummy file')
            open(ofile + '_ERROR_audio-record-failed', 'a').close()
            time.sleep(1)

        logging.info('\n{} - Finished recording\n'.format(self.current_file))

    def postprocess(self):
        """
        Method to optionally compress raw audio data to mp3 format and stage data to
        upload folder
        """

        # current working file
        wfile = self.uncomp_file

        if self.compress_data == True:
            # Compress the raw audio file to mp3 format
            ofile = os.path.join(self.upload_dir, self.current_file) + '.mp3'

            logging.info('\n{} - Starting compression\n'.format(self.current_file))
            cmd = ('avconv -loglevel panic -i {} -codec:a libmp3lame -filter:a "volume=5" '
                   '-qscale:a 0 -ac 1 {} >/dev/null 2>&1')
            subprocess.call(cmd.format(wfile, ofile), shell=True)
            logging.info('\n{} - Finished compression\n'.format(self.current_file))

        else:
            # Don't compress, store as wav
            logging.info('\n{} - No postprocessing of audio data\n'.format(self.current_file))
            ofile = os.path.join(self.upload_dir, self.current_file) + '.wav'
            os.rename(wfile, ofile)

