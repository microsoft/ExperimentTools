.. _hello_mnist_philly:

======================================
Hello MNIST Philly Tutorial
======================================

This tutorial will walk you through using XT to submit ML jobs to the Philly computing service
(internal to Microsoft).

For our ML job, we will use a slightly modified version of the PyTorch MNIST sample program, which
trains a model on the MNIST dataset.

To follow along in this tutorial, you should copy/paste the code shown into local files
on your computer and run the specified XT commands.

------------------------------
Install XT
------------------------------

If you haven't already done so, install XT now.  For details, refer to the :ref:`Getting Started <getting_started>` topic.

-------------------------------------
The MNIST program (train_mnist.py)
-------------------------------------

Here is the program (modified slightly from the MNIST PyTorch Sample) that we will be using::

    from __future__ import print_function
    import argparse
    import logging
    import os
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    from tempfile import TemporaryDirectory
    from torchvision import datasets, transforms
    from torch.autograd import Variable
    from torch.utils.tensorboard import SummaryWriter
    from tensorboard.compat import tf

    logging.basicConfig(level=logging.INFO)
    SW = SummaryWriter(os.environ.get('PT_OUTPUT_DIR', '.'), flush_secs=30)


    # Training settings
    parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
    parser.add_argument('--epochs', type=int, default=10, metavar='N',
                        help='number of epochs to train (default: 10)')
    parser.add_argument('--lr', type=float, default=0.01, metavar='LR',
                        help='learning rate (default: 0.01)')
    parser.add_argument('--momentum', type=float, default=0.5, metavar='M',
                        help='SGD momentum (default: 0.5)')
    parser.add_argument('--seed', type=int, default=1, metavar='S',
                        help='random seed (default: 1)')
    parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                        help='how many batches to wait before logging training status')
    # output
    parser.add_argument('--output-dir', type=str, default=os.getenv('PT_OUTPUT_DIR', '/tmp'))

    args = parser.parse_args()
    args.cuda = torch.cuda.is_available()

    torch.manual_seed(args.seed)
    if args.cuda:
        torch.cuda.manual_seed(args.seed)

    # Each job will download its own data inside the docker (virtual machine)
    # it is run to. This is feasible for small datasets (such as MNIST)
    # but for large dataset, we recommend using `upload_data` flag in the PT
    # YAML config file.
    kwargs = {'num_workers': 1, 'pin_memory': True} if args.cuda else {}
    temp_dir = TemporaryDirectory(prefix="mnist")
    train_loader = torch.utils.data.DataLoader(
        datasets.MNIST(
            temp_dir.name, train=True, download=True,
            transform=transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize((0.1307,), (0.3081,))])),
        batch_size=64, shuffle=True, **kwargs)
    test_loader = torch.utils.data.DataLoader(
        datasets.MNIST(temp_dir.name, train=False, transform=transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,))])),
        batch_size=100, shuffle=True, **kwargs)


    class Net(nn.Module):
        def __init__(self):
            super(Net, self).__init__()
            self.conv1 = nn.Conv2d(1, 10, kernel_size=5)
            self.conv2 = nn.Conv2d(10, 20, kernel_size=5)
            self.conv2_drop = nn.Dropout2d()
            self.fc1 = nn.Linear(320, 50)
            self.fc2 = nn.Linear(50, 10)

        def forward(self, x):
            x = F.relu(F.max_pool2d(self.conv1(x), 2))
            x = F.relu(F.max_pool2d(self.conv2_drop(self.conv2(x)), 2))
            x = x.view(-1, 320)
            x = F.relu(self.fc1(x))
            x = F.dropout(x, training=self.training)
            x = self.fc2(x)
            return F.log_softmax(x, dim=1)


    model = Net()
    if args.cuda:
        model.cuda()

    optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum)


    def train(epoch):
        model.train()
        for batch_idx, (data, target) in enumerate(train_loader):
            if args.cuda:
                data, target = data.cuda(), target.cuda()
            data, target = Variable(data), Variable(target)
            optimizer.zero_grad()
            output = model(data)
            loss = F.nll_loss(output, target)
            loss.backward()
            optimizer.step()
            if batch_idx % args.log_interval == 0:
                SW.add_scalar('loss/train', loss.item(), epoch)
                logging.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                    epoch, batch_idx * len(data), len(train_loader.dataset),
                    100. * batch_idx / len(train_loader), loss.item()))


    def test(epoch):
        model.eval()
        test_loss = 0
        correct = 0
        for data, target in test_loader:
            if args.cuda:
                data, target = data.cuda(), target.cuda()
            data, target = Variable(data, volatile=True), Variable(target)
            output = model(data)
            test_loss += F.nll_loss(output, target, size_average=False).item()  # sum up batch loss
            pred = output.data.max(1, keepdim=True)[1]  # get the index of the max log-probability
            correct += pred.eq(target.data.view_as(pred)).long().cpu().sum()

        test_loss /= len(test_loader.dataset)
        SW.add_scalar('loss/test', test_loss, epoch)
        SW.add_scalar('accuracy/test', 100. * correct / len(test_loader.dataset), epoch)
        logging.info('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
            test_loss, correct, len(test_loader.dataset),
            100. * correct / len(test_loader.dataset)))


    for epoch in range(1, args.epochs + 1):
        train(epoch)
        test(epoch)
        print("PROGRESS: {}%".format((epoch / args.epochs) * 100))

    torch.save(model.state_dict(), args.output_dir + "/model.pt")

