pip install -r dev_requirements.txt
pip install -e .
python prepare-test-environment.py
XT_GLOBAL_CONFIG=tests/xt_config.yaml xt help
XT_GLOBAL_CONFIG=tests/xt_config.yaml python -c 'from xtlib import xt_cmds; xt_cmds.main("xt run --target=aml tests/fixtures/miniMnist.py")'
# XT_GLOBAL_CONFIG=tests/xt_config.yaml xt list blobs
# XT_GLOBAL_CONFIG=tests/xt_config.yaml xt run --target=local tests/fixtures/miniMnist.py
# XT_GLOBAL_CONFIG=tests/xt_config.yaml pytest tests/ -s --junitxml=test-results.xml
# XT_GLOBAL_CONFIG=tests/xt_config.yaml pytest tests/ -v --junitxml=test-results.xml
