@echo off

echo Update code repository
git pull --ff-only
IF ERRORLEVEL 1 GOTO ERROR
.venv\Scripts\python -m pip install -r requirements.txt -q
IF ERRORLEVEL 1 GOTO ERROR

echo Update Datase from GitHub
cd COVID-19
git pull --ff-only
cd ..

echo Collect report
.venv\Scripts\python collect.py
IF ERRORLEVEL 1 GOTO ERROR

echo Done
goto EXIT

:ERROR
echo.
echo THERE WAS AN ERROR!!!
echo.

:EXIT
pause