The above program trains a model to classify the handwritten digits from the famous MNIST dataset. Copy the above code
into your clipboard and paste it into a file in your working directory called "train_mnist.py".

---------------------------------
XT .yaml files
---------------------------------

The XT run command we will be using is driven by a set of properties that control its behavior.  Most of the properties have sensible default values so,
when using it, we just need to specify the property values to override a default behavior.  These override property values 
are normally specified in a local XT .yaml file, but we also see some examples of overridding them on the XT command line.

Learning which properties need to be specified and when is a major part of learning to use XT.  This tutorial will introduce features and 
their associated properties incrementally.

-----------------------------------------
Our first .yaml file (hello_world.yaml)
-----------------------------------------

Here is hello_world.yaml::

    # hello_world.yaml: show how to run train_mnist.py on philly with XT

    xt-services:
        target: philly

    commands:
        - python train_mnist.py  --lr=.01
        - python train_mnist.py  --lr=.05

    code:
        code-dirs: ["."]                  # path to the code directories needed for the run (code snapshot)


You should copy/paste the above text into a file called "hello_world.yaml".

This file has 3 main properties::

    - xt-services (used to set the service we want as philly)
    - commands (where we can list the commands we want to run)
    - code (where we specify that we need our current directory of files to be captured for the remote runs)

----------------------------------------
Our first job submission
----------------------------------------

We submit jobs to Philly using the xt **run** command.  Run this now to submit our first job::

    $ xt run hello_world.yaml

This command takes about about 15 seconds to run - it will create a Philly job that will be queue to run
on the default Philly configuration (cluster, vc, sku, etc.).  Later we will see how to change these.

The job should start running in 10-20 minutes and take an additional 10 minutes or so to complete.

----------------------------------------
Monitoring the status of our job
----------------------------------------

To monitor the program of our job, we can use the **list runs** command::

    $ xt list runs

A new monitoring window will open to show events when you start the job.

In addition, we can go to the Philly website and monitor the job from there: http://philly

.. note:: You can also run the XT command **xt view portal philly** show show the Philly service website URL. Run the command **xt view portal philly --browse** to open a new browser window showing the URL.

----------------------------------------
Gathering the results of our job
----------------------------------------

Once our job has completed, we can download the results as a file using the command::

    $ xt extract run2 results --browse

Where **run2** is replaced by the run that you want to download. This will download the run's 
code, logs, and other output files to a new **results** directory and open them in your OS file browser. The directory uses the following naming conventions:

.. code-block::

results/experiment-name/job-id/run-name/
results/job-id/run-name/
run-name/

Here, *experiment-name* is the name of the experiment associated with the runs, *job-id* is the name of the job associated with the runs, and *run-name* is the name of each run extracted.

----------------------------------------
Next Step
----------------------------------------

Want to let us know about anything? Let the XT team know by filing an issue in our repository at `GitHub! <https://github.com/Microsoft/ExperimentTools/issues>`_. We look forward to hearing from you!


.. seealso:: 

    - :ref:`Getting Started <getting_started>`
