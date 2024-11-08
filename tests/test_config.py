import sys
import pymongo

def test_python_version():
    print(f"Python version: {sys.version}")
    assert sys.version_info.major == 3
    assert sys.version_info.minor == 11

def test_pymongo_version():
    print(f"PyMongo version: {pymongo.__version__}")
    assert pymongo.__version__ == "4.10.1"