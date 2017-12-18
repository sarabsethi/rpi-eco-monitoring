# rpi-eco-monitoring

This is part of a project developing a fully autonomous ecosystem monitoring unit. The full details of the device is described in an [academic paper](http://www.bbc.com), **easy to follow step by step instructions of setting one up from scratch can be found [on our website](https://sarabsethi.github.io/autonomous_ecosystem_monitoring/)**, and this page focuses more on the details of the software running on the device, targetted at more technical users.

## Setup

### Setup from our pre-prepared SD card image
To setup the monitoring unit from [our pre-prepared SD card image](https://www.dropbox.com/s/q9zynny0aajrcue/SD_card_rpi-eco-monitoring_lts.img?dl=0) follow these steps:
* Boot the Raspberry Pi with our prepared SD card inserted. Let the startup script run until it exits with the message "Config file not found!". If you would like to change an existing configuration, press ``Ctrl+C`` when you see "Start of ecosystem monitoring startup script"
* Type ``cd ~/rpi-eco-monitoring``
* Run ``python setup.py`` and follow the prompts. This will create a ``config.json`` file which contains the sensor type, its configuration and the FTP server details. The config file can be created manually, or imported from external storage without running ``setup.py`` if preferred 
* Make sure the timezone is set correctly. Check by typing ``sudo dpkg-reconfigure tzdata`` and following the prompts 
* If your SD card is larger than the size of our pre-prepared image (4GB) run ``sudo raspi-config`` and choose: _Advanced Options_ -> _Expand Filesystem_. Press ``Esc`` when this is complete
* Type ``sudo halt`` to shut down the Pi
* Take the microSD card from the Pi, and make a copy of it onto your computer [(How?)](https://www.raspberrypi.org/documentation/installation/installing-images/). Now you can clone as many of these SD cards as you need for your monitoring devices with no extra setup required 

### Setup from a stock Raspbian image
If you would rather start using a stock Raspbian image, there's an extra couple of steps before you start the above process. The below steps assume you have downloaded and installed the [Raspbian Stretch Lite image](https://www.raspberrypi.org/downloads/raspbian/).

You will need the Pi to be connected to the internet for the below process.

* Login when prompted with user 'pi' and password 'raspberry'
* Type ``sudo raspi-config`` and configure the Pi to boot to a command line, without login required: option _Boot Options_ -> _Desktop / CLI_ -> _Console Autologin_. Press ``Esc`` when this is complete
* Install git: ``sudo apt-get install git``
* Clone this repository in the home directory of the Raspberry pi: ``git clone -b lts https://github.com/sarabsethi/rpi-eco-monitoring.git`` (see below regarding branches)
* Make sure all the scripts in the repository are executable: ``chmod +x ~/rpi-eco-monitoring/*``
* Configure the Pi to run ``recorder_startup_script.sh`` on boot by adding ``sudo -u pi ~/rpi-eco-monitoring/recorder_startup_script.sh;`` to the last line of the file ``/etc/profile`` (requires root)
* Install the required packages: ``sudo apt-get -y install fswebcam lftp libav-tools usb-modeswitch ntpdate libvpx4 zip``
* Then follow the instructions above to complete the setup

**N.B.** This clones the long-term support branch, which will have software that has been extensively field-tested, whilst the ``dev`` branch will have the latest development code which may inherently be more unstable. For long remote deployments we recommend only using the LTS branch, and this is the branch used in our pre-prepared SD card images. If you plan on implementing a new sensor, fork the codebase and make your changes, but be sure to submit a pull request back to this repo when you're done!

## Implementing new sensors

To implement a new sensor type simply create a class in the ``sensors`` directory that implements the following methods:

* ``__init__`` - This method is loads the sensor options from the JSON configuration file, falling back to the default options (see the ``options`` static method below) where an option isn't included in the config. The ``__init.py__`` file in the ``sensors`` module provides the shared function ``set_options`` to help with this.
* ``options`` - This static method defines the config options and defaults for the sensor class
* ``setup`` - This method should be used to check that the system resources required to run the sensor are available: required Debian packages, correctly installed devices.
* ``capture_data`` - This method is used to capture data from the sensor input. The data will normally be stored to a working directory, set in the config file, in case further processing is needed before data is uploaded. If no further processing is needed, the data could be written directly to the upload directory.
* ``postprocess`` - This method performs any postprocessing that needs to be done to the raw data (e.g. compressing it) before upload. If no post processing is needed, you must still provide the method, but it can simply ``pass``.
* ``sleep`` - This method is a simple wrapper to pause between data captures - the pause length is implemented as a variable in the JSON config, so you're unlikely to need to change this method.
* ``cleanup`` - This method is used to check for and clean up any temporary files when the system shuts down.

Note that threads are used to run the ``capture_data`` and ``postprocess`` methods so that they operate independently.

For worked examples see classes made for monitoring audio from a USB audio card ([``USBSoundcardMic.py``](https://github.com/sarabsethi/rpi-eco-monitoring/blob/master/sensors/USBSoundcardMic.py)) and for capturing time-lapse images from a USB camera ([``TimelapseCamera.py``](https://github.com/sarabsethi/rpi-eco-monitoring/blob/master/sensors/TimelapseCamera.py)). For a really simple example, see the UnixDevice sensor ([``UnixDevice.py``](https://github.com/sarabsethi/rpi-eco-monitoring/blob/master/sensors/UnixDevice.py)): this just demonstrates the use of the class methods to read data from one of the basic system devices.

Finally add ``from sensors.YourNewSensor import YourNewSensor`` to ``sensors/__init__.py``

## Authors
This is a cross disciplinary research project based at Imperial College London, across the Faculties of Engineering, Natural Sciences and Life Sciences. 

Sarab Sethi, Rob Ewers, Nick Jones, David Orme, Lorenzo Picinali

Feel free to [drop me an email](mailto:s.sethi16@imperial.ac.uk) with any questions, and contributions to this codebase are always welcome.
