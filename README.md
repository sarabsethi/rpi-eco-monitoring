# rpi-eco-monitoring

This is part of a project developing a fully autonomous ecosystem monitoring unit. The full details of the device is described in an [academic paper](http://www.bbc.com), step by step instructions of setting one up from scratch can be found [on our website](https://sarabsethi.github.io/autonomous_ecosystem_monitoring/), and this page focuses more on the details of the software running on the device.

## Setup

### Setup from our pre-prepared SD card image
To setup the monitoring unit from our pre-prepared SD card image follow these steps:
* Boot the Raspberry Pi with our prepared SD card inserted. When you see ``Recorder script started`` press ``Ctrl+C``
* Type ``cd ~/rpi-eco-monitoring``
* Run ``python setup.py`` and follow the prompts. This will create a ``config.json`` file which contains the sensor type, its configuration and the FTP server details. 
* Make sure the timezone is set correctly. Check by typing ``sudo dpkg-reconfigure tzdata`` and following the prompts 
* If your SD card is larger than the size of our pre-prepared image (4GB) run ``sudo raspi-config`` and choose: _Advanced Options_ -> _Expand Filesystem_. Press ``Esc`` when this is complete
* Type ``sudo halt`` to shut down the Pi
* Take the microSD card from the Pi, and make a copy of it onto your computer (How?). Now you can clone as many of these SD cards as you need for your monitoring devices with no extra setup required 

### Setup from a stock Raspbian image
If you would rather start using a stock Raspbian image, there's an extra couple of steps before you start the above process. The below steps assume you have downloaded and installed the [Raspbian Stretch Lite image](https://www.raspberrypi.org/downloads/raspbian/).

* Login when prompted with user 'pi' and password 'raspberry'
* Type ``sudo raspi-config`` and configure the Pi to boot to a command line, without login required: option _Boot Options_ -> _Desktop / CLI_ -> _Console Autologin_. Press ``Esc`` when this is complete
* Install git: ``sudo apt-get install git``
* Clone this repository in the home directory of the Raspberry pi: ``git clone https://github.com/sarabsethi/rpi-eco-monitoring.git``
* Make sure all the scripts in the repository are executable: ``chmod +x ~/rpi-eco-monitoring/*``
* Configure the Pi to run ``recorder_startup_script.sh`` on boot by adding ``sudo -u pi ~/rpi-eco-monitoring/recorder_startup_script.sh;`` to the last line of the file ``/etc/profile`` (requires root)
* Then follow the instructions above to complete the setup

## Implementing new sensors

To implement a new sensor type simply create a class that implements the three functions:
* ``capture_data`` - capture data from the sensor input and store it temporarily in raw unprocessed format
* ``postprocess`` - process the raw data in the appropriate manner (e.g. compress it)
* ``cleanup`` - clean up any temporary files

For worked examples see classes made for monitoring audio from a USB audio card (``USBSoundcardMic.py``) and for capturing time-lapse images from a USB camera (``TimelapseCamera.py``)

Then edit ``python_record.py`` and ``setup.py`` where indicated as comments in the code to include your new class of sensor

## Authors
This is a cross disciplinary research project based at Imperial College London, across the Faculties of Engineering, Natural Sciences and Life Sciences. 

Sarab Sethi, Rob Ewers, Nick Jones, Lorenzo Picinali

More extensive documentation to come - any questions feel free to [drop me an email](mailto:s.sethi16@imperial.ac.uk)
