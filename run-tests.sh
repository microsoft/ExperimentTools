pip install -r dev_requirements.txt
pip install -e .
python prepare-test-environment.py
XT_GLOBAL_CONFIG=tests/xt_config.yaml xt help
XT_GLOBAL_CONFIG=tests/xt_config.yaml pytest tests/test_feature.py -v -s --junitxml=test-results.xml
