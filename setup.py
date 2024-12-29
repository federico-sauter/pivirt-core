from setuptools import find_packages, setup

setup(
    name="pivirt-core",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "portalocker",
    ],
)
