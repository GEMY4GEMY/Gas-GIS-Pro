@echo off
setlocal
rem Run from an existing OSGeo4W/QGIS installation. Not a portable launcher.
set "ROOT=%~dp0"
if not defined OSGEO4W_ROOT (
  echo OSGEO4W_ROOT is not set. Open the OSGeo4W Shell first.
  exit /b 2
)
if not exist "%OSGEO4W_ROOT%\bin\o4w_env.bat" (
  echo Cannot find OSGeo4W environment at "%OSGEO4W_ROOT%".
  exit /b 2
)
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
if errorlevel 1 exit /b %errorlevel%
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
if exist "%OSGEO4W_ROOT%\bin\python-qgis.bat" (
  call "%OSGEO4W_ROOT%\bin\python-qgis.bat" "%ROOT%gasgis\main.py"
) else (
  python "%ROOT%gasgis\main.py"
)
exit /b %errorlevel%
