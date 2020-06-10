#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# miniMnist.py: ML program for testing XT
# adapted from: https://github.com/pytorch/examples/blob/master/mnist/main.py
# adapted to use a subset of the MNIST train/test data (for faster training/eval runs)

import os
import sys
import math
import time
import yaml
import random
import argparse

print("------ miniMnist starting ------")
print("current conda=", os.getenv("CONDA_DEFAULT_ENV"))

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
import torchvision
import PIL

from xtlib import utils
from xtlib import errors
from xtlib import constants
from xtlib import file_utils

hvd = None     # imported on demand

# AML 
# this app uses the XT logging APIs to log to AML

def parse_cmdline_args():
    # Training settings
    parser = argparse.ArgumentParser(description='PyTorch MNIST Example')

    parser.add_argument('--batch-size', type=int, default=64, metavar='N', help='input batch size for training (default: 64)')
    parser.add_argument('--test-batch-size', type=int, default=5000, metavar='N', help='input batch size for testing (default: 5000)')
    parser.add_argument('--epochs', type=int, default=4, metavar='N', help='number of epochs to train (default: 4)')
    parser.add_argument('--lr', type=float, default=0.01, metavar='LR', help='learning rate (default: 0.01)')
    parser.add_argument('--dropout', type=float, default=0, help='dropout rate (default: 0)')
    parser.add_argument('--momentum', type=float, default=0.5, metavar='M', help='SGD momentum (default: 0.5)')
    parser.add_argument('--cuda', type=int, default=1, help='enables/disables use of GPU resources ')
    parser.add_argument('--seed', type=int, default=0, metavar='S', help='random seed (default: 0)')
    parser.add_argument('--save-model', action='store_true', default=False, help='For Saving the current Model')
    parser.add_argument('--gpu', type=int, default=0, help='specify which gpu to use')
    parser.add_argument('--parallel', type=int, default=0, help='when specified, will do parallel training on all gpus')
    parser.add_argument('--distributed', type=int, default=0, help='when specified, will do distributed training on all nodes')
    parser.add_argument('--data', type=str, default="data/mnist", metavar='N', help='where to get/store MNIST data')
    parser.add_argument('--search-api', type=float, default=0, help='should app call search API?')
    parser.add_argument('--raise-error', type=float, default=0, help='when =1, app will intentionaly raise error')

    # LOGGING
    parser.add_argument('--log-interval', type=int, default=1, metavar='N', help='how many epochs to wait before logging training status')
    parser.add_argument('--tensorboard', type=int, default=1, metavar='N', help='if tensorboard logging is enabled')
    parser.add_argument('--xtlib', type=int, default=1, metavar='N', help='if xtlib usage is enabled')
    parser.add_argument('--env-vars', type=int, default=1, metavar='N', help='=1 to show name/value of all environment variables')
    parser.add_argument('--tag-job', type=int, default=0, help='set =1 to tag associated with plotted_metrics=test-acc')

    # MINI MNIST
    parser.add_argument('--train-percent', type=float, default=0.001, metavar='TrainPercent', help='percent of training samples to use (default: .001)')
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
    return args

class SimpleCNN(nn.Module):
    def __init__(self, num_mid_conv=0, channels1=20, channels2=50, kernel_size=5, mlp_units=500, dropout=0):
        super(SimpleCNN, self).__init__()

        # input to conv1: channels=1 (grayscale), W=28, H=28
        self.conv1 = nn.Conv2d(1, channels1, kernel_size, 1)
        self.dropout = dropout

        for i in range(num_mid_conv):
            name = "conv" + str(2+i)
            convX = nn.Conv2d(channels1, channels1, kernel_size, 1, padding=2)
            setattr(self, name, convX)

        self.conv_last = nn.Conv2d(channels1, channels2, kernel_size, 1)
        self.channels2 = channels2
        self.num_mid_conv = num_mid_conv

        sz1 = 28-kernel_size+1
        assert sz1 % 2 == 0
        pool1 = sz1 // 2

        sz2 = pool1-kernel_size+1
        assert sz2 % 2 == 0
        pool2 = sz2 // 2

        self.factor = pool2*pool2*channels2
        #print("sz1=", sz1, ", sz2=", sz2, ", factor=", self.factor)
        
        self.fc1 = nn.Linear(self.factor, mlp_units)
        self.fc2 = nn.Linear(mlp_units, 10)


    def forward(self, input):
        dropout = self.dropout

        # first CONV2D
        x = F.relu(self.conv1(input))

        # middle CONV2D's
        for i in range(self.num_mid_conv):
            name = "conv" + str(2+i)
            convX = getattr(self, name)
            x = F.relu(convX(x))
            if dropout:
                x = F.dropout(x, dropout)

        x = F.max_pool2d(x, 2, 2)
        x = F.relu(self.conv_last(x))
        if dropout:
            x = F.dropout(x, dropout)
        x = F.max_pool2d(x, 2, 2)
        x = x.view(-1, 4*4*self.channels2)
        x = F.relu(self.fc1(x))
        if dropout:
            x = F.dropout(x, dropout)
        x = self.fc2(x)

        # print("\tIn Model: input size", input.size(),
        #     "output size", x.size())     

        return F.log_softmax(x, dim=1)
    
