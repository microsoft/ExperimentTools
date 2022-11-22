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
    "azure-batch==8.0.0",
    "azure-identity==1.2.0",
    "azure-keyvault==4.0.0",
    "azure-storage-blob==2.1.0",
    "azureml-sdk==1.0.69",
    "azureml-widgets==1.0.69.1",
 
    # other xtlib dependencies
    "PyYAML==5.3.1",            # for YAML parser
    "arrow==0.14.0",            # avoid annoying warning msgs in 0.14.4, 
    "future==0.18.2",           # temporarily needed by tensorboard
    "grpcio==1.29.0",           # tensorboard requirement
    "hyperopt==0.2.4",          # for bayesian hyperparam searching
    "matplotlib==3.2.1",        # for plotting (exploring their use)
    "numpy==1.18.1",            # general use
    "pandas==1.0.4",            # for DataFrame 
    "paramiko==2.7.1",          # SSH session-level API (fast access to remote box)
    "pillow==9.3.0",
    "psutil==5.7.0",            # for querying and killing processes (XT controller)
    "ptvsd==4.3.2",             # for attaching debugger to python processes
    "pymongo==3.10.1",          # for reporting/querying runs database (Azure MongoDB API)
    "python-interface==1.6.0",  # for specifying provider interface classes
    "rpyc==4.1.2",              # rpyc requires its versions to match (client/remote)
    "ruamel.yaml==0.15.89",
    "seaborn==0.10.1",          # for plotting styles
    "tensorboard==2.1.0",       # for logging to Tensorboard
    "tqdm==4.46.1",             # for command line progress displays (still used?)
    "watchdog==0.9.0"           # for watching file we want to copy to grok server (watchdog 0.10.0 has setup error)
]

if platform.system() == 'Windows':
    requirements.append('pywin32==227')                 # windows only package
elif platform.system() == 'Linux':
    requirements.append('scikit-learn==0.22.2.post1')   # required by shap, azureml-explain-model
    requirements.append('pyasn1==0.4.8')                # linux only package


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
            "sphinx==3.0.4",            # for docs
            "sphinx_rtd_theme==0.4.3"   # for docs
        ], ),

    # used to identify the package to various searches
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
