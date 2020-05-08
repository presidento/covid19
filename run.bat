@echo off

echo Update code repository
git pull --ff-only
pause

echo Update Datase from GitHub
cd COVID-19
git pull
cd ..

echo Collect report
python collect.py

echo Done
pause