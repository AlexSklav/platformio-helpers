import sys

import setuptools as st

sys.path.insert(0, '.')
import version

st.setup(name='platformio-helpers',
         version=version.getVersion(),
         description='Add description here.',
         keywords='',
         author='Christian Fobel',
         author_email='christian@fobel.net',
         url='https://github.com/wheeler-microfluidics/platformio-helpers',
         license='BSD',
         packages=['platformio_helpers'],
         install_requires=['conda-helpers'],
         # Install data listed in `MANIFEST.in`
         include_package_data=True)
