rem --- runs the docker image along with the main_script file (outside of the image)
docker run  --rm -v %cd%:/usr/src pytorch-xtlib python -u /usr/src/train.py