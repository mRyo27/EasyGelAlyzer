@echo off
echo ============================
echo   EasyGelAlyzer Auto Build
echo    (with Cython compilation)
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
for /f "tokens=* delims= " %%a in ("%CURRENT%") do set CURRENT=%%a

echo Version: %CURRENT%

rem ---- Parse version numbers ----
for /f "tokens=1-3 delims=." %%a in ("%CURRENT%") do (
    set MAJOR=%%a
    set MINOR=%%b
    set PATCH=%%c
)

echo Building EasyGelAlyzer v%CURRENT%

rem ---- Check required tools ----
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: python not found in PATH.
    pause
    exit /b 1
)

python -c "import Cython" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Cython not found. Installing...
    python -m pip install cython
    python -c "import Cython" >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install Cython.
        pause
        exit /b 1
    )
    echo Cython installed successfully.
) else (
    echo Cython already installed. Skipping.
)

python -c "import PyInstaller" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
    python -c "import PyInstaller" >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install PyInstaller.
        pause
        exit /b 1
    )
    echo PyInstaller installed successfully.
) else (
    echo PyInstaller already installed. Skipping.
)

rem ---- Run git commands if git is available ----
where git >nul 2>nul
if %ERRORLEVEL% equ 0 (
    git add .
    git commit -m "Build v%CURRENT%"
    git tag v%CURRENT% >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo Tag v%CURRENT% already exists. Skipping tag.
    ) else (
        echo Tagged v%CURRENT%.
    )
) else (
    echo Git not found, skipping git tagging.
)

rem ================================================================
rem  STEP 1: Cython compile  src/**/*.py  ¨  .pyd  (in-place)
rem ================================================================
echo.
echo [Step 1] Cython compile...

rem ---- Check for Visual C++ compiler (cl.exe) ----
where cl >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Microsoft Visual C++ Build Tools not found.
    echo Please install from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo Select "C++ Build Tools" workload during installation.
    echo After installation, re-run this script from a "Developer Command Prompt for VS"
    echo or run vcvarsall.bat before this script.
    pause
    exit /b 1
)

rem ---- Write setup_cython.py to a temp file ----
rem     NOTE: Run from inside src/ so --inplace resolves correctly.
set SETUP_PY=%TEMP%\setup_cython_%RANDOM%.py
(
echo from setuptools import setup
echo from Cython.Build import cythonize
echo import glob, os
echo.
echo # CWD is src/ when this script runs
echo src_root = os.path.abspath("."^)
echo exclude = {"main.py", "version.py"}
echo.
echo py_files = []
echo for path in glob.glob(os.path.join(src_root, "**", "*.py"^), recursive=True^):
echo     fname = os.path.basename(path^)
echo     if fname not in exclude:
echo         py_files.append(os.path.relpath(path, src_root^)^)
echo.
echo setup(
echo     ext_modules=cythonize(
echo         py_files,
echo         compiler_directives={"language_level": "3"},
echo         nthreads=0,
echo     ^),
echo     script_args=["build_ext", "--inplace"],
echo ^)
) > "%SETUP_PY%"

pushd "%~dp0src"
python "%SETUP_PY%"
set CYTHON_RESULT=%ERRORLEVEL%
popd

if %CYTHON_RESULT% neq 0 (
    echo Error: Cython compilation failed.
    del "%SETUP_PY%" 2>nul
    pause
    exit /b 1
)
del "%SETUP_PY%" 2>nul
echo Cython compilation done.

rem ================================================================
rem  STEP 2: Remove generated .c files and build/ dir (keep workspace clean)
rem ================================================================
echo.
echo [Step 2] Cleaning up Cython C sources and build directory...
for /r "%~dp0src" %%f in (*.c) do del "%%f" 2>nul
rmdir /s /q "%~dp0src\build" 2>nul

rem ================================================================
rem  STEP 3: PyInstaller packaging
rem ================================================================
echo.
echo [Step 3] PyInstaller packaging...

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

rem ---- Collect compiled .pyd files so PyInstaller can pick them up ----
rem     --paths points to src/ so that both .py and .pyd are discoverable.
rem     --hidden-import entries cover any module that Cython may have renamed
rem     internally (Cython keeps the same module name, so the same list works).

python -m PyInstaller ^
    --onefile --windowed ^
    --name EasyGelAlyzer ^
    %ICON_OPT% ^
    --paths "%~dp0src" ^
    --add-data "%~dp0src\assets;assets" ^
    --collect-all i18n ^
    --hidden-import i18n ^
    --hidden-import i18n.translations ^
    --hidden-import ui ^
    --hidden-import ui.main_window ^
    --hidden-import ui.dialogs ^
    --hidden-import ui.preset_manager ^
    --hidden-import core ^
    --hidden-import core.annotation ^
    --hidden-import core.calibration ^
    --hidden-import core.excel_export ^
    --hidden-import core.image_export ^
    --hidden-import core.image_manager ^
    --hidden-import core.image_proc ^
    --hidden-import core.marker_presets ^
    --hidden-import core.project_io ^
    --hidden-import core.utils ^
    --hidden-import matplotlib.backends.backend_svg ^
    --hidden-import matplotlib.backends.backend_pdf ^
    --workpath "%WORK_PATH%" ^
    --distpath "%DIST_PATH%" ^
    --specpath "%SPEC_PATH%" ^
    "%~dp0src\main.py"

rem ---- Copy the built executable back to local workspace ----
if exist "%DIST_PATH%\EasyGelAlyzer.exe" (
    mkdir "%~dp0dist" 2>nul
    copy /y "%DIST_PATH%\EasyGelAlyzer.exe" "%~dp0dist\EasyGelAlyzer.exe"
)

rem ---- Clean temporary build directory ----
rmdir /s /q "%TEMP_BUILD_DIR%" 2>nul

rem ================================================================
rem  STEP 4: Clean up .pyd files generated by Cython (optional)
rem          Comment out these lines if you want to keep .pyd for
rem          faster incremental rebuilds.
rem ================================================================
echo.
echo [Step 4] Cleaning up Cython .pyd files...
for /r "%~dp0src" %%f in (*.pyd) do del "%%f" 2>nul

rem ---- Create shortcut ----
set SC_PATH=%~dp0EasyGelAlyzer.lnk
set EXE_PATH=%~dp0dist\EasyGelAlyzer.exe
set TEMP_VBS=%TEMP%\CreateShortcut_%RANDOM%.vbs

if not exist "%EXE_PATH%" goto :BUILD_FAIL

:CREATE_SHORTCUT
echo Set ws = CreateObject("WScript.Shell") > "%TEMP_VBS%"
echo Set sc = ws.CreateShortcut("%SC_PATH%") >> "%TEMP_VBS%"
echo sc.TargetPath = "%EXE_PATH%" >> "%TEMP_VBS%"
echo sc.WorkingDirectory = "%~dp0dist" >> "%TEMP_VBS%"
if exist "%ICON_PATH%" echo sc.IconLocation = "%ICON_PATH%" >> "%TEMP_VBS%"
echo sc.Save >> "%TEMP_VBS%"

cscript //nologo "%TEMP_VBS%"
del "%TEMP_VBS%" 2>nul
echo.
echo ============================
echo   Build completed: v%CURRENT%
echo ============================
goto :END

:BUILD_FAIL
echo.
echo Error: Build failed, executable not found.

:END
pause
