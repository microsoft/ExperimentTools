call conda deactivate
call conda env remove -n exper
rd /s /q c:\anaconda3\envs\exper

rem --- caution: python 3.6.10 is corrupted as of 3/18/2020, so use 3.6.9 ----
call conda create -n exper python=3.6.9
call conda activate exper

call conda install pytorch==1.2.0 torchvision cudatoolkit -c pytorch
call pip install -U xtlib

call pip install -r dev_requirements.txt

