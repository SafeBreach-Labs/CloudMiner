"""
Setup file for installing our custom pip package
"""
from setuptools import find_packages, setup

setup(
    name="pip",
    version="1.0.0",
    description="CloudMiner custom pip",
    entry_points={
        "console_scripts": [
            "pip=pip.main:_main",
        ],
    },
    package_dir={"": "src"},
    packages=find_packages("src"),
)
