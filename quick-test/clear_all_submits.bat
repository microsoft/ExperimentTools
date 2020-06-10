echo on
del approved_*.zip
rd /s /q approved_submitLogs_windows
rd /s /q submitLogs

python code\runTests.py
python code\runTests.py
