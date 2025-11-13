@echo off
setlocal

REM Paths
set "TARGET=%AppData%\Blender Foundation\Blender\5.1\extensions\user_default\collection_toggle\__init__.py"
set "SOURCE=%~dp0__init__.py"

REM Ensure source file exists
if not exist "%SOURCE%" exit /b 1

REM Copy (overwrite without prompt)
copy /Y "%SOURCE%" "%TARGET%" >nul 2>&1

REM Exit immediately if successful, otherwise show error
if %errorlevel% equ 0 (
    exit
) else (
    echo Failed to replace the file.
    pause
)

endlocal
