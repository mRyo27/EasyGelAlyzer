@echo off

set TEMP=C:\Temp
set TMP=C:\Temp
mkdir C:\Temp 2>nul
echo TEMP=%TEMP%

echo ============================
echo   EasyGelAlyzer Release Build
echo   (PyInstaller + UPX Edition)
echo ============================

rem ============================================================
rem  0. Init
rem ============================================================
cd /d %~dp0


rem ============================================================
rem  1. Read version.py
rem ============================================================
if not exist src\version.py (
    echo Error: src\version.py not found.
    pause
    exit /b 1
)

for /f "tokens=2 delims== " %%a in (src\version.py) do set CURRENT=%%a
set CURRENT=%CURRENT:"=%
for /f "tokens=* delims= " %%a in ("%CURRENT%") do set CURRENT=%%a

echo Version detected: %CURRENT%


rem ============================================================
rem  2. Download and extract UPX
rem ============================================================
set UPX_VERSION=4.2.4
set UPX_DIR=%~dp0tools\upx
set UPX_EXE=%UPX_DIR%\upx.exe

if not exist "%UPX_EXE%" (
    echo UPX not found. Downloading UPX v%UPX_VERSION%...
    mkdir "%UPX_DIR%" 2>nul
    set "_UPX_URL=https://github.com/upx/upx/releases/download/v%UPX_VERSION%/upx-%UPX_VERSION%-win64.zip"
    set "_UPX_ZIP=%TEMP%\upx_%UPX_VERSION%.zip"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri $env:_UPX_URL -OutFile $env:_UPX_ZIP"
    if not exist "%TEMP%\upx_%UPX_VERSION%.zip" (
        echo Error: Failed to download UPX.
        pause
        exit /b 1
    )
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path $env:_UPX_ZIP -DestinationPath '%UPX_DIR%' -Force"
    if exist "%UPX_DIR%\upx-%UPX_VERSION%-win64\upx.exe" (
        copy /y "%UPX_DIR%\upx-%UPX_VERSION%-win64\upx.exe" "%UPX_DIR%\" >nul
        rmdir /s /q "%UPX_DIR%\upx-%UPX_VERSION%-win64"
    )
    if not exist "%UPX_EXE%" (
        echo Error: UPX extraction failed.
        pause
        exit /b 1
    )
    echo UPX downloaded successfully.
) else (
    echo UPX already exists: %UPX_EXE%
)


rem ============================================================
rem  3. Prepare Release folder
rem ============================================================
set RELEASE_ROOT=%~dp0Releases
set RELEASE_DIR=%RELEASE_ROOT%\EasyGelAlyzer
set DIST_DIR=%RELEASE_DIR%\dirt
set ASSETS_DIR=%RELEASE_DIR%\assets
set PATCHNOTE_SRC=%~dp0PatchNote

rmdir /s /q "%RELEASE_DIR%" 2>nul
mkdir "%RELEASE_DIR%"
mkdir "%DIST_DIR%"
mkdir "%ASSETS_DIR%"


rem ============================================================
rem  4. Copy documents
rem ============================================================
copy /y "%~dp0LICENSE" "%RELEASE_DIR%" >nul
copy /y "%~dp0README.md" "%RELEASE_DIR%" >nul
copy /y "%~dp0README_EN.md" "%RELEASE_DIR%" >nul


rem ============================================================
rem  5. Copy icon
rem ============================================================
set ICON_PATH=%~dp0src\assets\icon.ico
if exist "%ICON_PATH%" copy /y "%ICON_PATH%" "%ASSETS_DIR%" >nul


rem ============================================================
rem  6. Copy test image
rem ============================================================
set TEST_IMG_SRC=%~dp0src\assets\test_gel_image.png
if exist "%TEST_IMG_SRC%" copy /y "%TEST_IMG_SRC%" "%RELEASE_DIR%" >nul


rem ============================================================
rem  7. Build main EXE (PyInstaller)
rem ============================================================
echo.
echo Building main executable...

set TEMP_BUILD_DIR=%TEMP%\EasyGelAlyzerBuild_%RANDOM%
set WORK_PATH=%TEMP_BUILD_DIR%\build
set DIST_PATH=%TEMP_BUILD_DIR%\dist
set SPEC_PATH=%TEMP_BUILD_DIR%

python -m PyInstaller -v --onefile --windowed --name EasyGelAlyzer ^
    --icon="%ICON_PATH%" ^
    --paths "%~dp0src" ^
    --add-data "%~dp0src\assets;assets" ^
    --workpath "%WORK_PATH%" ^
    --distpath "%DIST_PATH%" ^
    --specpath "%SPEC_PATH%" ^
    "%~dp0src\main.py"

if not exist "%DIST_PATH%\EasyGelAlyzer.exe" (
    echo Build failed.
    pause
    exit /b 1
)

echo Compressing EasyGelAlyzer.exe with UPX...
"%UPX_EXE%" --ultra-brute "%DIST_PATH%\EasyGelAlyzer.exe"

copy /y "%DIST_PATH%\EasyGelAlyzer.exe" "%DIST_DIR%" >nul
copy /y "%~dp0src\version.py" "%DIST_DIR%" >nul
echo EasyGelAlyzer.exe build complete.


rem ============================================================
rem  8. Build launcher.exe (PyInstaller)
rem ============================================================
echo.
echo Building launcher.exe...

set LAUNCHER_TEMP=%TEMP%\LauncherBuild_%RANDOM%
set LAUNCHER_WORK=%LAUNCHER_TEMP%\build
set LAUNCHER_DIST=%LAUNCHER_TEMP%\dist
set LAUNCHER_SPEC=%LAUNCHER_TEMP%

python -m PyInstaller --onefile --windowed ^
    --icon="%ICON_PATH%" ^
    --name launcher ^
    --workpath "%LAUNCHER_WORK%" ^
    --distpath "%LAUNCHER_DIST%" ^
    --specpath "%LAUNCHER_SPEC%" ^
    "%~dp0launcher\launcher.py"

if not exist "%LAUNCHER_DIST%\launcher.exe" (
    echo Launcher build failed.
    pause
    exit /b 1
)

echo Compressing launcher.exe with UPX...
"%UPX_EXE%" --ultra-brute "%LAUNCHER_DIST%\launcher.exe"

copy /y "%LAUNCHER_DIST%\launcher.exe" "%RELEASE_DIR%" >nul
echo launcher.exe build complete.


rem ============================================================
rem  9. Copy PatchNote
rem ============================================================
set PATCH_FILE_NAME=PatchNote_v%CURRENT%.txt
if exist "%PATCHNOTE_SRC%\%PATCH_FILE_NAME%" (
    copy /y "%PATCHNOTE_SRC%\%PATCH_FILE_NAME%" "%RELEASE_DIR%" >nul
)


rem ============================================================
rem  10. Create ZIP
rem ============================================================
set ZIP_NAME=EasyGelAlyzer_v%CURRENT%.zip
powershell -NoProfile -ExecutionPolicy Bypass ^
    Compress-Archive -Path "%RELEASE_DIR%" -DestinationPath "%RELEASE_ROOT%\%ZIP_NAME%" -Force


rem ============================================================
rem  11. Delete Release folder
rem ============================================================
rmdir /s /q "%RELEASE_DIR%"


echo.
echo ============================
echo Release Build Completed
echo Output: %RELEASE_ROOT%\%ZIP_NAME%
echo ============================

pause
