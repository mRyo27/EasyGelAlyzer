@echo off
echo ============================
echo   EasyGelAlyzer Auto Build
echo ============================
cd /d %~dp0

rem ---- Read version.py from src/ ----
if not exist src\version.py (
    echo Error: src\version.py not found.
    pause
    exit /b 1
)

for /f "tokens=2 delims== " %%a in (src\version.py) do set CURRENT=%%a
set CURRENT=%CURRENT:"=%
rem Trim leading/trailing spaces
for /f "tokens=* delims= " %%a in ("%CURRENT%") do set CURRENT=%%a

echo Version: %CURRENT%

rem ---- Parse version numbers ----
for /f "tokens=1-3 delims=." %%a in ("%CURRENT%") do (
    set MAJOR=%%a
    set MINOR=%%b
    set PATCH=%%c
)

echo Building EasyGelAlyzer v%CURRENT%

rem ---- Run git commands if git is available ----
where git >nul 2>nul
if %ERRORLEVEL% equ 0 (
    git add .
    git commit -m "Build v%CURRENT%"
    git tag v%CURRENT%
) else (
    echo Git not found, skipping git tagging.
)

rem ---- Set up temp paths to avoid non-ASCII characters in workpath ----
set TEMP_BUILD_DIR=%TEMP%\EasyGelAlyzerBuild_%RANDOM%
set WORK_PATH=%TEMP_BUILD_DIR%\build
set DIST_PATH=%TEMP_BUILD_DIR%\dist
set SPEC_PATH=%TEMP_BUILD_DIR%

echo Using temporary build directory: %TEMP_BUILD_DIR%

rem ---- Clean old local builds ----
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
if exist EasyGelAlyzer.spec del EasyGelAlyzer.spec

rem ---- Set icon path ----
set ICON_PATH=%~dp0src\assets\icon.ico
set ICON_OPT=
if exist "%ICON_PATH%" (
    set ICON_OPT=--icon="%ICON_PATH%"
)

rem ---- Run PyInstaller ----
rem - Use absolute paths for all source, path, and resource parameters to avoid spec-relative path resolution errors.
rem - Bundles absolute path to assets/ folder. translations.json is no longer needed since it is compiled directly in Python.
python -m PyInstaller --onefile --windowed --name EasyGelAlyzer %ICON_OPT% --paths "%~dp0src" --add-data "%~dp0src\assets;assets" --workpath "%WORK_PATH%" --distpath "%DIST_PATH%" --specpath "%SPEC_PATH%" "%~dp0src\main.py"

rem ---- Copy the built executable back to local workspace ----
if exist "%DIST_PATH%\EasyGelAlyzer.exe" (
    mkdir "%~dp0dist" 2>nul
    copy /y "%DIST_PATH%\EasyGelAlyzer.exe" "%~dp0dist\EasyGelAlyzer.exe"
)

rem ---- Clean temporary build directory ----
rmdir /s /q "%TEMP_BUILD_DIR%" 2>nul

rem ---- Create shortcut ----
set SC_PATH=%~dp0EasyGelAlyzer.lnk
set EXE_PATH=%~dp0dist\EasyGelAlyzer.exe
set TEMP_VBS=%TEMP%\CreateShortcut_%RANDOM%.vbs

if not exist "%EXE_PATH%" goto :BUILD_FAIL

:CREATE_SHORTCUT
rem Create the VBScript without using complex parentheses inside Batch IF statements to avoid parser issues.
echo Set ws = CreateObject("WScript.Shell") > "%TEMP_VBS%"
echo Set sc = ws.CreateShortcut("%SC_PATH%") >> "%TEMP_VBS%"
echo sc.TargetPath = "%EXE_PATH%" >> "%TEMP_VBS%"
echo sc.WorkingDirectory = "%~dp0dist" >> "%TEMP_VBS%"
if exist "%ICON_PATH%" echo sc.IconLocation = "%ICON_PATH%" >> "%TEMP_VBS%"
echo sc.Save >> "%TEMP_VBS%"

cscript //nologo "%TEMP_VBS%"
del "%TEMP_VBS%" 2>nul
echo Completed successfully.
goto :END

:BUILD_FAIL
echo Error: Build failed, executable not found.

:END
pause
