# rpi-eco-monitoring

This is part of a project developing a fully autonomous ecosystem monitoring unit. The full details of the device is described in an [academic paper](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.13089), **easy to follow step by step instructions of setting one up from scratch can be found [on our website](https://sarabsethi.github.io/autonomous_ecosystem_monitoring/)**, and this page focuses more on the details of the software running on the device, targeted at more technical users. 

Information on how to build these devices into a fully functional real-time monitoring network can be found in a further [academic paper](https://www.biorxiv.org/content/10.1101/2020.02.27.968867v1), and full code and deployment notes for the associated server-side software can be found in the [acoustics-db GitHub repository](https://github.com/ImperialCollegeLondon/acoustics-db). 

**This code is not being actively maintained** and may not work on newer Raspberry Pi devices / OS images (originally written in 2018). Designs and firmware for a more recently built similar device, [Bugg](https://www.bugg.xyz) can be found open-source at https://github.com/bugg-resources.

## Code design

The ``setup.py`` script is used to configure the required sensor to be used for data capture and creates a JSON config fle. Once a sensor configuration has been created, the recorder is started up using ``recorder_startup_script.sh``, which runs  the ``record()`` function from ``python_record.py``. This then does the following:

1. Sets up error logging.
2. Logs the id of the Pi device running the code and the current git version of the recorder script.
3. Loads the config file.
4. Sets the reboot time.
5. Checks the working and upload directories for data files and copies previous logs into the upload directory.
6. Runs the ``configure_sensor`` function to instantiate a sensor class object.
7. Attaches the function ``exit_handler`` to run if a SIGINT signal is detected either from reboot or user interrupt.
7. Creates a thread instance that executes the FTP synchronisation at a server sync interval defined by the sensor config using the ``ftp_server_sync()`` function.
8. Creates a thread instance that runs the ``continuous_recording()``  function. This function is just a wrapper that repeats the ``sensor_record`` function while the thread is running.
9. The ``sensor_record`` function itself executes the sensor methods: a) ``sensor.capture_data()`` to record whatever it is the sensor records; b) ``sensor.postprocess()`` is run in a separate thread to avoid locking up the ``sensor_record`` loop; and then c) ``sensor.sleep()`` to pause until the next sample is due.
10. When a SIGINT occurs then ``exit_handler`` intercepts SIGINT and raises a ``StopMonitoring``  exception to exit the recording. The exception handling sets a threading event instance that has been passed to the two threads running ``ftp_server_sync()`` and  ``continuous_recording()``, and signals that the functions running in these thread should finish their current loop and exit. The ``record()`` function then exits.
11. As long as  ``recorder_startup_script.sh`` is setup to run on boot, then the process repeats from the first step.

## Setup

### Setup from our pre-prepared SD card image
To setup the monitoring unit from [our pre-prepared SD card image](https://www.dropbox.com/sh/0zth6nb7dpocms0/AABybwvwO4fepkbi1kWFUfJEa?dl=0) follow these steps:
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

To implement a new sensor type simply create a class in the ``sensors`` directory that extends the SensorBase class. The SensorBase class contains default implementations of the required class methods, which can be overridden in derived sensor classes. The required methods are:

* ``__init__`` - This method is loads the sensor options from the JSON configuration file, falling back to the default options (see the ``options`` static method below) where an option isn't included in the config. The ``__init.py__`` file in the ``sensors`` module provides the shared function ``set_options`` to help with this.
* ``options`` - This static method defines the config options and defaults for the sensor class
* ``setup`` - This method should be used to check that the system resources required to run the sensor are available: required Debian packages, correctly installed devices.
* ``capture_data`` - This method is used to capture data from the sensor input. The data will normally be stored to a working directory, set in the config file, in case further processing is needed before data is uploaded. If no further processing is needed, the data could be written directly to the upload directory.
* ``postprocess`` - This method performs any postprocessing that needs to be done to the raw data (e.g. compressing it) before upload. If no post processing is needed, you don't need to provide the method, as the default SensorBase implementation contains a simple stub to handle calls to ``Sensor.postprocess()``.
* ``sleep`` - This method is a simple wrapper to pause between data captures - the pause length is implemented as a variable in the JSON config, so you're unlikely to need to override the base method.

Note that threads are used to run the ``capture_data`` and ``postprocess`` methods so that they operate independently.

For worked examples see classes made for monitoring audio from a USB audio card ([``USBSoundcardMic.py``](https://github.com/sarabsethi/rpi-eco-monitoring/blob/lts/sensors/USBSoundcardMic.py)) and for capturing time-lapse images from a USB camera ([``TimelapseCamera.py``](https://github.com/sarabsethi/rpi-eco-monitoring/blob/lts/sensors/TimelapseCamera.py)). For a really simple example, see the UnixDevice sensor ([``UnixDevice.py``](https://github.com/sarabsethi/rpi-eco-monitoring/blob/lts/sensors/UnixDevice.py)): this just demonstrates the use of the class methods to read data from one of the basic system devices.

Finally add ``from sensors.YourNewSensor import YourNewSensor`` to ``sensors/__init__.py``


## Authors
This is a cross disciplinary research project based at Imperial College London, across the Faculties of Engineering, Natural Sciences and Life Sciences.

Sarab Sethi, Rob Ewers, Nick Jones, David Orme, Lorenzo Picinali

Feel free to [drop me an email](mailto:s.sethi16@imperial.ac.uk) with any questions, and contributions to this codebase are always welcome.

## Citations
Please cite the below papers when referring to this work:

Sethi, SS, Ewers, RM, Jones, NS, Orme, CDL, Picinali, L. Robust, real‐time and autonomous monitoring of ecosystems with an open, low‐cost, networked device. Methods Ecol Evol. 2018; 9: 2383– 2387. https://doi.org/10.1111/2041-210X.13089 

Sethi, SS, Ewers, RM, Jones, NS, Signorelli, A., Picinali, L, Orme, CDL. SAFE Acoustics: an open-source, real-time eco-acoustic monitoring network in the tropical rainforests of Borneo. biorxiv 968867. https://doi.org/10.1101/2020.02.27.968867
