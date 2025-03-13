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
    entry_points={
        'console_scripts': [
            'check-puppetfile-dependencies = pre_commit_hooks.check_puppetfile_dependencies:main',  # Corrected entry point
        ],
    },
)
