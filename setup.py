
from setuptools import setup

setup(
        name='syncenv',
        packages=['syncenv'],
        author='Huizi Mao',
        author_email='ralphmao95@gmail.com',
        entry_points={
            'console_scripts': [
                'se = syncenv.syncenv:main']
            }
        )
