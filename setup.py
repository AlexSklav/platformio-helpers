# -*- encoding: utf-8 -*-
from setuptools import setup

import versioneer

setup(name='platformio-helpers',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='Helpers functions, etc. for PlatformIO projects.',
      keywords='',
      author='Christian Fobel',
      author_email='christian@fobel.net',
      url='https://github.com/sci-bots/platformio-helpers',
      license='BSD',
      packages=['platformio_helpers'],
      # Install data listed in `MANIFEST.in`
      include_package_data=True)
