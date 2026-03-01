@echo off
setlocal enabledelayedexpansion
title Project Doctor - Batch Crawler
color 0F

:: Phase 6C: Use script-relative paths (consistent with Repo Doctor.bat)
set "REGISTRY=%~dp0repo-registry.py"
set "DOCTOR=%~dp0PROJECT-DOCTOR.md"

:: Check dependencies
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found in PATH.
    pause
    exit /b
)

where claude >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Claude Code CLI not found in PATH.
    echo  Install it first: https://docs.claude.com
    pause
    exit /b
)

if not exist "%DOCTOR%" (
    echo  [ERROR] PROJECT-DOCTOR.md not found at %DOCTOR%
    echo  Run setup first.
    pause
    exit /b
)

:: Initialize registry
python "%REGISTRY%" init 2>nul

cls
echo.
echo  +======================================================+
echo  :         PROJECT DOCTOR  -  Batch Crawler              :
echo  +======================================================+
echo  :                                                       :
echo  :  This will scan a directory for projects and audit    :
echo  :  each one automatically with Claude Code.             :
echo  :                                                       :
echo  :  MODES:                                               :
echo  :   [1] Shallow - Audit each subfolder (1 level deep)  :
echo  :   [2] Deep    - Find all projects in tree (any depth) :
echo  :   [3] List    - Audit specific folders from a file    :
echo  :   [4] Pick    - Scan and choose which to audit        :
echo  :                                                       :
echo  :   [0] Back                                            :
echo  :                                                       :
echo  +======================================================+
echo.
set /p "mode=  Choose mode: "

if "%mode%"=="1" goto SHALLOW
if "%mode%"=="2" goto DEEP
if "%mode%"=="3" goto LISTFILE
if "%mode%"=="4" goto PICK
if "%mode%"=="0" exit /b
goto :eof

:: -------------------------------------------------------
:: AUDIT_ONE subroutine (Phase 6A: centralized audit logic)
:: Usage: call :AUDIT_ONE "path" "name"
:: -------------------------------------------------------
:AUDIT_ONE
set "_apath=%~1"
set "_aname=%~2"
echo.
echo  ------ Auditing: %_aname% ------
python "%REGISTRY%" register "%_apath%" "%_aname%" 2>nul
copy /Y "%DOCTOR%" "%_apath%\PROJECT-DOCTOR.md" >nul 2>nul
pushd "%_apath%"
claude -p PROJECT-DOCTOR.md
if errorlevel 1 (
    echo  [WARNING] Audit may have had issues for %_aname%
    set /a failed+=1
)
popd
set /a done+=1
echo  [OK] %_aname% complete
goto :eof

:: -------------------------------------------------------
:: MODE 1: SHALLOW - every immediate subfolder
:: -------------------------------------------------------
:SHALLOW
cls
echo.
echo  ======================================================
echo   SHALLOW CRAWL - Audit each subfolder
echo  ======================================================
echo.
set /p "root=  Parent directory (e.g. C:\Projects): "
if "%root%"=="" exit /b
if not exist "%root%" (
    echo  [ERROR] Path not found: %root%
    pause
    exit /b
)

:: Count projects
set "count=0"
for /d %%D in ("%root%\*") do set /a count+=1

echo.
echo  Found %count% subfolders in %root%
echo.

:: List them
set "i=0"
for /d %%D in ("%root%\*") do (
    set /a i+=1
    echo    !i!. %%~nxD
)

echo.
echo  Each will be registered and audited sequentially.
echo  Claude Code will open for each project, run the audit,
echo  and results will be saved to the registry.
echo.
set /p "confirm=  Start crawl? (y/n): "
if /i not "%confirm%"=="y" exit /b

:: Process each
set "done=0"
set "failed=0"
for /d %%D in ("%root%\*") do (
    call :AUDIT_ONE "%%D" "%%~nxD"
)

echo.
echo  ======================================================
echo   CRAWL COMPLETE
echo  ======================================================
echo.
echo   Audited: !done!
echo   Issues:  !failed!
echo.
echo   Run the dashboard to see all results:
echo   python "%REGISTRY%" dashboard
echo.
python "%REGISTRY%" status
echo.
pause
exit /b

:: -------------------------------------------------------
:: MODE 2: DEEP - find projects at any depth
:: Phase 6B: Single-pass project discovery
:: -------------------------------------------------------
:DEEP
cls
echo.
echo  ======================================================
echo   DEEP CRAWL - Find projects at any depth
echo  ======================================================
echo.
echo  This finds project roots by looking for indicators:
echo   Code: package.json, requirements.txt, Cargo.toml, go.mod, pyproject.toml
echo.
set /p "root=  Root directory to crawl: "
if "%root%"=="" exit /b
if not exist "%root%" (
    echo  [ERROR] Path not found: %root%
    pause
    exit /b
)

