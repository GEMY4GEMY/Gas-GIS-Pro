@echo off
setlocal
rem Development launcher: requires an installed OSGeo4W/QGIS runtime.
set "ROOT=%~dp0"
if not exist "%ROOT%gasgis\main.py" (
  echo Missing gasgis\main.py next to this launcher.
  exit /b 2
)
if not defined OSGEO4W_ROOT (
  if exist "C:\OSGeo4W\bin\o4w_env.bat" set "OSGEO4W_ROOT=C:\OSGeo4W"
)
if not defined OSGEO4W_ROOT (
  echo OSGeo4W not detected. Launch from the OSGeo4W Shell or set OSGEO4W_ROOT.
  exit /b 2
)
if not exist "%OSGEO4W_ROOT%\bin\o4w_env.bat" (
  echo Missing OSGeo4W environment script at "%OSGEO4W_ROOT%".
  exit /b 2
)
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
if errorlevel 1 exit /b 3
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
if exist "%OSGEO4W_ROOT%\bin\python-qgis.bat" goto run_qgis
python "%ROOT%gasgis\main.py"
exit /b %errorlevel%
:run_qgis
call "%OSGEO4W_ROOT%\bin\python-qgis.bat" "%ROOT%gasgis\main.py"
exit /b %errorlevel%
