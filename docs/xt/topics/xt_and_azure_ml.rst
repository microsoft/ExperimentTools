.. _xt_and_azure_ml:

========================================
Running Azure ML with XT 
========================================

XT supports running python scripts under Azure ML.

Some notable differences when running under Azure ML:
    - Normally in XT, the run script and its associated current directory files are stored in azure store, as a .zip file or as 
      individual files.  In the case of Azure ML, they are stored in as an AML snapshot (internally a .zip file), 
      whose ID is associated with your run record.

    - The location of the run logs and other output files are normally stored in the Azure storage service specified in
      your config file, under workspace/runname.  In the case of Azure ML, they are stored in as part of your run record, 
      in a storage service associated with your Azure ML workspace, and are named with GUIDs.  There is not a clear correspondance
      between your storge service contents and a Azure ML run record.

    - In XT hyperparameter searches with discrete values, you may train multiple times with the same hyperparameter set.  In Azure ML,
      you only schedule runs to train with a particular hyperparameter set once.

The suggested steps for *getting started* with XT for Azure ML development are as follows:

    **1. PREPARE a conda virtual environment with PyTorch:**
        
        .. code-block::

            > conda create -n MyEnvName python=3.6
            > conda activate MyEnvName
            > conda install pytorch torchvision cudatoolkit=10.1 -c pytorch

    **2. INSTALL XT and expose virtual env as Jupyter Notebook KERNEL:**

        .. code-block::

            > (first, save your old config file by renaming "c:\users\yourname\.xt\xt_config.toml" to a different name)
            > pip install -U xtlib
            > python -m ipykernel install --user --name MyEnvName --display-name "Python (MyEnvName)" 

    **3. CREATE a set of demo files:**

        .. code-block::

            > xt create demo xt_demo

    **4. Submit a single run to Azure ML and prepare a jupyter notebook to monitor it:**

        .. code-block::

            > xt run --monitor miniMnist.py

    **5. Submit a set of hyperparameter search runs for parameter distributions specified as script command-line arguments (10 runs):**

        .. code-block::

            > xt run --monitor --max-total-runs=10 miniMnist.py --epochs=25 --lr=@normal(.1,.025) --optimizer=@choice(sgd,adam)

    **6. Submit a set of hyperparameter search runs for parameter distributions specified in a text file (10 runs):**

        .. code-block::

            > xt run --monitor --max-total-runs=10 --hp-config=miniSweeps.txt miniMnist.py 

    **7. Submit a distributed run on 4 machines:**

        .. code-block::

            > xt run --monitor --nodes=4 miniMnist.py --train-percent=1 --test-percent=1  --epochs=100  --distributed=1

        .. note::

            - the XT option "--nodes=4" is sufficient to switch from normal to distributed training.  Other backends beside MPI can be selected in your xt_config.tom file (use "xt config" to view/edit).

            - the above will run on 4 nodes using MPI, training with 100% of the MNIST dataset, with 100 passes over the data.  the "--distributed" tells miniMnist.py to use the horovod library to run correctly on a distributed node.  

            - this take about 20-25 mins to run on the 4 nodes.

    **8. Explore other XT commands that work with Azure ML:**

        - **xt monitor**            (to monitor an Azure ML run from a Jupyter Notebook widget)
        - **xt attach**             (to attach to streaming output from an Azure ML run)
        - **xt list files**         (to list log and output files associated with a run)
        - **xt download files**     (to download log and output files associated with a run)
        - **xt kill**               (to stop a run)
        - **xt list runs**          (to show a report of runs)
        - **xt list workspaces**    (list all the workspaces known to XT - regular and Azure ML)
        - **xt list experiments**   (to list all the experiments associated with the current workspace)

