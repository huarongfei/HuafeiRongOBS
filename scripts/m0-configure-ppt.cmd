@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
echo === vcvars done ===
cmake --preset windows-x64 -DENABLE_BROWSER=OFF -DHFR_ENABLE_PPT=ON -DHFR_LO_SDK_DIR="D:/HuafeirongOBS/tools/LibreOfficeSDK/sdk/include"
echo CMakeConfigureExit=%ERRORLEVEL%
endlocal
