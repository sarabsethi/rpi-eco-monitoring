import time
from threading import Thread
import subprocess
import os
import ntpath

class USBSoundcardMic(object):

    def __init__(self,record_length,compress_data):
        self.record_length = int(record_length)
        self.compress_data = bool(compress_data)

        # Load alsactl file - increased microphone volume level
        subprocess.call('alsactl --file ./audio_sensor_scripts/asound.state restore', shell=True)

        self.cleanup()

    # Capture raw audio data from USB sound card
    def capture_data(self,temp_out_dir,final_out_dir):
        # Name files by start time and duration
        startTime = time.strftime('%H-%M-%S')
        raw_data_fname = '{}/{}_dur={}secs.wav'.format(temp_out_dir,startTime,self.record_length)
        final_fname_no_ext = '{}/{}_dur={}secs'.format(final_out_dir,startTime,self.record_length)

        # Record for a specific duration
        print('\n{} - Started recording\n'.format(ntpath.basename(raw_data_fname)))
        try:
            subprocess.call('sudo arecord --device hw:1,0 --rate 44100 --format S16_LE --duration {} {}'.format(self.record_length,self.recording_file),shell=True)
            os.rename(self.recording_file,raw_data_fname)
        except:
            print('Error recording from audio card. Creating dummy file')
            final_fname_no_ext = final_fname_no_ext + '_ERROR_audio-record-failed'
            open(raw_data_fname, 'a').close()

        print('\n{} - Finished recording\n'.format(ntpath.basename(raw_data_fname)))

        return raw_data_fname,final_fname_no_ext

    # Compress raw audio data to mp3 format
    def postprocess(self,raw_data_fname,final_fname_no_ext):
        if self.compress_data:
            # Compress the raw audio file to mp3 format
            final_fname = '{}.mp3'.format(final_fname_no_ext)
            temp_comp_fname = raw_data_fname + '_temp.mp3'

            print('\n{} - Starting compression\n'.format(ntpath.basename(raw_data_fname)))
            subprocess.call('avconv -loglevel panic -i {} -codec:a libmp3lame -filter:a "volume=5" -qscale:a 0 -ac 1 {} >/dev/null 2>&1'.format(raw_data_fname,temp_comp_fname),shell=True)
            print('\n{} - Finished compression\n'.format(ntpath.basename(final_fname)))

            os.rename(temp_comp_fname,final_fname)
            os.remove(raw_data_fname)
        else:
            # Don't compress, store as wav
            print('\nNo postprocessing of audio data: {}\n'.format(ntpath.basename(raw_data_fname)))
            final_fname = '{}.wav'.format(final_fname_no_ext)
            os.rename(raw_data_fname,final_fname)

    def cleanup(self):
        self.recording_file = 'currentlyRecording.wav'
        if os.path.exists(self.recording_file):
           os.remove(self.recording_file)
