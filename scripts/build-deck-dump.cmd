@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set SRC=D:\HuafeirongOBS\obs-src\frontend\widgets
set DEPS=D:\HuafeirongOBS\obs-src\.deps\obs-deps-2026-07-15-x64
set OUT=D:\HuafeirongOBS\logs\deckdump
if not exist "%OUT%" mkdir "%OUT%"
cl /nologo /std:c++17 /EHsc /O2 /utf-8 /Fe:"%OUT%\hfr_deck_dump.exe" /Fo:"%OUT%\\" /I"%SRC%" /I"%DEPS%\include" "%SRC%\HFRDeck.cpp" "%SRC%\HFRDeckRender.cpp" "%SRC%\HFRDeckDump.cpp" /link /LIBPATH:"%DEPS%\lib" zlibstatic.lib user32.lib gdi32.lib
echo BUILD_EXIT=%ERRORLEVEL%
endlocal