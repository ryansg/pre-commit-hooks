from setuptools import setup, find_packages

setup(
    name='puppetfile-dependency-check',
    version='1.0.0',
    description='Checks Puppetfile dependencies against Puppet Forge.',
    py_modules=['check_puppetfile_dependencies'],  # List your Python modules
    install_requires=[
        'semver',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'check_puppetfile_dependencies=check_puppetfile_dependencies:main', #Optional, if you want to run from the command line
        ],
    },
)
