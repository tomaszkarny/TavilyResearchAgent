# setup.py
from setuptools import setup, find_packages

setup(
    name="research-assistant",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'python-dotenv',
        'pymongo',
        'tavily-python',
    ],
)