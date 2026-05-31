@echo off
echo ============================
echo   EasyGelAlyzer Release Build
echo ============================

rem ============================================================
rem  0. 初期設定
rem ============================================================
cd /d %~dp0


rem ============================================================
rem  1. version.py の読み取り
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
rem  2. Release フォルダ準備
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
rem  3. ドキュメントコピー
rem ============================================================
copy /y "%~dp0LICENSE" "%RELEASE_DIR%" >nul
copy /y "%~dp0README.md" "%RELEASE_DIR%" >nul
copy /y "%~dp0README_EN.md" "%RELEASE_DIR%" >nul


rem ============================================================
rem  4. アイコンコピー
rem ============================================================
set ICON_PATH=%~dp0src\assets\icon.ico
if exist "%ICON_PATH%" copy /y "%ICON_PATH%" "%ASSETS_DIR%" >nul


rem ============================================================
rem  5. テスト画像コピー
rem ============================================================
set TEST_IMG_SRC=%~dp0src\assets\test_gel_image.png
if exist "%TEST_IMG_SRC%" copy /y "%TEST_IMG_SRC%" "%RELEASE_DIR%" >nul


rem ============================================================
rem  6. main EXE ビルド（onefile）
rem ============================================================
echo Building main executable...

set TEMP_BUILD_DIR=%TEMP%\EasyGelAlyzerBuild_%RANDOM%
set WORK_PATH=%TEMP_BUILD_DIR%\build
set DIST_PATH=%TEMP_BUILD_DIR%\dist
set SPEC_PATH=%TEMP_BUILD_DIR%

python -m PyInstaller --onefile --windowed --name EasyGelAlyzer ^
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

copy /y "%DIST_PATH%\EasyGelAlyzer.exe" "%DIST_DIR%" >nul
copy /y "%~dp0src\version.py" "%DIST_DIR%" >nul


rem ============================================================
rem  7. launcher.exe ビルド（onefile）
rem ============================================================
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

copy /y "%LAUNCHER_DIST%\launcher.exe" "%RELEASE_DIR%" >nul


rem ============================================================
rem  8. PatchNote コピー
rem ============================================================
set PATCH_FILE_NAME=PatchNote_v%CURRENT%.txt
if exist "%PATCHNOTE_SRC%\%PATCH_FILE_NAME%" (
    copy /y "%PATCHNOTE_SRC%\%PATCH_FILE_NAME%" "%RELEASE_DIR%" >nul
)


rem ============================================================
rem  9. ZIP 作成
rem ============================================================
set ZIP_NAME=EasyGelAlyzer_v%CURRENT%.zip
powershell -NoProfile -ExecutionPolicy Bypass ^
    Compress-Archive -Path "%RELEASE_DIR%" -DestinationPath "%RELEASE_ROOT%\%ZIP_NAME%" -Force


rem ============================================================
rem  10. Release フォルダ削除
rem ============================================================
rmdir /s /q "%RELEASE_DIR%"


echo ============================
echo Release Build Completed
echo Output: %RELEASE_ROOT%\%ZIP_NAME%
echo ============================

pause