##
## Copyright (c) Microsoft Corporation.
## Licensed under the MIT license.
##
cd ..
# ---- update tools everything ----
python -m pip install --user --upgrade setuptools wheel twine

# ---- remove previous build directories ----
rm -rf dist
rm -rf build
rm -rf xtlib.egg-info

# ---- build SOURCE DIST (*.tar.gz) and WHEEL (*.whl) ----
python setup.py sdist bdist_wheel

# ---- updload file from DIST folder to PYPI ----
python -m twine upload dist/*

