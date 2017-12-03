import time
from threading import Thread
import subprocess
import os
import ntpath

class USBSoundcardMic(object):

    def __init__(self,record_length,compress_data):
        self.record_length = record_length
        self.compress_data = compress_data

        self.recording_file = 'currentlyRecording.wav'
        if os.path.exists(self.recording_file):
           os.remove(self.recording_file)

        # Load alsactl file - increased microphone volume level
        subprocess.call('alsactl --file ./audio_sensor_scripts/asound.state restore', shell=True)

    # Capture raw audio data from USB sound card
    def capture_data(self,temp_out_dir,final_out_dir):
        # Name files by start time and duration
        startTime = time.strftime('%H-%M-%S')
        raw_data_fname = '{}/{}_dur={}secs.wav'.format(temp_out_dir,startTime,self.record_length)
        final_fname_no_ext = '{}/{}_dur={}secs'.format(final_out_dir,startTime,self.record_length)

        # Record for a specific duration
        print('\n{} - Started recording\n'.format(ntpath.basename(raw_data_fname)))
        subprocess.call('sudo bash ./audio_sensor_scripts/bash_record_audio.sh {} {} {}'.format(self.record_length,raw_data_fname,recording_file),shell=True)
        print('\n{} - Finished recording\n'.format(ntpath.basename(raw_data_fname)))

        return raw_data_fname,final_fname_no_ext

    # Compress raw audio data to mp3 format
    def postprocess(self,raw_data_fname,final_fname_no_ext):
        if self.compress_data:
            # Compress the raw audio file to mp3 format
            final_fname = '{}.mp3'.format(final_fname_no_ext)
            print('\n{} - Starting compression\n'.format(ntpath.basename(raw_data_fname)))
            subprocess.call('bash ./audio_sensor_scripts/bash_compress_audio_mp3.sh {} {}'.format(raw_data_fname,final_fname),shell=True)
            print('\n{} - Finished compression\n'.format(ntpath.basename(final_fname)))
        else:
            # Don't compress, store as wav
            print('\nNo postprocessing of audio data: {}\n'.format(ntpath.basename(raw_data_fname)))
            final_fname = '{}.wav'.format(final_fname_no_ext)
            os.rename(raw_data_fname,final_fname)
