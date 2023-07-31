# coding: utf-8
import os
import logging

import conda_helpers as ch
import path_helpers as ph

from . import (conda_arduino_include_path, conda_bin_path,
               conda_arduino_include_path_05, conda_bin_path_05)


logger = logging.getLogger(__name__)


def link(working_dir: str = None, package_name: str = None) -> None:
    """
    Prepare development environment.

    Perform the following steps:

     - Install build and run-time Conda dependencies.
     - Uninstall package if installed as Conda package.
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

    Version log
    -----------
    .. versionchanged:: 0.3.2
       Create ``.pioenvs`` directory in working directory if it doesn't exist.

    .. versionchanged:: 0.10
       Add support for packages that are split between a Python package and a
       `-dev` package.

    .. versionchanged:: 0.10.1
       Remove any existing links to ``lib`` contents.
    """
    if working_dir is None:
        working_dir = os.getcwd()

    # Resolve absolute working directory.
    working_dir = ph.path(working_dir).realpath()

    if package_name is None:
        package_name = working_dir.name

    # Install build and run-time Conda dependencies.
    logger.info('Install build and run-time Conda dependencies...')
    recipe_dir = working_dir.joinpath('.conda-recipe').realpath()
    ch.conda_exec('install', '-y', '-n', 'root', 'conda-build', verbose=True)
    ch.development_setup(recipe_dir, verbose=True)

    # Uninstall package if installed as Conda package.
    logger.info('Check if Conda package is installed...')
    for package_name_i in (package_name, package_name + '-dev'):
        try:
            version_info = ch.package_version(package_name_i)
        except NameError:
            logger.info(f'`{package_name_i}` package is not installed.')
        else:
            logger.info(f"Uninstall `{package_name_i}=={version_info.get('version')}` package...")
            ch.conda_exec('uninstall', '--force', '-y', package_name_i, verbose=True)

    # Link working ``.pioenvs`` directory into Conda ``Library`` directory.
    logger.info('Link working firmware directories into Conda environment.')
    pio_bin_dir = conda_bin_path()

    fw_bin_dir = pio_bin_dir.joinpath(package_name)

    if not fw_bin_dir.exists():
        pioenvs_dir = working_dir.joinpath('.pioenvs')
        # Create `.pioenvs` directory if it doesn't exist.
        pioenvs_dir.makedirs_p()
        pioenvs_dir.junction(fw_bin_dir)

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
            target_i = pio_lib_dir.joinpath(file_i.name)
            if target_i.exists():
                target_i.unlink()
            file_i.link(target_i)
        for dir_i in working_lib_dir.dirs():
            target_i = pio_lib_dir.joinpath(dir_i.name)
            if target_i.isjunction() or target_i.islink():
                target_i.unlink()
            dir_i.junction(target_i)

    # Link ``dmf_control_board_firmware`` Python package `conda.pth` in site
    # packages directory.
    logger.info('Link working Python directory into Conda environment...')
    ch.conda_exec('develop', working_dir, verbose=True)
    logger.info(72 * '-' + '\nFinished')


def unlink(working_dir: str = None, package_name: str = None) -> None:
    """
    Restore original (i.e., non-development) environment.

    Perform the following steps:

     - Unlink working ``.pioenvs`` directory from Conda ``Library`` directory.
     - TODO Unlink working ``lib`` directory from Conda ``Library`` directory.
     - Unlink Python package from site packages directory.

    See Also
    --------
    :func:`link`

    Version log
    -----------
    .. versionchanged:: 0.6
        Search for firmware directory in ``<prefix>/share/platformio/bin``
        (fall back to deprecated <=0.5 binary directory path).

    .. versionchanged:: 0.10
       Add support for packages that are split between a Python package and a
       `-dev` package.
    """
    if working_dir is None:
        working_dir = os.getcwd()

    # Resolve absolute working directory.
    working_dir = ph.path(working_dir).realpath()

    if package_name is None:
        package_name = working_dir.name

    # Unlink working ``.pioenvs`` directory from Conda ``Library`` directory.
    logger.info('Unlink working firmware directories from Conda environment.')

    # Search for firmware directory (fall back to deprecated <=0.5 binary
    # directory path).
    for bin_path_i in (conda_bin_path(), conda_bin_path_05()):
        fw_bin_dir = bin_path_i.joinpath(package_name)
        if fw_bin_dir.exists():
            break
    else:
        fw_bin_dir = None

    if fw_bin_dir is not None:
        fw_config_ini = fw_bin_dir.joinpath('platformio.ini')
        if fw_config_ini.exists():
            fw_config_ini.unlink()
        fw_bin_dir.unlink()

    # Unlink working `lib` directory from Conda
    # `<prefix>/share/platformio/include` directory
    # (fall back to deprecated <=0.5 include directory path).
    logger.info('Unlink working firmware libraries from Conda environment.')

    package_names = (package_name, package_name + '-dev')
    for include_path_i in (conda_arduino_include_path(), conda_arduino_include_path_05()):
        for package_name_j in package_names:
            include_dir_j = include_path_i.joinpath(package_name_j)
            if include_dir_j.exists():
                break
    else:
        include_dir = None

    working_lib_dir = working_dir.joinpath('lib')

    if include_dir is not None and working_lib_dir.isdir():
        for path_i in working_lib_dir.listdir():
            pio_path_i = include_dir.joinpath(path_i.name)
            if pio_path_i.exists():
                pio_path_i.unlink()

    # Remove link to Python package in `conda.pth` in site packages directory.
    logger.info('Unlink working Python directory from Conda environment...')
    ch.conda_exec('develop', '-u', working_dir, verbose=True)
    logger.info(72 * '-' + '\nFinished')
