import logging
import os

import conda_helpers as ch
import path_helpers as ph

from . import conda_arduino_include_path, conda_bin_path


logger = logging.getLogger(__name__)


def link(working_dir=None, package_name=None):
    '''
    Prepare development environment.

    Perform the following steps:

     - Uninstall package if installed as Conda package.
     - Install build and run-time Conda dependencies.
     - Link working ``.pioenvs`` directory into Conda ``Library`` directory to
       make development versions of compiled firmware binaries available to
       Python API.
     - TODO Link working ``lib`` directory (if it exists) into Conda
       ``Library`` directory to make development versions of C++ headers
       available to PlatformIO.
     - Link Python package into site packages directory.

    See Also
    --------
    :func:`unlink`
    '''
    if working_dir is None:
        working_dir = os.getcwd()

    # Resolve absolute working directory.
    working_dir = ph.path(working_dir).realpath()

    if package_name is None:
        package_name = working_dir.name

    # Uninstall package if installed as Conda package.
    logger.info('Check if Conda package is installed...')
    try:
        version_info = ch.package_version(package_name)
    except NameError:
        logger.info('`%s` package is not installed.', package_name)
    else:
        logger.info('Uninstall `%s==%s` package...', package_name,
                    version_info.get('version'))
        ch.conda_exec('uninstall', '--force', '-y', package_name, verbose=True)

    # Install build and run-time Conda dependencies.
    logger.info('Install build and run-time Conda dependencies...')
    recipe_dir = working_dir.joinpath('.conda-recipe').realpath()
    ch.conda_exec('install', '-y', '-n', 'root', 'conda-build', verbose=True)
    ch.development_setup(recipe_dir, verbose=True)

    # Link working ``.pioenvs`` directory into Conda ``Library`` directory.
    logger.info('Link working firmware directories into Conda environment.')
    pio_bin_dir = conda_bin_path()

    fw_bin_dir = pio_bin_dir.joinpath(package_name)

    if not fw_bin_dir.exists():
        working_dir.joinpath('.pioenvs').junction(fw_bin_dir)

    fw_config_ini = fw_bin_dir.joinpath('platformio.ini')
    if not fw_config_ini.exists():
        working_dir.joinpath('platformio.ini').link(fw_config_ini)

    # Link working ``lib`` directory into Conda ``Library/include/Arduino``
    # directory.
    logger.info('Link working firmware libraries into Conda environment.')
    pio_lib_dir = conda_arduino_include_path()
    working_lib_dir = working_dir.joinpath('lib')

    if working_lib_dir.isdir():
        pio_lib_dir.makedirs_p()
        for file_i in working_lib_dir.files():
            file_i.link(pio_lib_dir.joinpath(file_i.name))
        for dir_i in working_lib_dir.dirs():
            dir_i.junction(pio_lib_dir.joinpath(dir_i.name))

    # Link ``dmf_control_board_firmware`` Python package `conda.pth` in site
    # packages directory.
    logger.info('Link working Python directory into Conda environment...')
    ch.conda_exec('develop', working_dir, verbose=True)
    logger.info(72 * '-' + '\nFinished')


def unlink(working_dir=None, package_name=None):
    '''
    Restore original (i.e., non-development) environment.

    Perform the following steps:

     - Unlink working ``.pioenvs`` directory from Conda ``Library`` directory.
     - TODO Unlink working ``lib`` directory from Conda ``Library`` directory.
     - Unlink Python package from site packages directory.

    See Also
    --------
    :func:`link`
    '''
    if working_dir is None:
        working_dir = os.getcwd()

    # Resolve absolute working directory.
    working_dir = ph.path(working_dir).realpath()

    if package_name is None:
        package_name = working_dir.name

    # Unlink working ``.pioenvs`` directory from Conda ``Library`` directory.
    logger.info('Unlink working firmware directories from Conda environment.')
    pio_bin_dir = conda_bin_path()
    fw_bin_dir = pio_bin_dir.joinpath(package_name)

    if fw_bin_dir.exists():
        fw_config_ini = fw_bin_dir.joinpath('platformio.ini')
        if fw_config_ini.exists():
            fw_config_ini.unlink()
        fw_bin_dir.unlink()

    # Unlink working ``lib`` directory from Conda ``Library/include/Arduino``
    # directory.
    logger.info('Unlink working firmware libraries from Conda environment.')
    pio_lib_dir = conda_arduino_include_path()
    working_lib_dir = working_dir.joinpath('lib')

    if working_lib_dir.isdir():
        for path_i in working_lib_dir.listdir():
            pio_path_i = pio_lib_dir.joinpath(path_i.name)
            if pio_path_i.exists():
                pio_path_i.unlink()

    # Remove link to ``dmf_control_board_firmware`` Python package in
    # `conda.pth` in site packages directory.
    logger.info('Unlink working Python directory from Conda environment...')
    ch.conda_exec('develop', '-u', working_dir, verbose=True)
    logger.info(72 * '-' + '\nFinished')
