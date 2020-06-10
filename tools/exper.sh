#!/bin/bash
set -v
rm -rf ExperimentTools
git clone https://rfernand2@github.com/msrdl/ExperimentTools
cd ExperimentTools
chmod -w xtlib/helpers/default_config.yaml