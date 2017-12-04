import os

class Sensor(object):

    def capture_data(self,temp_out_dir,final_out_dir):
        return 'raw_data_fname', 'final_fname'

    def postprocess(self,raw_data_fname,final_fname):
        os.rename(raw_data_fname,final_fname)

    def cleanup():
        pass
