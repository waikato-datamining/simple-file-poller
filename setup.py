# setup.py
# Copyright (C) 2020 University of Waikato, Hamilton, NZ

from setuptools import setup


def _read(f):
    """
    Reads in the content of the file.
    :param f: the file to read
    :type f: str
    :return: the content
    :rtype: str
    """
    return open(f, 'rb').read()


setup(
    name="simple-file-poller",
    description="Simple Python3 library for file polling.",
    long_description=(
        _read('DESCRIPTION.rst') + b'\n' +
        _read('CHANGES.rst')).decode('utf-8'),
    url="https://github.com/waikato-datamining/simple-file-poller",
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Topic :: System :: Filesystems',
        'Programming Language :: Python :: 3',
    ],
    license='MIT License',
    package_dir={
        '': 'src'
    },
    packages=[
        "sfp",
    ],
    version="0.0.2",
    author='Peter Reutemann',
    author_email='fracpete@waikato.ac.nz',
)
