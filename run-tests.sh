pip install -r dev_requirements.txt
pip install -e .

# if [ "$PHILLY_TESTS" = "true" ]; then
#    pip install xtlib-internal -i https://pkgs.dev.azure.com/msresearch/e709de22-dd8c-4b66-a84e-688f2a391d01/_packaging/eXperimentTools/pypi/simple/
#    xtlib-internal config --reset
# fi

# pip install keyring artifacts-keyring
# python prepare-test-environment.py
# XT_GLOBAL_CONFIG=tests/xt_config.yaml xt help
XT_GLOBAL_CONFIG=tests/xt_config.yaml pytest tests/ -v --junitxml=test-results.xml
# XT_GLOBAL_CONFIG=tests/xt_config.yaml xt run --target=philly tests/fixtures/miniMnist.py
# curl https://philly
