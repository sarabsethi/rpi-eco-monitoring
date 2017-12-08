# Import individual sensor class files into the sensor module namespace
# This does need to be edited as classes are added

from sensors.TimelapseCamera import TimelapseCamera
from sensors.USBSoundcardMic import USBSoundcardMic
from sensors.UnixDevice import UnixDevice

def set_option(var, config, opts):
    """
    Method to compare the provided and default config for a class variable
    and return a value.

    Args:
        var: The variable to return a value for
        config: The provided sensor config loaded from file
        opts: The base information from the sensor options method

    Returns:
        A value for the class variable named in var
    """

    this_opt = opts[var]
    if 'default' in this_opt.keys():
        default_val = this_opt['default']
    else:
        default_val = None

    # check if there is a config value of the right type
    val_type = this_opt['type']
    if config is not None and var in config:
        if isinstance(config[var], val_type):
            use_default = False
        else:
            use_default = True
    else:
        use_default = True

    # return what is available
    if not use_default:
        return config[var]
    elif use_default and default_val is not None:
        return default_val
    else:
        raise ValueError('No config value provided for {} and no default value is set'.format(var))