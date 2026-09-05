@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
echo === vcvars done ===
cmake --preset windows-x64 -DENABLE_BROWSER=OFF
echo CMakeConfigureExit=%ERRORLEVEL%
endlocal
