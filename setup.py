import os
from setuptools import setup


# Utility function to read the README.md file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README.md file and 2) it's easier to type in the README.md file than to put a raw
# string in below ...
def read(file_name):
    return open(os.path.join(os.path.dirname(__file__), file_name)).read()


setup(
    name="scclient",
    version="0.3.4",
    author="Justin Nesselrotte",
    author_email="admin@jnesselr.org",
    description="A SocketCluster compatible WebSocket library",
    license="MIT",
    keywords="socket cluster websocket socketcluster",
    url="https://github.com/jnesselr/scclient",
    packages=['scclient', 'tests'],
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    classifiers=[
        "License :: OSI Approved :: BSD License",
    ],
    install_requires=[
        "websocket-client<1.0",

        "pytest>=4.4.0",
        "pytest-cov",
        "codacy-coverage",
        "setuptools",
        "wheel",
        "twine",
    ],
)
