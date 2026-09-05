@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
echo === vcvars done ===
cmake --build build_x64 --config RelWithDebInfo --parallel 8
echo CMakeBuildExit=%ERRORLEVEL%
endlocal
