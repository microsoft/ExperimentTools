.. _xt_and_philly:

========================================
Running Jobs on Philly from XT
========================================

XT supports running jobs on Philly.  

The suggested steps for *getting started* with XT for Philly are as follows:

    **1. PREPARE a conda virtual environment with PyTorch:**
        
        .. code-block::

            > conda create -n MyEnvName python=3.6
            > conda activate MyEnvName
            > conda install pytorch torchvision cudatoolkit=10.1 -c pytorch

    **2. INSTALL XT:**

        .. code-block::

            > pip install -U xtlib

    **3. CREATE a set of demo files:**

        .. code-block::

            > md c:\clean
            > cd c:\clean
            > xt create demo xt_demo

            This will create 2 files and 1 subdirectories in the *xt_demo* directory:
                - xt_config_overrides.yaml     (xt config settings, active when xt is run from this directory)
                - xt_demo.py - the python file that drives the demo
                - code  (a subdirectory containing some files used by the demo app)

    **4. Submit a single run to Philly and prepare a jupyter notebook to monitor it:**

        .. code-block::

            > xt run --target=philly miniMnist.py

        Once submitted, you can track your run in the philly portal (http://philly)

    **5. Submit a set of hyperparameter runs as specified by script command-line arguments (10 runs):**

        .. code-block::

            > xt run --target=philly --max-total-runs=10 miniMnist.py --epochs=25 --lr=@normal(.1,.025) --optimizer=@choice(sgd,adam)

    **6. Submit a set of hyperparameter search runs for parameter distributions specified in a text file (10 runs):**

        .. code-block::

            > xt run --target=philly --max-total-runs=10 --hp-config=miniSweeps.txt miniMnist.py 


    **7. To view the console output for a run:**

        .. code-block::

            > xt view console run321

    **7. To view the run tensorboard logs (while it is running, or after it has completed):**

        .. code-block::

            > xt view tensorboard run321

    **8. To kill all runs associated with philly job 'jobNNN':**

        .. code-block::

            > xt kill all --job=jobNNN 

    **9. To compare the last 20 runs:**

        .. code-block::

            > xt list runs --last=20


    **10. To download the before and after snapshots for a run:**

        .. code-block::

            > xt extract run321 c:\philly-runs\run321

    **11. To view the status of a Philly cluster:**

        .. code-block::

            > xt status --target=philly --cluster=rr1  --username=all

     **12. To upload data and reference it's folder from a Philly run:**

        .. code-block::

            > xt upload data c:\mnist\** mnist
            > xt run --data-mnt=mnist --target=philly miniMnist.py

     **13. To upload a model and reference it's folder from a Philly run:**

        .. code-block::

            > xt upload model c:\mnist\** res-net-hybrid-v3
            > xt run --model-mnt=res-net-hybrid-v3 --target=philly miniMnist.py

     **14. To visually explore the results of a hyperparameter search (aggregated by job):**

        .. code-block::

            > xt explore job321

     **15. To train a script with 4 gpu's (parallel training):**

        .. code-block::

            > xt run --sku=G4 --parallel --target=philly miniMnist.py

     **16. To train a script with 10 nodes (distributed training):**

        .. code-block::

            > xt run --low-pri=10 --distributed --target=philly miniMnist.py

------------------------------
Philly authentication
------------------------------

For submitting, querying, and managing your jobs, Philly requires your domain username and password. XT uses the **curl** command
and Philly's certificate to communicate securely with Philly.

For Windows users:
    - your username and password are automatically sent to Philly (using the **-u :** option of **curl**).

For Linux users:
    - by default your Linux login name will be used as the Philly username and you will be prompted for your matching password on each Philly access.  
    - you can override this behavior by storing your username and password in the file `~/.xt/curl_config.txt` in the form::
    
        -u myUserName:MyPassWord

    - the **chmod** command can be used to remove all access permissions for other users on this file::

        chmod go-rwx ~/.xt/curl_config.tx

.. seealso:: 

    - :ref:`run command <run>`
    - :ref:`Understanding the XT Config file <xt_config_file>`
    - `curl command <https://curl.haxx.se/docs/httpscripting.html>`_