class MLP(nn.Module):
    def __init__(self, sizes=[3200]):
        super(MLP, self).__init__()

        input_size = 28*28
        self.sizes = sizes

        for i, size in enumerate(self.sizes):
            fcx = nn.Linear(input_size, size)
            setattr(self, "fc" + str(i), fcx)
            input_size = size

            bnx = nn.BatchNorm1d(size)
            setattr(self, "bn" + str(i), bnx)

        self.last = nn.Linear(input_size, 10)

    def forward(self, input):
        # flatten
        do_percent = .1

        x = input.view(-1, 28*28)
        #x = F.dropout(x, do_percent)

        for i in range(len(self.sizes)):
            fcx = getattr(self, "fc" + str(i))
            x = fcx(x)
            bnx = getattr(self, "bn" + str(i))
            x = bnx(x)
            #x = F.dropout(x, do_percent)

        x = self.last(x)
        #x = F.dropout(x, do_percent)

        return F.log_softmax(x, dim=1)

class Trainer():
    def __init__(self):
        pass

    def train(self, args, model, device, optimizer, epoch):
        model.train()
        total_correct = 0
        total = 0
        steps = 0

        for batch_idx, (data, target) in enumerate(self.train_loader):
            data, target = data.to(device), target.to(device)
            optimizer.zero_grad()
            output = model(data)
            loss = F.nll_loss(output, target)
            loss.backward()
            optimizer.step()

            # compute train-acc
            pred = output.argmax(dim=1, keepdim=True) # get the index of the max log-probability
            correct = pred.eq(target.view_as(pred)).sum().item()
            total_correct += correct
            total += len(data)
            steps += 1

        return loss.item(), total_correct/total, steps, len(data), loss, total_correct, total

    def test(self, args, model, device):
        test_loader = self.test_loader

        model.eval()
        test_loss = 0
        correct = 0
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(device), target.to(device)
                output = model(data)
                test_loss += F.nll_loss(output, target, reduction='sum').item() # sum up batch loss
                pred = output.argmax(dim=1, keepdim=True) # get the index of the max log-probability
                correct += pred.eq(target.view_as(pred)).sum().item()

        test_loss /= len(test_loader.dataset)
        test_acc = correct / len(test_loader.dataset)

        print('Test set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
            test_loss, correct, len(test_loader.dataset),
            100. * test_acc))

        return test_loss, test_acc

    def get_dataset(self, data_dir, train, auto_download):
        ds = datasets.MNIST(data_dir, train=train, download=auto_download, transform=transforms.Compose([
            # PIL transforms
            #transforms.Resize(22),       
            #transforms.Resize(28),       
            #transforms.RandomCrop(28),
            #transforms.RandomHorizontalFlip(),
            #transforms.RandomRotation(3, resample=PIL.Image.BILINEAR),
            # TENSOR transforms
            transforms.ToTensor(), 
            transforms.Normalize((0.1307,), (0.3081,)),

            # requires pytorch 1.2
            #transforms.RandomErasing(p=.25, value="random"),
            ]))
        return ds

    def sample_mnist(self, data_dir, train, rand, percent, auto_download):

        # get MNIST data
        ds = self.get_dataset(data_dir, train, auto_download)

        # support previous torchvision version as well as current  (AML workaround)
        if hasattr(ds, "data"):
            data_attr = "data"
            target_attr = "targets"
        elif train:
            data_attr = "train_data"
            target_attr = "train_labels"
        else:
            data_attr = "test_data"
            target_attr = "test_labels"

        # extract data and targets
        data = getattr(ds, data_attr)
        targets = getattr(ds, target_attr)

        count = len(data)
        indexes = list(range(count))

        rand.shuffle(indexes)

        samples = int(count * percent)
        indexes = indexes[0:samples]
        
        # update data
        setattr(ds, data_attr, data[indexes])

        # update targets
        setattr(ds, target_attr, targets[indexes])

        which = "TRAIN" if train else "TEST"
        print("Sampled " + which + " data: ", len(data), ", targets=", len(targets))
        return ds

    def save_model(self, model, fn):
        # ensure output dir exists
        dir = os.path.dirname(fn)
        if not os.path.exists(dir):
            os.makedirs(dir)

        torch.save(model.state_dict(), fn)

    def text_log(self, msg):
        with open(self.fn_text_log, "a") as outfile:
            outfile.write(msg + "\n")

    def log_stats_and_test(self, epoch, steps, data_len, loss, total_correct, total, model, device, 
        checkpoint_freq, run, train_loss, train_acc, args):

        msg = 'Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}\tAcc: {:.6f}'.format(
            epoch, steps * data_len, len(self.train_loader.dataset),
            100. * steps / len(self.train_loader), loss.item(), total_correct/total)

        # print to console
        print(msg)

        # log to simple text logger
        self.text_log(msg)

        if checkpoint_freq and run and run.store:
            if checkpoint_units == "epochs" and epoch % checkpoint_freq == 0:
                cp_now = True
            elif checkpoint_units == "mins" and time.time() - last_checkpoint > checkpoint_freq*60:
                cp_now = True
            else:
                cp_now = False

            if cp_now:
                checkpoint_count += 1
                print("checkpointing model (#{})\n".format(checkpoint_count))

                save_model(model, fn_checkpoint)   
                run.set_checkpoint({"epoch": epoch}, fn_checkpoint)
                last_checkpoint = time.time()

        if run:
            # log TRAINING stats
            run.log_metrics({"epoch": epoch, "loss": train_loss, "acc": train_acc}, step_name="epoch", stage="train")

            # log EVAL/TEST stats half as often
            if (epoch / args.log_interval ) % 2 == 0:
                test_loss, test_acc = self.test_model_and_log_metrics(run, model, device, epoch, args)

                # early stopping
                if math.isnan(test_loss):
                    run.log_event("early_stopping", {"reason": "loss_is_nan"})
                    # exit without error
                    sys.exit(0)

    def test_model_and_log_metrics(self, run, model, device, epoch, args):
        # TEST the model
        test_loss, test_acc = self.test(args, model, device)
        
        # log TEST METRICS
        #print("test_loss=", test_loss, ", test_acc=", test_acc)
        run.log_metrics({"epoch": epoch, "loss": test_loss, "acc": test_acc}, step_name="epoch", stage="test")

        return test_loss, test_acc

    def train_test_loop(self, run, model, device, optimizer, start_epoch, checkpoint_freq, 
        args):

        total_steps = 0
        start = time.time()
        print("train_test_loop: start_epoch={} end_epoch={}\n".format(start_epoch, args.epochs + 1))

        for epoch in range(start_epoch, args.epochs + 1):

            # train an epoch
            train_loss, train_acc, steps, data_len,  loss, total_correct, total = \
                self.train(args, model, device, optimizer, epoch)

            total_steps += steps

            if epoch % args.log_interval == 0:
                elapsed = time.time() - start
                #print("{} epoch(s) training took: {:.2f} secs".format(args.log_interval, elapsed))

                self.log_stats_and_test(epoch, steps, data_len, loss, total_correct, total, model, device, 
                    checkpoint_freq, run, train_loss, train_acc, args)
            
                start = time.time()

    def init_xt_run(self, logging, tb_path, args):
        # init xtlib
        self.run = None

        if args.xtlib and (os.getenv("XT_RUN_NAME") or tb_path):
            # access to the XTLib API
            from xtlib.run import Run as XTRun

            # create an instance of XTRunLog to log info for current run
            print("---> tb_path=", tb_path)
            self.run = XTRun(xt_logging=logging, aml_logging=logging, checkpoints_enabled=logging, tensorboard_path=tb_path)

            #utils.debug_break()

            if args.tag_job:
                self.run.tag_job( {"plotted_metric": "test_acc"} )

            # if "call search API" test was specified and if we are running under XT
            if args.search_api and run.run_name:
                fn_sweeps = os.path.join(file_utils.get_my_file_dir(__file__), "miniSweeps.yaml")
                sweeps = file_utils.load_yaml(fn_sweeps)
                hp_space_dict = sweeps[constants.HPARAMS_DIR]
                print("hp_space_dict=", hp_space_dict)
                search_type = "random"

                hp_set = run.get_next_hp_set_in_search(hp_space_dict, search_type=search_type)
                print("hp_set=", hp_set)

                # apply to args
                for name, value in hp_set.items():
                    setattr(args, name, value)

    def init_datasets(self, data_dir, use_cuda, args):
        kwargs = {'num_workers': 0, 'pin_memory': True} if use_cuda else {}

        # load subset of training and test data
        ds_train = self.sample_mnist(data_dir, True, self.rand, args.train_percent, args.auto_download)
        ds_test = self.sample_mnist(data_dir, False, self.rand, args.test_percent, args.auto_download)

        if args.distributed:
            # Partition dataset among workers using DistributedSampler
            train_sampler = torch.utils.data.distributed.DistributedSampler(ds_train, num_replicas=hvd.size(), rank=hvd.rank())
            shuffle = False
        else:
            train_sampler = None
            shuffle = True

        print("loading TRAIN data...")
        self.train_loader = torch.utils.data.DataLoader(ds_train, 
            batch_size=args.batch_size, shuffle=shuffle, sampler=train_sampler, **kwargs)

        print("loading TEST data...")
        self.test_loader = torch.utils.data.DataLoader(ds_test, 
            batch_size=args.test_batch_size, shuffle=True, **kwargs)

    def init_cuda(self, args):
        #---- CUDA init ----
        cuda_avail = torch.cuda.is_available()
        use_cuda = cuda_avail and args.cuda 
        gpu_count = torch.cuda.device_count()
        
        if use_cuda and not args.parallel:
            torch.cuda.set_device(args.gpu)

        print("  cuda_avail={}, GPU count={}, use_cuda={}, gpu={} ---".format(cuda_avail, gpu_count, use_cuda, args.gpu))

        if use_cuda and not cuda_avail:
            # if we cannot find a GPU, consider that a hard error (used to detect problems with seeing Philly GPUs)
            errors.env_error("CUDA not available on this platform")

        if args.distributed:
            # Initialize Horovod
            global hvd
            import horovod.torch as hvd

            hvd.init()
            # Pin GPU to be used to process local rank (one GPU per process)
            print("  distributed: rank={}, size={}".format(hvd.rank(), hvd.size() ))
            device = torch.device("cuda:" + str(hvd.local_rank()))

            # only log HPARAMS and METRICS for job if running as rank 0
            logging = (hvd.rank() == 0)
        else:
            device = torch.device("cuda" if use_cuda else "cpu")
            logging = True

        return use_cuda, device, logging

    def init_dirs(self, args):
        # set mnt_output_dir (using environment variable setting from xt)
        mnt_output_dir = os.getenv("XT_OUTPUT_MNT", "output")
        mnt_output_dir = os.path.expanduser(mnt_output_dir)
        file_utils.ensure_dir_exists(mnt_output_dir)
        print("writing mnt_output to: " + mnt_output_dir)

        # set local_output_dir (using environment variable setting from xt)
        local_output_dir = "output"
        file_utils.ensure_dir_exists(local_output_dir)
        print("writing local_output to: " + local_output_dir)

        # set data_dir (allowing overridden by environment variable)
        data_dir = os.getenv("XT_DATA_DIR", args.data)
        data_dir = os.path.expanduser(data_dir)
        file_utils.ensure_dir_exists(data_dir)
        print("getting data from: " + data_dir)

        fn_test = data_dir + "/MNIST/processed/test.pt"
        exists = os.path.exists(fn_test)
        print("fn_test={}, exists={}".format(fn_test, exists))

        fn_train = data_dir + "/MNIST/processed/training.pt"
        exists = os.path.exists(fn_train)
        print("fn_train={}, exists={}".format(fn_train, exists))

        if args.download_only:
            print("miniMnist (ensuring data is downloaded)")
            self.get_dataget_dataset(data_dir, True, True)
            self.get_dataset(data_dir, False, True)
            
        return mnt_output_dir, local_output_dir, data_dir


    def print_settings(self, args):
        print("--- miniMnist settings ---")
        print("  command-line args:", sys.argv)

        if args.env_vars:
            print("  env vars:")
            keys = list(os.environ.keys())
            keys.sort()

            for key in keys:
                value = os.environ[key]
                if len(value) > 100:
                    value = value[0:100] + "..."
                print("    {}: {}".format(key, value))

        print("  cwd: " + os.getcwd())
        print("  python: " + sys.version.replace("\n", " "))
        print("  torch.__version__=", torch.__version__)

        # bug workaround: torchvision version 0.4.2 is missing the "__version__" attribute
        if hasattr(torchvision, "__version__"):
            print("  torchvision: " + str(torchvision.__version__))
        else:
            print("  dir(torchvision)=", dir(torchvision))

        in_docker = os.path.exists(".dockerenv") or os.getenv("XT_IN_DOCKER")
        print("  in_docker: " + str(in_docker))

        if args.xtlib:
            import xtlib
            print("  xtlib: " + str(xtlib.__version__))

    def init_model(self, device, args):
        use_cnn = True
        if use_cnn:
            print("created CNN model...")
            model = SimpleCNN(num_mid_conv=args.mid_conv, channels1=args.channels1, channels2=args.channels2, kernel_size=args.kernel_size, 
                mlp_units=args.mlp_units)
        else:
            print("created MLP model...")
            model = MLP()
            
        gpu_count = torch.cuda.device_count()

        if args.parallel and gpu_count > 1:
            model = nn.DataParallel(model)
            print("using PARALLEL training with {} GPUs".format(gpu_count))
        elif args.parallel:
            print("PARALLEL requested but only found {} GPUs".format(gpu_count))
        else:
            print("using single GPU; gpu_count=", gpu_count)
        model.to(device)

        return model

    def init_random_seeds(self, args):
        #---- random seeds ----
        if args.seed == 0:
            args.seed = int(time.time())
        self.rand = random.Random(args.seed)
        fn_checkpoint = "checkpoints/mnist_cnn.pt"
        torch.manual_seed(args.seed)

    def init_stuff(self):
        args = self.args

        mnt_output_dir, local_output_dir, data_dir = self.init_dirs(args)
        
        self.print_settings(args)
        self.init_random_seeds(args)
        
        use_cuda, device, logging = self.init_cuda(args)

        print("-------------")

        tb_path = mnt_output_dir if args.tensorboard else None
        self.init_xt_run(logging, tb_path, args)

        self.init_datasets(data_dir, use_cuda, args)

        model = self.init_model(device, args)

        return model, device, mnt_output_dir, local_output_dir

    def apply_runset_file(self, args, fn):
        #utils.debug_break()

        fn = os.path.abspath(fn)
        with open(fn, "rt") as infile:
            yd = yaml.safe_load(infile)  

        if not constants.HPARAM_RUNSET in yd:
            errors.internal_error("found runset file without {} property: {}".format(constants.HPARAM_RUNSET, fn))

        print("applying runset file to args: {}".format(fn))
        
        hd = yd[constants.HPARAM_RUNSET ]
        
        for prop, val in hd.items():
            prop = prop.replace("-", "_")
            setattr(args, prop, val)

    def run(self):

        print("args=", sys.argv)
        self.args = parse_cmdline_args()
        args = self.args

        fn_runset = "runset.yaml"
        if os.path.exists(fn_runset):
            self.apply_runset_file(args, fn_runset)

        model, device, mnt_output_dir, local_output_dir = self.init_stuff()

        start_epoch = 1
        run = self.run

        if args.raise_error:
            #errors.internal_error("Raising an intentional error")
            # try a different type of error
            abc.foo = 1

        # log hyperparameters to xt
        if run:
            hp_dict = {"seed":args.seed, "batch-size": args.batch_size, "epochs": args.epochs, "lr": args.lr, 
                "momentum": args.momentum, "channels1": args.channels1, "channels2": args.channels2, "kernel_size": args.kernel_size, 
                    "mlp-units": args.mlp_units, "weight-decay": args.weight_decay, "optimizer": args.optimizer, 
                    "mid-conv": args.mid_conv, "gpu": args.gpu, "log-interval": args.log_interval}

            run.log_hparams(hp_dict)

        if args.cuda:
            # if on linux, show GPU info
            if os.name != "nt":
                os.system("nvidia-smi")

        # print hyperparameters
        print("hyperparameters:", hp_dict)
        print()

        # see if we are resuming a preempted run
        if run and run.resume_name:
            print("resuming from run=", run.resume_name)
            dd = run.get_checkpoint(fn_checkpoint)
            if dd and dd["epoch"]:
                model.load_state_dict(torch.load(fn_checkpoint))
                start_epoch = 1 + dd["epoch"] 

        if args.optimizer == "sgd":
            #print("using SGD optimizer")
            optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum, weight_decay=args.weight_decay)
        else:  
            #print("using Adam optimizer")
            optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

        if args.distributed:
            optimizer = hvd.DistributedOptimizer(optimizer, named_parameters=model.named_parameters())

            # Broadcast parameters from rank 0 to all other processes.
            hvd.broadcast_parameters(model.state_dict(), root_rank=0)

        checkpoint_freq = 0
        checkpoint_units = ""
        last_checkpoint = time.time()
        checkpoint_count = 0

        # force a ML app error to kill the app
        #x = foo/bar

        # parse checkpoint arg
        #print("args.checkpoint=", args.checkpoint, ", type(args.checkpoint)", type(args.checkpoint))

        if False:   # args.checkpoint:
            if type(args.checkpoint) in ["int", "float"]:
                checkpoint_freq = int(args.checkpoint)
                checkpoint_units = "epochs"
            elif isinstance(args.checkpoint, str):
                parts = args.checkpoint.split(' ')
                if len(parts) == 2:
                    checkpoint_freq, checkpoint_units = parts
                    checkpoint_freq = float(checkpoint_freq)
                    checkpoint_units = checkpoint_units.strip().lower()
                else:
                    checkpoint_freq = float(args.checkpoint)
                    checkpoint_units = "epochs"

        model_dir = os.getenv("XT_MODEL_DIR", "models/miniMnist")
        fn_model = model_dir + "/mnist_cnn.pt"
        self.fn_text_log = mnt_output_dir + "/text_log.txt"

        if args.eval_model:
            # load model and evaluate it
            print("loading existing MODEL and evaluating it, fn=", fn_model)
            exists = os.path.exists(fn_model)
            print("model exists=", exists)

            model.load_state_dict(torch.load(fn_model))
            print("model loaded!")

            # just test model
            self.test_model_and_log_metrics(run, model, device, epoch=1, args=args)
        else:
            self.train_test_loop(run, model, device, optimizer, 1, checkpoint_freq, args=args)

        if (args.save_model):
            file_utils.ensure_dir_exists(model_dir)
            self.save_model(model, fn_model)   

        # # always save a copy of model in the AFTER FILES
        # self.save_model(model, "output/mnist_cnn.pt")

        if args.clear_checkpoint_at_end:        
            if checkpoint_freq and run and run.store:
                run.clear_checkpoint()
            
        # create a file to be captured in OUTPUT FILES
        fn_app_log = os.path.join(local_output_dir, "miniMnist_log.txt")
        with open(fn_app_log, "wt") as outfile:
            outfile.write("This is a log for miniMnist app\n")
            outfile.write("miniMnist app completed\n")

        # create a file to be ignored in OUTPUT FILES
        fn_app_log = os.path.join(local_output_dir, "test.junk")
        with open(fn_app_log, "wt") as outfile:
            outfile.write("This is a file that should be omitted from AFTER upload\n")
            outfile.write("end of junk file\n")

        if run:
            # ensure we close all logging
            run.close()

def main():
    started = time.time()
    #utils.debug_break()

    trainer = Trainer()
    trainer.run()

    elapsed = time.time() - started
    print("\n--- miniMnist elapsed: {:.0f} secs ---".format(elapsed))

if __name__ == '__main__':
    main()
