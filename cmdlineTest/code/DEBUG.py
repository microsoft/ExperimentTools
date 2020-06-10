#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# debug_cmd.py: run an XT command under the debugger
import os
import shutil

from xtlib import utils
import xtlib.xt_run as xt_run

def test_cmd(cmd, capture_output=False):
    print("debug cmd: {}".format(cmd))
    return xt_run.main(cmd, disable_quickstart = True, capture_output=capture_output, mini=False)

#test_cmd( 'xt list blobs /' )
#test_cmd( 'xt --seed=52342342 --nodes=2 --max-runs=10 --target=batch --search-type=random --dry-run=1 run code/miniMnist.py --epochs=10 --lr=[.1, .3, .5] --optimizer=[sgd, adam] --seed=[$randint()]' )
#test_cmd(' xt list work ')

#test_cmd( 'xt --target=batch run code/miniMnist.py' )
#test_cmd( ' xt --runs=2 run code\miniMnist.py  --lr=[.1,.2,.3] --epochs=7 ' )

#test_cmd(" xt --target=batch --data-action=download --model-action=download run code\\miniMnist.py --auto-download=0 --eval-model=1 ")
#test_cmd(' xt --runs=3 --search-type=bayesian --target=vm10 run code\miniMnist.py --lr=[.1, .2, .3, .4, .5] --optimizer=[sgd, adam] ')

#test_cmd(' xt cancel all batch ')
#test_cmd(' xt plot job6908 train-acc, test-acc --aggregate=mean --group-by=job --error-bars=var')

#test_cmd(' xt plot job6908 train-acc, test-acc --aggregate=mean --group-by=node --break-on=group --error-bars=var ')

#test_cmd( "xt list runs --status=cancelled" )
test_cmd(" xt run --target=aml code/miniMnist.py " )
#test_cmd("xt list runs ")
#test_cmd("xt extract run5723.3 xxx")

#test_cmd(" xt plot job7647 train-acc --color-map=jet --color-steps=5")
#test_cmd(" xt plot job7647 train-acc, test-acc --smooth=.5 --shadow-type=pre-smooth --break=col ")
#test_cmd('xt --target=batch --runs=15 --nodes=3 run code\miniMnist.py --epochs=200')
#test_cmd(' xt attach $lastrun  --escape=10')

#test_cmd(' xt attach $lastrun ')
#test_cmd( 'xt --target=local run rl_nexus/run.py' )
#test_cmd(" xt --show --target=vm10 --cluster=rr1 --vc=resrchvc --sku=g1 run train_from_scratch.sh " )
#test_cmd(' xt view controller status job6272  ')
#test_cmd( 'xt --target=batch run code/miniMnist.py --epochs=5000' )

#test_cmd( 'xt attach $lastrun  --escape=10    ' )
#test_cmd("xt stop controller")