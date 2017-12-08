import time
import subprocess
import os


class USBSoundcardMic(object):

    def __init__(self, wdir, udir, config=None):

        """
        A class to record audio from a USB Soundcard microphone.

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

        if config is not None and 'record_length' in config:
            try:
                self.record_length = float(config['record_length'])
            except ValueError:
                print("Invalid record length in sensor config ({}), using default."
                      " ".format(config['record_length']))
                self.record_length = defaults['record_length']
        else:
            self.record_length = defaults['record_length']

        if config is not None and 'compress_data' in config:
            # insist on 1/0 coding for boolean variables: bool('False') is a common gotcha
            if config['compress_data'] in [0, 1]:
                self.compress_data = bool(config['compress_data'])
            else:
                print("Invalid compress_data ({}) in sensor config, using default."
                      " ".format(config['compress_data']))
                self.compress_data = defaults['compress_data']
        else:
            self.compress_data = defaults['compress_data']

        if config is not None and 'capture_delay' in config:
            try:
                self.capture_delay = float(config['capture_delay'])
            except ValueError:
                print("Invalid capture delay in sensor config ({}), using default."
                      " ".format(config['capture_delay']))
                self.capture_delay = defaults['capture_delay']
        else:
            self.capture_delay = defaults['capture_delay']

        # That could all be done with a setattr loop (see commented code) which might
        # be faster for a long list, but actually it is less obscure and code checkers
        # work more easily if this is done simply, exposing the class variable names.

        # for var in defaults:
        #     if config is not None and var['name'] in config:
        #         # check the type
        #         var_type = type(var['default'])
        #         try:
        #             value = var_type(config[var['name']])
        #             # set the variable
        #             setattr(self, var['name'], value)
        #         except ValueError:
        #             print("Error setting {} in sensor config".format(var['name']))
        #     else:
        #         setattr(self, var['name'], var['default'])

        # set internal variables and required class variables
        self.working_file = 'currentlyRecording.wav'
        self.current_file = None
        self.wdir = wdir
        self.udir = udir
        self.server_sync_interval = self.record_length + self.capture_delay

        # Load alsactl file - increased microphone volume level
        # subprocess.call('alsactl --file ./audio_sensor_scripts/asound.state restore', shell=True)

        self.cleanup()

    @staticmethod
    def config():
        """
        Static method defining the config options and defaults for the sensor class
        """
        return [{'name': 'record_length',
                 'type': float,
                 'default': 1200.0,
                 'prompt': 'What is the time in seconds of the audio segments?'},
                {'name': 'compress_data',
                 'type': int,
                 'default': 1,
                 'prompt': 'Should the audio data be compressed from WAV to VBR mp3?',
                  'valid': [0, 1]},
                {'name': 'capture_delay',
                 'type': float,
                 'default': 0.0,
                 'prompt': 'How long should the system wait between audio samples?'}
                ]

    def capture_data(self):
        """
        Method to capture raw audio data from the USB Soundcard Mic
        """

        # Name files by start time and duration
        start_time = time.strftime('%H-%M-%S')
        self.current_file = '{}_dur={}secs'.format(start_time, self.record_length)

        # Record for a specific duration
        print('\n{} - Started recording\n'.format(self.current_file))
        wfile = os.path.join(self.wdir, self.working_file)
        ofile = os.path.join(self.wdir, self.current_file)
        try:
            cmd = 'sudo arecord --device hw:1,0 --rate 44100 --format S16_LE --duration {} {}'
            subprocess.call(cmd.format(self.record_length, wfile), shell=True)
            os.rename(wfile, ofile + '.wav')
        except subprocess.CalledProcessError:
            print('Error recording from audio card. Creating dummy file')
            open(ofile + '_ERROR_audio-record-failed', 'a').close()

        print('\n{} - Finished recording\n'.format(self.current_file))

    def postprocess(self):
        """
        Method to optionally compress raw audio data to mp3 format and stage data to
        upload folder
        """

        # current working file
        wfile = os.path.join(self.wdir, self.current_file) + '.wav'

        if self.compress_data == 'y':
            # Compress the raw audio file to mp3 format
            ofile = os.path.join(self.udir, self.current_file) + '.mp3'

            print('\n{} - Starting compression\n'.format(self.current_file))
            cmd = ('avconv -loglevel panic -i {} -codec:a libmp3lame -filter:a "volume=5" '
                   '-qscale:a 0 -ac 1 {} >/dev/null 2>&1')
            subprocess.call(cmd.format(wfile, ofile), shell=True)
            print('\n{} - Finished compression\n'.format(self.current_file))

        else:
            # Don't compress, store as wav
            print('\n{} - No postprocessing of audio data\n'.format(self.current_file))
            ofile = os.path.join(self.udir, self.current_file) + '.wav'
            os.rename(wfile, ofile)

    def sleep(self):
        """
        Method to pause between data capture
        """
        time.sleep(self.capture_delay)

    def cleanup(self):
        """
        Method to make sure the system is clean to go
        """
        wfile = os.path.join(self.wdir, self.working_file)
        if os.path.exists(wfile):
            os.remove(wfile)
