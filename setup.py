from setuptools import setup, find_packages

setup(
    name='puppetfile-dependency-check',
    version='1.0.0',
    description='Checks Puppetfile dependencies against Puppet Forge.',
    packages=find_packages(),
    install_requires=[
        'semver',
        'requests',
    ],
)
