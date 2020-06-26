#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# userApp.py: this represents a CPU only ML app.  Many can be run in parallel on a single box.
import sys
import time
import json
import argparse
import numpy as np

# access to the XTLib API
from xtlib.run import Run 

print("start of ML run")
print("this is a WARNING that should appear in the stderr file.", file=sys.stderr)

parser = argparse.ArgumentParser(description='PyTorch MNIST Example')

parser.add_argument('--batch-size', type=int, default=64, metavar='N', help='input batch size for training (default: 64)')
parser.add_argument('--test-batch-size', type=int, default=5000, metavar='N', help='input batch size for testing (default: 5000)')
parser.add_argument('--epochs', type=int, default=4, metavar='N', help='number of epochs to train (default: 4)')
parser.add_argument('--lr', type=float, default=0.01, metavar='LR', help='learning rate (default: 0.01)')
parser.add_argument('--momentum', type=float, default=0.5, metavar='M', help='SGD momentum (default: 0.5)')
parser.add_argument('--no-cuda', action='store_true', default=False, help='disables CUDA training')
parser.add_argument('--seed', type=int, default=0, metavar='S', help='random seed (default: 0)')

# MINI MNIST
parser.add_argument('--train-percent', type=float, default=0.001, metavar='TrainPercent', help='percent of training samples to use (default: .1)')
parser.add_argument('--test-percent', type=float, default=1, metavar='TestPercent', help='percent of test samples to use (default: .5)')
parser.add_argument('--download-only', action='store_true', default=False, help='when specified, app will exit after downloading data')
parser.add_argument('--checkpoint', type=str, default='5 epochs', metavar='CP', help='specifies frequency of checkpoints (15 epochs, 15 mins, etc.')
parser.add_argument('--clear_checkpoint_at_end', type=bool, default=False, help='clear checkpoint at normal end of run')
parser.add_argument('--auto-download', type=int, default=1, help='when =1, app will automatically download data if needed')
parser.add_argument('--eval-model', type=int, default=0, help='when =1, app will skip training, load existing model, and evaluate it')

# CNN
parser.add_argument('--mid-conv', type=int, default=0, help='number of middle conv2d layers')
parser.add_argument('--channels1', type=int, default=20, help='number of output channels for CNN layer 1')
parser.add_argument('--channels2', type=int, default=50, help='number of output channels for CNN layer 2')
parser.add_argument('--kernel-size', type=int, default=5, help='size of CNN kernel')
parser.add_argument('--mlp-units', type=int, default=100, metavar='MU', help='number of units in the MLP layer of the model')

# OPTIMIZER
parser.add_argument('--optimizer', type=str, default="sgd", help='sets the optimizer for the model')
parser.add_argument('--weight-decay', type=float, default=0, help='sets rate of weight decay for weights')


args = parser.parse_args()

# create an instance of XTRunLog to log info for current run
run = Run()

# log hyperparameters to xt
hp_dict = {"seed":args.seed, "batch-size": args.batch_size, "epochs": args.epochs, "lr": args.lr, 
    "momentum": args.momentum, "channels1": args.channels1, "channels2": args.channels2, "kernel_size": args.kernel_size, 
        "mlp-units": args.mlp_units, "weight-decay": args.weight_decay, "optimizer": args.optimizer, 
        "mid-conv": args.mid_conv}

run.log_hparams(hp_dict)

with open("userapp.txt", "at") as tfile:
    tfile.write("starting...\n")

for epoch in range(1, 1+args.epochs):
    accuracy = np.random.random()
    with open("userapp.txt", "at") as tfile:
        tfile.write("epoch=" + str(epoch) + "\n")
        
    print("epoch={}, test-acc={}".format(epoch, accuracy))
    run.log_metrics({"epoch": epoch, "test-acc": accuracy})

    time.sleep(2)   

with open("userapp.txt", "at") as tfile:
    tfile.write("completed.\n")

print("end of ML run.")