rem --- copy demo files to xtlib\demos ---
call pushd cmdlineTest
call clean.bat
call popd

rem --- clean files ---
rd /s /q xt_demo_archives

rem --- push to github repo ---
git add .
git commit -m %1
git push
