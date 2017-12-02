import time
from threading import Thread
import subprocess
import os

class TimelapseCamera:

    def capture_data(self,temp_out_dir,final_out_dir):
        # Name images by capture time
        capture_time = time.strftime('%H-%M-%S')
        raw_data_fname = '{}/{}.jpeg'.format(temp_out_dir,capture_time)
        final_fname_no_ext = '{}/{}'.format(final_out_dir,capture_time)

        if os.path.exists('/dev/video0'):
            print('\nTaking picture - smile!\n')
            res = '2592x1944'
            # Delay and skip some frames to make sure exposure is adjusted to lighting
            subprocess.call('fswebcam -D 5 -S 20 -p YUYV -r {} {}'.format(res,raw_data_fname),shell=True)
        else:
            print('No camera detected');
        subprocess.call('touch {}'.format(raw_data_fname),shell=True)

        return raw_data_fname,final_fname_no_ext

    # No postprocessing is done since the image is captured directly to jpeg
    def postprocess(self,raw_data_fname,final_fname_no_ext):
        final_fname = '{}.jpeg'.format(final_fname_no_ext)
        os.rename(raw_data_fname,final_fname)
