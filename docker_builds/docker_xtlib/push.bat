call xt docker login --environ=pytorch-xtlib
set registry=xtcontainerregistry.azurecr.io

call docker tag pytorch-xtlib %registry%/pytorch-xtlib:latest
call docker push %registry%/pytorch-xtlib:latest
