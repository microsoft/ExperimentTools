call pushd ..
python -m pip install --user --upgrade setuptools wheel
python setup.py sdist bdist_wheel

python -m pip install --user --upgrade twine
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
call popd

python -m pip install --index-url https://test.pypi.org/simple/ --no-deps xtlib
