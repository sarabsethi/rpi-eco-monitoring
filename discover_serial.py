import sys

def discover_serial():
    """
    Function to return the Raspberry Pi serial from /proc/cpuinfo

    Returns:
        A string containing the serial number or an error placeholder
    """

    # parse /proc/cpuinfo
    cpu_serial = None
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                cpu_serial = line.split(':')[1].strip()
        f.close()
        # No serial line found?
        if cpu_serial is None:
            raise IOError
    except IOError:
        cpu_serial = "ERROR000000001"

    cpu_serial = "RPiID-{}".format(cpu_serial)
    
    # echo it to std out
    sys.stdout.write(cpu_serial)


if __name__ == "__main__":

    discover_serial()
