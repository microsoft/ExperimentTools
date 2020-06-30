pip install -e .
pip install -r dev_requirements.txt
python prepare-test-environment.py
# XT_GLOBAL_CONFIG=tests/xt_config.yaml pytest tests/test_storage_provider.py -s
