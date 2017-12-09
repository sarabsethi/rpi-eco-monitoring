import os
import json
import sys

def discover_serial(config_file):
    """
    Function to extract Raspberry Pi serial from cpuinfo file
    and update a config file and an environment variable

    Returns:
        A string containing the serial or an error value
    """

    # parse /proc/cpuinfo
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                cpu_serial = line[10:26]
        f.close()
    except:
        cpu_serial = "ERROR000000001"

    # store it in the config file
    config = json.load(open(config_file, 'r'))
    config['cpu_serial'] = cpu_serial
    json.dump(config, open(config_file, 'w'))

    # echo it to std out
    sys.stdout.write(cpu_serial)


if __name__ == "__main__":

    discover_serial(sys.argv[1])