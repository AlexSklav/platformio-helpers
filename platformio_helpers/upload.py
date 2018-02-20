from __future__ import absolute_import
from __future__ import print_function
import os
import subprocess as sp
import sys
import tempfile as tmp

import path_helpers as ph
import conda_helpers as ch

from . import conda_bin_path, available_environments


def get_arg_parser(project_name=None):
    '''
    Returns a base argument parser for setting PlatformIO upload parameters.

    Useful, for example, to extend with additional arguments for specific
    PlatformIO environments or projects.

    .. versionchanged:: 0.4
        Fix explicit :data:`args` handling.

    Parameters
    ----------
    project_name : str, optional
        Name of PlatformIO project.

    Returns
    -------
    argparse.ArgumentParser
        Argument parser including common arguments for PlatformIO firmware
        uploading.
    '''
    from argparse import ArgumentParser

    parser = ArgumentParser(description='Upload firmware to board.')
    if project_name is not None:
        available_environments_ = available_environments(project_name)
        parser.add_argument('env_name', choices=available_environments_,
                            help='PlatformIO environment to upload.')
    else:
        parser.add_argument('env_name', default=None)
    parser.add_argument('-p', '--port', default=None)
    return parser


def parse_args(project_name=None, args=None):
    '''
    .. versionchanged:: 0.4
        Fix explicit :data:`args` handling.

    Parameters
    ----------
    project_name : str, optional
        Name of PlatformIO project.

    Returns
    -------
    argparse.Namespace
        Resolved arguments parsed from :data:`args`.
    '''
    if args is None:
        args = sys.argv[1:]

    parser = get_arg_parser(project_name=project_name)

    args = parser.parse_args(args)
    return args


def upload_conda(project_name, env_name=None, extra_args=None):
    '''
    Upload pre-built binary from Conda PlatformIO binaries directory to target.

    Parameters
    ----------
    project_name : str
        Name of PlatformIO project.
    env_name : str, optional
        PlatformIO environment name (e.g., ``'teensy31'``).

        If no environment name is specified and only a *single
        environment* is available, automatically select the only
        environment.
    extra_args : list(str), optional
        List of additional arguments to pass to command line upload command.

    See also
    --------
    :func:`upload`
    '''
    extra_args = extra_args or []
    project_bin_dir = conda_bin_path().joinpath(project_name)
    if env_name is None:
        if len(project_bin_dir.dirs()) == 1:
            env_name = project_bin_dir.dirs()[0].name
        else:
            raise ValueError('Platform environment must be specified '
                             'as one of: %s' %
                             [p.name for p in project_bin_dir.dirs()])
    upload(project_bin_dir, env_name, pioenvs_path='.', extra_args=extra_args)


def upload(project_dir, env_name, ini_path='platformio.ini',
           pioenvs_path='.pioenvs', extra_args=None):
    '''
    Upload pre-built binary to target.

    .. versionchanged:: 0.3.1
       Run upload command in activated Conda environment.  See  `issue 3
       <https://github.com/wheeler-microfluidics/platformio-helpers/issues/3>`_.

    Parameters
    ----------
    project_dir : str
        Path to PlatformIO project directory.
    env_name : str
        PlatformIO environment name (e.g., ``'teensy31'``).
    ini_path : str, optional
        Path to PlatformIO configuration file.

        If path is not absolute, it is resolved relative to the specified
        :data:`project_dir`.
    pioenvs_path : str, optional
        Path to ``.pioenvs`` build directory.

        If path is not absolute, it is resolved relative to the specified
        :data:`project_dir`.
    extra_args : list(str), optional
        List of additional arguments to pass to command line upload command.

    See also
    --------
    :func:`upload_conda`
    '''
    extra_args = extra_args or []
    ini_path = ph.path(ini_path)
    if not ini_path.isabs():
        ini_path = project_dir.joinpath(ini_path)
    pioenvs_path = ph.path(pioenvs_path)
    if not pioenvs_path.isabs():
        pioenvs_path = project_dir.joinpath(pioenvs_path)
    ini_path = ini_path.realpath()
    pioenvs_path = pioenvs_path.realpath()

    # Create temporary directory.
    tempdir = ph.path(tmp.mkdtemp(prefix='platformio-%s-' % project_dir.name))
    original_dir = os.getcwd()

    try:
        os.chdir(tempdir)
        env_dir = pioenvs_path.joinpath(env_name)
        temp_env_dir = tempdir.joinpath(env_dir.name)
        ini_path.copy(tempdir)
        env_dir.copytree(temp_env_dir)

        env = os.environ.copy()
        # Set the PlatformIO build environments directory for the upload shell
        # environment.
        env['PLATFORMIO_ENVS_DIR'] = str(tempdir)

        # Run the PlatformIO upload command in an activated Conda environment,
        # e.g., to set `PLATFORMIO_HOME_DIR` and  `PLATFORMIO_LIB_EXTRA_DIRS`
        # environment variables.
        #
        # See [issue #3][1].
        #
        # [1]: https://github.com/wheeler-microfluidics/platformio-helpers/issues/3
        command = (ch.conda_activate_command() + ['&', 'pio', 'run', '-e',
                                                  env_name, '-t', 'upload',
                                                  '-t', 'nobuild'] +
                   list(extra_args))
        print(command)
        sp.check_call(command, env=env, cwd=tempdir, shell=True)
    finally:
        os.chdir(original_dir)
        tempdir.rmtree()