echo.
echo  Scanning for projects...

:: Write project list to temp file
set "listfile=%TEMP%\repo-doctor-crawl.txt"
if exist "%listfile%" del "%listfile%"

:: Single-pass: find all manifest types in one tree traversal
for /r "%root%" %%F in (package.json requirements.txt pyproject.toml Cargo.toml go.mod) do (
    if exist "%%F" (
        set "pdir=%%~dpF"
        set "pdir=!pdir:~0,-1!"
        echo !pdir!>> "%listfile%"
    )
)

:: Deduplicate
if exist "%listfile%" (
    sort "%listfile%" /unique /o "%listfile%"
) else (
    echo  No projects found.
    pause
    exit /b
)

:: Count and display
set "count=0"
for /f "usebackq delims=" %%L in ("%listfile%") do (
    set /a count+=1
    echo    !count!. %%L
)

echo.
echo  Found !count! projects.
echo.
set /p "confirm=  Audit all? (y/n): "
if /i not "%confirm%"=="y" exit /b

:: Process each
set "done=0"
set "failed=0"
for /f "usebackq delims=" %%L in ("%listfile%") do (
    for %%N in ("%%L") do set "projname=%%~nxN"
    call :AUDIT_ONE "%%L" "!projname!"
)

echo.
echo  ======================================================
echo   DEEP CRAWL COMPLETE - !done! projects audited
echo  ======================================================
echo.
python "%REGISTRY%" status
echo.
pause
exit /b

:: -------------------------------------------------------
:: MODE 3: LIST - audit from a text file
:: -------------------------------------------------------
:LISTFILE
cls
echo.
echo  ======================================================
echo   LIST MODE - Audit from a file
echo  ======================================================
echo.
echo  Provide a text file with one project path per line:
echo.
echo  Example projects.txt:
echo    C:\Projects\my-app
echo    C:\Legal\relish-case
echo    C:\School\fall-2025
echo.
set /p "listpath=  Path to list file: "
if "%listpath%"=="" exit /b
if not exist "%listpath%" (
    echo  [ERROR] File not found: %listpath%
    pause
    exit /b
)

:: Count and display
set "count=0"
for /f "usebackq delims=" %%L in ("%listpath%") do (
    set /a count+=1
    echo    !count!. %%L
)

echo.
echo  Found !count! projects in list.
echo.
set /p "confirm=  Audit all? (y/n): "
if /i not "%confirm%"=="y" exit /b

set "done=0"
set "failed=0"
for /f "usebackq delims=" %%L in ("%listpath%") do (
    if exist "%%L" (
        for %%N in ("%%L") do set "projname=%%~nxN"
        call :AUDIT_ONE "%%L" "!projname!"
    ) else (
        echo  [SKIP] Path not found: %%L
    )
)

echo.
echo  ======================================================
echo   LIST CRAWL COMPLETE - !done! projects audited
echo  ======================================================
echo.
python "%REGISTRY%" status
echo.
pause
exit /b

:: -------------------------------------------------------
:: MODE 4: PICK - scan then choose
:: -------------------------------------------------------
:PICK
cls
echo.
echo  ======================================================
echo   PICK MODE - Scan and choose which to audit
echo  ======================================================
echo.
set /p "root=  Parent directory: "
if "%root%"=="" exit /b
if not exist "%root%" (
    echo  [ERROR] Path not found: %root%
    pause
    exit /b
)

echo.
echo  Subfolders found:
echo.

:: List with numbers
set "total=0"
for /d %%D in ("%root%\*") do (
    set /a total+=1
    echo    [!total!] %%~nxD
)

echo.
echo    [A] Audit ALL
echo    [0] Cancel
echo.
set /p "picks=  Enter numbers separated by spaces (e.g. 1 3 5) or A for all: "

if /i "%picks%"=="0" exit /b
if /i "%picks%"=="a" (
    echo  Auditing all...
    set "done=0"
    set "failed=0"
    for /d %%D in ("%root%\*") do (
        call :AUDIT_ONE "%%D" "%%~nxD"
    )
    echo.
    echo  [OK] !done! projects audited.
    python "%REGISTRY%" status
    echo.
    pause
    exit /b
)

:: Process picked numbers
set "done=0"
set "failed=0"
for %%P in (%picks%) do (
    set "idx=0"
    for /d %%D in ("%root%\*") do (
        set /a idx+=1
        if !idx!==%%P (
            call :AUDIT_ONE "%%D" "%%~nxD"
        )
    )
)

echo.
python "%REGISTRY%" status
echo.
pause
exit /b
