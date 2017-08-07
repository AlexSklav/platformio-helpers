import os
import subprocess as sp
import sys
import tempfile as tmp

import path_helpers as ph

from . import conda_bin_path


def get_arg_parser():
    from argparse import ArgumentParser

    parser = ArgumentParser(description='Upload firmware to board.')
    parser.add_argument('env_name', default=None)
    parser.add_argument('-p', '--port', default=None)
    return parser


def parse_args(args=None):
    """Parses arguments, returns (options, args)."""
    if args is None:
        args = sys.argv

    parser = get_arg_parser()

    args = parser.parse_args()
    return args


def upload_conda(project_name, env_name=None, extra_args=None):
    '''
    Upload pre-built binary from Conda PlatformIO binaries directory
    to target.

    Parameters
    ----------
    project_dir : str
        Path to PlatformIO project directory.
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
        env['PLATFORMIO_ENVS_DIR'] = str(tempdir)

        # Temporary workaround until we can figure out a way to
        # launch MicroDrop in a way that runs the
        # %CONDA_PREFIX%\etc\conda\activate.d scripts. See [1]
        #
        # [1]: https://github.com/wheeler-microfluidics/platformio-helpers/issues/3
        import conda_helpers as ch
        env['PLATFORMIO_HOME_DIR'] = str(ch.conda_prefix() /
            'share' / 'platformio')
        env['PLATFORMIO_LIB_EXTRA_DIRS']= str(ch.conda_prefix() /
            'Library' / 'include' / 'Arduino')
 
        command = ('pio run -e %s -t upload -t nobuild %s' %
                   (env_name, ' '.join(extra_args)))
        print command
        sp.check_call(command, env=env, cwd=tempdir)
    finally:
        os.chdir(original_dir)
        tempdir.rmtree()
