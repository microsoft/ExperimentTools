#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
import platform
import setuptools
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install

# this must be incremented every time we push an update to pypi (but not before)
VERSION ="1.0.0"

# supply contents of our README file as our package's long description
with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = [
    # azure SDK
    "azureml-sdk==1.0.69",
    "azure-storage-blob==2.1.0",
    "azure-identity==1.2.0",
    "azure-keyvault==4.0.0",
    "azure-batch==8.0.0",
    "azureml-widgets==1.0.69.1",

    # other xtlib dependencies
    "pillow==6.2.2",
    "numpy",  # general use
    "arrow==0.14.0",  # avoid annoying warning msgs in 0.14.4, 
    "rpyc==4.1.2",  # rpyc requires its versions to match (client/remote)
    "future",  # temporarily needed by tensorboard
    "watchdog==0.9.0",  # for watching file we want to copy to grok server (watchdog 0.10.0 has setup error)
    "hyperopt",  # for bayesian hyperparam searching
    "pymongo",  # for reporting/querying runs database (Azure MongoDB API)
    "tqdm",  # for command line progress displays (still used?)
    "tensorboard==2.1.0",  # for logging to Tensorboard
    "psutil",  # for querying and killing processes (XT controller)
    "ptvsd",  # for attaching debugger to python processes
    "matplotlib",  # for plotting (exploring their use)
    "seaborn",     # for plotting styles
    "pandas",      # for DataFrame 
    "PyYAML>=5.1.0",   # for YAML parser
    "python-interface",    # for specifying provider interface classes
    "paramiko",         # SSH session-level API (fast access to remote box)

    #"torch==1.2.0",
    # "torchvision==0.4.1",
    #  "pillow==6.2.0",  
    "grpcio>=1.24.3",   # tensorboard requirement
    "ruamel.yaml==0.15.89",
]

if platform.system() == 'Windows':
    requirements.append('pywin32')  # windows only package
elif platform.system() == 'Linux':
    requirements.append('scikit-learn') # required by shap, azureml-explain-model
    requirements.append('pyasn1>=0.4.6') # linux only package


setuptools.setup(
    # this is the name people will use to "pip install" the package
    name="xtlib",

    version=VERSION, 
    author="Roland Fernandez",
    author_email="rfernand@microsoft.com",
    description="A set of tools for organizing and scaling ML experiments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rfernand2",

    # this will find our package "xtlib" by its having an "__init__.py" file
    packages=[
        "xtlib", "xtlib.helpers", "xtlib.hparams", "xtlib.backends", "xtlib.templates", 
        "xtlib/public_certs", "xtlib/demo_files", "xtlib/demo_files/code", "xtlib.storage",
        "xtlib/help_topics/topics", "xtlib/help_topics/internals", "xtlib/psm"
    ],  # setuptools.find_packages(),

    entry_points={
        'console_scripts': ['xt = xtlib.xt_run:main'],
    },

    # normally, only *.py files are included - this forces our YAML file and controller scripts to be included
    package_data={'': ['*.yaml', '*.sh', '*.bat', '*.txt', '*.rst', '*.crt', '*.json']},
    include_package_data=True,

    # the packages that our package is dependent on
    install_requires=requirements,
    extras_require=dict(
        dev=[
            "sphinx",  # for docs
            "sphinx_rtd_theme"  # for docs
        ], ),

    # used to identify the package to various searches
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)