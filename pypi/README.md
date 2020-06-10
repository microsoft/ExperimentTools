# To release xtlib (to PYPI):

   - check latest ExperimentTools changes into github (usually from Windows)
   - clone ExperimentTools on a LINUX machine (bash on Windows is NOT sufficient)
   - double check that script/xt file:
        - has no CR chars (cat scripts/xt | od -c)
        - has the executable bits set (stat scripts/xt)

    - bump the version number for xtlib in setup.py
    - cd to this (the pypi) directory
    - sh release.xtlib.sh

# Why can't this be done from Windows?
    - the "xt" file needs to be pushed to pypi with its "executable" bits set
    - doing the release from Windows loses the execuatable bits on "xt"

    

