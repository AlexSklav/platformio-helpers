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


def available_environments(project_name):
    '''
    Parameters
    ----------
    project_name : str
        Name of PlatformIO project.

    Returns
    -------
    list
        List of available environments with compiled binaries for the specified
        PlatformIO project.

    Raises
    ------
    NameError
        If no PlatformIO project with the specified name is found in the Conda
        PlatformIO binary search path.
    '''
    # Get root directory in Conda environment where PlatformIO project binaries
    # are located.
    conda_bin_path_ = conda_bin_path()
    project_bin_dir = conda_bin_path_.joinpath(project_name)
    if not project_bin_dir.isdir():
        raise NameError('No PlatformIO project named `{}` found in `{}`'
                        .format(project_name, conda_bin_path_))
    else:
        # Project directory was found.  Each subdirectory contains a compiled
        # firmware for the corresponding PlatformIO environment.

        # Return sorted list so result is deterministic.
        return sorted([str(env_i.name) for env_i in project_bin_dir.dirs()])


