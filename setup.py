from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))


with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
requirements = []
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    requirements = f.read().splitlines()
setup(
    name='CatBot',

    version='1.0',

    description="CatBot - You've cat to be kitten me.",

    long_description=long_description,

    url='https://github.com/yoshimi777/CatBot',

    license='MIT',

    classifiers=[
        'Environment :: Console',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5'
        'Programming Language :: Python :: 3.6'
    ],
    python_requires='>=3.5',

    keywords='discord chatbot',

    packages=find_packages(),
    include_package_data=True,

    install_requires=requirements,


)