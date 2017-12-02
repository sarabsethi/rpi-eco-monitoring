# rpi-eco-monitoring

Automated continuous bio-acoustic monitoring

Edit ``/etc/profile`` on your Pi to run ``recorder_startup_script.sh`` on boot (see example startup script in os_files directory). Main python code which calls various bash snippets is in ``python_record.py``.

This is the core Python / Shell code but additional tweaks are needed to the Raspbian Jessie SD card image before it works properly. Full instructions to follow eventually - for now ask me (s.sethi16@imperial.ac.uk) 
