# setup.py
from setuptools import setup, find_packages

setup(
    name='puppetfile-dependency-check',
    version='1.0.0',
    description='Checks Puppetfile dependencies against Puppet Forge.',
    packages=find_packages(), # will find all packages inside of the root.
    install_requires=[
        'semver',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'check-puppetfile-dependencies=pre_commit_hooks.check-puppetfile-dependencies:main', #Optional, if you want to run from the command line
        ],
    },
)
