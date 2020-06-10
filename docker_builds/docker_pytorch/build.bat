rem --- builds a docker image containing: cuda, conda, and pytorch 1.2.0
call docker build --pull -t pytorch-cuda .

