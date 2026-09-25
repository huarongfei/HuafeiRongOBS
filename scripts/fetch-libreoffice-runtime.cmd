@echo off
setlocal
REM 下载并免管理员解包 LibreOffice 运行时（供 HFRPpt 嵌入使用）
set VER=26.2.6
set ROOT=%~dp0..
set TOOLS=%ROOT%\tools
if not exist "%TOOLS%" mkdir "%TOOLS%"
if exist "%TOOLS%\LibreOffice\program\mergedlo.dll" ( echo [skip] runtime already present & goto :done )
echo [1/3] 下载 LibreOffice %VER% 主程序与 SDK ...
curl -L --retry 4 -o "%TOOLS%\LibreOffice_%VER%_Win_x86-64.msi" "https://download.documentfoundation.org/libreoffice/stable/%VER%/win/x86_64/LibreOffice_%VER%_Win_x86-64.msi"
curl -L --retry 4 -o "%TOOLS%\LibreOffice_%VER%_Win_x86-64_sdk.msi" "https://download.documentfoundation.org/libreoffice/stable/%VER%/win/x86_64/LibreOffice_%VER%_Win_x86-64_sdk.msi"
echo [2/3] 解包运行时（免管理员）...
msiexec /a "%TOOLS%\LibreOffice_%VER%_Win_x86-64.msi" /qn TARGETDIR="%TOOLS%\LibreOffice"
msiexec /a "%TOOLS%\LibreOffice_%VER%_Win_x86-64_sdk.msi" /qn TARGETDIR="%TOOLS%\LibreOfficeSDK"
echo [3/3] 完成。
:done
echo 运行时目录：%TOOLS%\LibreOffice
endlocal
