rem --- builds a docker image containing: cuda, conda, pytorch 1.2.0, and xtlib
rem 
rem --- FIRST, you need to run "docker_pytorch\build.bat" (builds "pytorch-cuda")
rem --- then, you can run this build.bat file.
call docker build --no-cache -t pytorch-xtlib .

