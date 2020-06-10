call conda deactivate
call conda env remove -n exper38
rd /s /q c:\anaconda3\envs\exper38

call conda create -n exper38 python=3.8
call conda activate exper38

call conda install pytorch==1.2.0 torchvision cudatoolkit -c pytorch
call pip install -U xtlib

call pip install -r dev_requirements.txt
