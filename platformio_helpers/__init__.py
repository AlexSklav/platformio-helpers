import platform

import conda_helpers as ch


def conda_arduino_include_path():
    '''
    Returns
    -------
    path_helpers.path
        Path to Arduino libraries directory in active Conda environment.
    '''
    if platform.system() in ('Linux', 'Darwin'):
        return ch.conda_prefix().joinpath('include', 'Arduino')
    elif platform.system() == 'Windows':
        return ch.conda_prefix().joinpath('Library', 'include', 'Arduino')
    raise 'Unsupported platform: %s' % platform.system()


def conda_bin_path():
    '''
    Returns
    -------
    path_helpers.path
        Path to directory in active Conda environment containing compiled
        PlatformIO Conda package binaries.
    '''
    if platform.system() in ('Linux', 'Darwin'):
        sys_prefix = ch.conda_prefix()
    elif platform.system() == 'Windows':
        sys_prefix = ch.conda_prefix().joinpath('Library')
    else:
        raise 'Unsupported platform: %s' % platform.system()
    return sys_prefix.joinpath('bin', 'platformio')
