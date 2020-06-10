rd /s /q _build
rd /s /q cmds

call xt generate help cmds

call make html %*

set dest=..\..\xtlib\help_topics\internals
rd /s /q %dest%
xcopy internals\*.rst %dest%\ /s

set dest=..\..\xtlib\help_topics\topics
rd /s /q %dest%
xcopy topics\*.rst %dest%\ /s

echo "NOW, use VS CODE to deploy the "_built\html" directory to the XTDOCS storage target"

