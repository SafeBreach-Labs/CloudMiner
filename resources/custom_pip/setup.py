from setuptools import find_packages, setup

setup(
    name="pip",
    version="99.99.99",
    description="CloudMiner custom pip",
    entry_points={
        "console_scripts": [
            "pip=pip.main:main",
        ],
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
)
