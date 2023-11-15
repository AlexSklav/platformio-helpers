# coding: utf-8
import os
import sys
import platform

import subprocess as sp
import tempfile as tmp
from typing import Optional, List, Callable

import colorama as co
import conda_helpers as ch
import path_helpers as ph

from argparse import ArgumentParser
from . import conda_bin_path, conda_bin_path_05, available_environments


class UploadError(Exception):
    def __init__(self, command, working_dir):
        self.command = command
        self.working_dir = working_dir
        message = f'\nUpload error.\nWorking directory: `{self.working_dir}`\nCommand: `{self.command}`'
        super(UploadError, self).__init__(message)


def get_arg_parser(project_name: Optional[str] = None) -> ArgumentParser:
    """
    Returns a base argument parser for setting PlatformIO upload parameters.

    Useful, for example, to extend with additional arguments for specific
    PlatformIO environments or projects.

    Parameters
    ----------
    project_name : str, optional
        Name of PlatformIO project.

    Returns
    -------
    argparse.ArgumentParser
        Argument parser including common arguments for PlatformIO firmware
        uploading.

    Version log
    -----------
    .. versionchanged:: 0.4
        Fix explicit :data:`args` handling.
    """

    parser = ArgumentParser(description='Upload firmware to board.')
    if project_name is not None:
        available_environments_ = available_environments(project_name)
        parser.add_argument('env_name', choices=available_environments_, help='PlatformIO environment to upload.')
    else:
        parser.add_argument('env_name', default=None)
    parser.add_argument('-p', '--port', default=None)
    return parser


def parse_args(project_name: Optional[str] = None, args: Optional[List[str]] = None) -> ArgumentParser:
    """
    Parameters
    ----------
    project_name : str, optional
        Name of PlatformIO project.

    Returns
    -------
    argparse.Namespace
        Resolved arguments parsed from :data:`args`.

    Version log
    -----------
    .. versionchanged:: 0.4
        Fix explicit :data:`args` handling.
    """
    if args is None:
        args = sys.argv[1:]

    parser = get_arg_parser(project_name=project_name)

    args = parser.parse_args(args)
    return args


def upload_conda(project_name: str, env_name: Optional[str] = None, extra_args: Optional[List[str]] = None,
                 **kwargs) -> None:
    """
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

    Version log
    -----------
    .. versionchanged:: 0.6
        Search for firmware directory in ``<prefix>/share/platformio/bin``
        (fall back to deprecated <=0.5 binary directory path).

    .. versionchanged:: 0.9
        Pass unknown keyword arguments to :func:`upload` function.
    """
    extra_args = extra_args or []

    for bin_path_i in (conda_bin_path(), conda_bin_path_05()):
        project_bin_dir = bin_path_i.joinpath(project_name)
        if project_bin_dir.isdir():
            break
    else:
        raise IOError(f'No binaries found for project `{project_name}`.')

    if env_name is None:
        if len(project_bin_dir.dirs()) == 1:
            env_name = project_bin_dir.dirs()[0].name
        else:
            raise ValueError(f'Platform environment must be specified'
                             f' as one of: {[p.name for p in project_bin_dir.dirs()]}')
    upload(project_bin_dir, env_name, pioenvs_path='.', extra_args=extra_args, **kwargs)


def upload(project_dir: str, env_name: str, ini_path: Optional[str] = 'platformio.ini',
           pioenvs_path: Optional[str] = '.pioenvs', extra_args: Optional[List[str]] = None,
           on_error: Optional[Callable] = None) -> None:
    """
    Upload pre-built binary to target.

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
    on_error : callable, optional
        Call-back function called if upload returns non-zero return code,
        accepting a :class:`UploadError` instance as the only argument.

    See also
    --------
    :func:`upload_conda`

    Version log
    -----------
    .. versionchanged:: 0.3.1
       Run upload command in activated Conda environment.  See  `issue 3
       <https://github.com/wheeler-microfluidics/platformio-helpers/issues/3>`_.

    .. versionchanged:: 0.5.2
        Copy environments to ``.pioenvs`` sub-directory instead of using
        ``PLATFORMIO_ENVS_DIR`` environment variable (see issue #5).

    .. versionchanged:: 0.9
        Add optional ``on_error`` call-back argument.

    .. versionchanged:: 0.10.1
        Run ``pio`` wrapped using ``.conda-recipe-wrappers`` package, which performs a
        *"pseudo-activation"* of the Conda environment, but a) is >50x faster
        than *actually* activating the environment; and b) supports running in
        a packaged environment where no ``.conda-recipe`` executable is on the system
        path.
    """
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
    tempdir = ph.path(tmp.mkdtemp(prefix=f'platformio-{project_dir.name}-'))
    original_dir = os.getcwd()

    try:
        # Change into temporary directory, since PlatformIO tools look for
        # `.pioenvs` in current working directory.
        os.chdir(tempdir)
        print(f'{co.Fore.MAGENTA}Working directory: {co.Fore.WHITE}{tempdir}')
        env_dir = pioenvs_path.joinpath(env_name)
        temp_env_dir = tempdir.joinpath('.pioenvs', env_dir.name)
        ini_path.copy(tempdir)
        temp_env_dir.parent.makedirs_p()
        env_dir.copytree(temp_env_dir)

        # Run the PlatformIO upload command in a pseudo-activated Conda
        # environment, e.g., to set `PLATFORMIO_HOME_DIR` and
        # `PLATFORMIO_LIB_EXTRA_DIRS` environment variables.
        #
        # See [issue #3][1].
        #
        # [1]: https://github.com/wheeler-microfluidics/platformio-helpers/issues/3
        command = [ch.conda_prefix().joinpath('Scripts' if platform.system()
                                                           == 'Windows' else 'bin',
                                              'wrappers', '.conda-recipe', 'run-in'),
                   'pio', 'run', '-e', env_name, '-t', 'upload', '-t',
                   'nobuild'] + list(extra_args)

        print(f'{co.Fore.MAGENTA}Executing: {co.Fore.WHITE}{sp.list2cmdline(command)}')

        returncode, stdout, stderr = ch.with_loop(ch.run_command)(command, shell=True, verbose=True)
        if returncode != 0:
            print(f'{co.Back.RED}{co.Fore.WHITE}Error uploading:')
            print(f'{co.Back.RESET}{co.Fore.RED}{stderr}')

            exception = UploadError(tempdir, sp.list2cmdline(command))
            if on_error is not None:
                on_error(exception)
            else:
                raise exception
    finally:
        os.chdir(original_dir)
        tempdir.rmtree()
