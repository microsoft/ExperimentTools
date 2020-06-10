.. _config_schema:

=======================
XT Config File Schema
=======================

This page lists the schema we use in XT to validate XT config files.  Both the default config file and 
the user's local config file (if present) are validated as they are loaded.

---------------------------------
Schema Definition
---------------------------------

The schema is defined in the YAML language (a nested dictionary), using a set of predefined keys and values.

The following KEYS are predefined for building schemas::

    - $record_types     (used to define new dictionary value types)
    - $repeat           (used to require 1 or more occurance of the following type)
    - $opt              (used to introduce a dictionary of optional key/value pairs}
    - $select           (uses the $select-key to select one record from the set of $select-records)
    - $select-key       (specifies the key to use in selecting the type of record to validate)
    - $select-records   (specifies the set of records that $select-key will match)

The following VALUES are predefined for building schemas::

    - $str          (the value must be a string or null)
    - $bool         (the value must be a true or false YAML value)
    - $int          (the value must be a integer number or null)
    - $num          (the value must be a floating point, integer, or null)
    - $str-list     (the value must be a YAML list of strings)
    - $rec          (the value must be a simple YAML dictionary)

---------------------------------
Schema
---------------------------------

Here is the schema for the XT config file::

    $record-types:
        rec_philly: {type: "philly"}
        rec_batch: {type: "batch", key: $str, url: $str }
        rec_aml: {type: "aml", subscription-id: $str, resource-group: $str}
        rec_storage: {type: "storage", provider: $str, $opt: {key: $str, path: $str}}
        rec_mongo: {type: "mongo", mongo-connection-string: $str}
        rec_vault: {type: "vault", url: $str}
        rec_registry: {type: "registry", login-server: $str, $opt: {username: $str, password: $str, login: $bool}}

        rec_service: {service: $str, $opt: 
            {vm-size: $str, azure-image: $str, low-pri: $bool, box-class: $str, environment: $str, boxes: $str-list, vc: $str, cluster: $str, queue: $str,
            sku: $str, compute: $str, nodes: $int }}

        rec_environment: {registry: $str, image: $str}
        rec_image: {offer: $str, publisher: $str, sku: $str, node-agent-sku-id: $str, version: $str}
        rec_box: {address: $str, max-runs: $int, $opt: {os: $str, actions: $str-list, box-class: $str}}

    external-services:
        $repeat:
            $str: {$select: {$select-key: type, $select-records: {philly: $rec_philly, batch: $rec_batch, aml: $rec_aml, storage: $rec_storage, mongo: $rec_mongo, 
                vault: $rec_vault, registry: $rec_registry} } }

    xt-services:
        storage: $str
        mongo: $str
        vault: $str
        target: $str

    compute-targets:
        $repeat:
            $str: $rec_service

    environments:
        $repeat:
            $str: $rec_environment

    general:
        username: $str
        workspace: $str
        experiment: $str
        attach: $bool
        feedback: $bool
        run-cache-dir: $str
        distributed: $bool
        direct-run: $bool
        quick-start: $bool
        primary-metric: $str
        maximize-metric: $bool
        conda-packages: $str-list
        pip-packages: $str-list
        env-vars: $rec
        authentication: [auto, browser, device-code]
        xt-team-name: $str
        
    code:
        code-dirs: $str-list
        code-upload: $bool
        code-zip: [none, fast, compress] 
        code-omit: $str-list
        xtlib-upload: $bool

    after-files:
        after-dirs: $str-list
        after-upload: $bool
        after-omit: $str-list

    data:
        data-local: $str
        data-upload: $bool
        data-share-path: $str
        data-action: [none, download, mount]
        data-omit: $str-list
        data-writable: $bool

    model:
        model-share-path: $str
        model-action: [none, dowhnload, mount]
        model-writable: $bool

    logging:
        log: $bool
        notes: [none, before, after, all]
        mirror-files: $str
        mirror-dest: [none, storage]

    internal:
        console: [none, normal, diagnostics, detail]
        stack-trace: $bool
        auto-start: $bool
        show-controller: $bool

    aml-options:
        use-gpu: $bool
        use-docker: $bool
        framework: $str
        fw-version: $str
        user-managed: $bool
        distributed-training: [mpi, gloo, nccl]
        max-seconds: $int

    early-stopping:
        early-policy: [none, bandit, median, truncation]
        delay-evaluation: $num
        evaluation-interval: $num
        slack-factor: $num
        slack-amount: $num
        truncation-percentage: $num

    hyperparameter-search:
        option-prefix: $str
        aggregate-dest: [job, experiment, none]
        search-type: [random, grid, bayesian, dgd]
        max-minutes: $num
        max-concurrent-runs: $int
        hp-config: $str
        fn-generated-config: $str

    hyperparameter-explorer:
        hx-cache-dir: $str
        steps-name: $str
        log-interval-name: $str
        step-name: $str
        time-name: $str
        sample-efficiency-name: $str
        success-rate-name: $str

    run-reports:
        sort: $str
        group: $str
        number-groups: $bool
        reverse: $bool
        max-width: $int
        precision: $int
        uppercase-hdr: $bool
        right-align-numeric: $bool
        truncate-with-ellipses: $bool
        status: $str
        report-rollup: $bool
        columns: $str-list

    job-reports:
        sort: $str
        reverse: $bool
        max-width: $int
        precision: $int
        uppercase-hdr: $bool
        right-align-numeric: $bool
        truncate-with-ellipses: $bool
        columns: $str-list

    tensorboard:
        template: $str

    script-launch-prefix:
        windows: $str
        linux: $str
        dsvm: $str
        azureml: $str
        philly: $str

    azure-batch-images:
        $repeat:
            $str: $rec_image

    boxes:
        $repeat:
            $str: $rec_box

    providers:
        command: 
            $repeat: {$str: $str}

        compute: 
            $repeat: {$str: $str}

        hp-search: 
            $repeat: {$str: $str}

        storage: 
            $repeat: {$str: $str}


.. seealso:: 

    - :ref:`XT Config File <xt_config_file>`
    