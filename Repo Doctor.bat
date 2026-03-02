@echo off
setlocal enabledelayedexpansion
title Repo Doctor - Registry Manager
color 0F

set "REGISTRY=%~dp0repo-registry.py"
set "DOCTOR=%~dp0PROJECT-DOCTOR.md"
set "DB=%~dp0registry.db"

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python is not installed or not in your PATH.
    echo  Download it from https://python.org and make sure "Add to PATH" is checked.
    echo.
    pause
    exit /b
)

:: Auto-init database if it doesn't exist
if not exist "%DB%" (
    echo.
    echo  First run detected - initializing database...
    python "%REGISTRY%" init
    echo.
)

:MENU
cls
echo.
echo  +======================================================+
echo  :            REPO DOCTOR  Registry Manager              :
echo  +=== AUDIT ===========================================+
echo  :                                                       :
echo  :   [1]  Audit a Project  - Register + run full audit   :
echo  :   [2]  Batch Crawl      - Audit multiple projects     :
echo  :   [3]  Register Only    - Add project without auditing:
echo  :                                                       :
echo  +=== BROWSE ===========================================+
echo  :                                                       :
echo  :   [4]  Dashboard        - Portfolio overview          :
echo  :   [5]  Portfolio        - Business intelligence view  :
echo  :   [6]  Status           - All projects at a glance    :
echo  :   [7]  Brief            - One-page project summary    :
echo  :   [8]  History          - Audit history for a project :
echo  :   [9]  Diff             - Compare last 2 audits       :
echo  :   [10] Search           - Find projects by keyword    :
echo  :                                                       :
echo  +=== INTELLIGENCE ====================================+
echo  :                                                       :
echo  :   [11] Actions          - All open issues, all projects:
echo  :   [12] Stale            - Projects needing attention  :
echo  :   [13] Overlap          - Shared tech across projects :
echo  :   [14] Me               - Personal development report :
echo  :                                                       :
echo  +=== DOCUMENTS =======================================+
echo  :                                                       :
echo  :   [15] Doc Scan         - Extract + index all docs    :
echo  :   [16] Doc Search       - Full-text search everything :
echo  :   [17] Doc Entities     - Dates, amounts, emails, etc :
echo  :   [18] Doc Info         - Document stats for project  :
echo  :   [19] OCR Check        - Check installed tools       :
echo  :                                                       :
echo  +=== MANAGE ===========================================+
echo  :                                                       :
echo  :   [20] Tags             - Tag a project               :
echo  :   [21] Value            - Set revenue/client/priority :
echo  :   [22] Note             - Add a note                  :
echo  :   [23] Relate           - Link two projects           :
echo  :   [24] Export           - Export all data (JSON)       :
echo  :   [25] Open DB Folder   - Open in Explorer            :
echo  :                                                       :
echo  :   [0]  Exit                                           :
echo  :                                                       :
echo  +======================================================+
echo.
set /p "choice=  Enter choice: "

if "%choice%"=="1" goto AUDIT
if "%choice%"=="2" goto BATCHCRAWL
if "%choice%"=="3" goto REGISTER
if "%choice%"=="4" goto DASHBOARD
if "%choice%"=="5" goto PORTFOLIO
if "%choice%"=="6" goto STATUS
if "%choice%"=="7" goto BRIEF
if "%choice%"=="8" goto HISTORY
if "%choice%"=="9" goto DIFF
if "%choice%"=="10" goto SEARCH
if "%choice%"=="11" goto ACTIONS
if "%choice%"=="12" goto STALE
if "%choice%"=="13" goto OVERLAP
if "%choice%"=="14" goto ME
if "%choice%"=="15" goto DOCSCAN
if "%choice%"=="16" goto DOCSEARCH
if "%choice%"=="17" goto DOCENTITIES
if "%choice%"=="18" goto DOCINFO
if "%choice%"=="19" goto OCRCHECK
if "%choice%"=="20" goto TAGS
if "%choice%"=="21" goto VALUE
if "%choice%"=="22" goto NOTE
if "%choice%"=="23" goto RELATE
if "%choice%"=="24" goto EXPORT
if "%choice%"=="25" goto OPENDB
if "%choice%"=="0" exit /b

echo  Invalid choice.
timeout /t 2 >nul
goto MENU

:: -------------------------------------------------------
:AUDIT
cls
echo.
echo  ======================================================
echo   AUDIT A PROJECT
echo  ======================================================
echo.
echo  This will:
echo    1. Register the project in your database (if new)
echo    2. Copy PROJECT-DOCTOR.md into the project folder
echo    3. Launch Claude Code to run the full audit
echo.
echo  Auto-detects: code, legal docs, school work, business, etc.
echo.
set /p "rpath=  Project path (e.g. C:\Projects\my-app): "
if "%rpath%"=="" goto MENU

:: Validate path exists
if not exist "%rpath%" (
    echo.
    echo  [ERROR] Path does not exist: %rpath%
    echo.
    pause
    goto MENU
)

:: Derive repo name from folder
for %%I in ("%rpath%") do set "rname=%%~nxI"
echo.
echo  Detected repo name: %rname%
set /p "rname_override=  Repo name [press Enter to keep '%rname%']: "
if not "%rname_override%"=="" set "rname=%rname_override%"

:: Try to grab remote URL if it's a git repo
set "rremote="
pushd "%rpath%" 2>nul
if exist ".git" (
    for /f "delims=" %%R in ('git remote get-url origin 2^>nul') do set "rremote=%%R"
)
popd

:: Register
echo.
if "%rremote%"=="" (
    python "%REGISTRY%" register "%rpath%" "%rname%"
) else (
    echo  Remote: %rremote%
    python "%REGISTRY%" register "%rpath%" "%rname%" --remote "%rremote%"
)

:: Copy PROJECT-DOCTOR.md into repo
echo.
if exist "%DOCTOR%" (
    copy /Y "%DOCTOR%" "%rpath%\PROJECT-DOCTOR.md" >nul
    echo  [OK] Copied PROJECT-DOCTOR.md into %rpath%
) else (
    echo  [WARNING] PROJECT-DOCTOR.md not found in %~dp0
    echo  Place it next to this .bat file for auto-copy.
)

:: Check if Claude Code is available
echo.
where claude >nul 2>&1
if errorlevel 1 (
    echo  ======================================================
    echo  Claude Code CLI not found in PATH.
    echo  To run the audit manually, open a terminal and run:
    echo.
    echo    cd "%rpath%"
    echo    claude -p PROJECT-DOCTOR.md
    echo.
    echo  Or if using Claude Code interactively:
    echo    cd "%rpath%"
    echo    claude
    echo    /read PROJECT-DOCTOR.md
    echo    Run the full repo health check
    echo  ======================================================
    echo.
    pause
    goto MENU
)

:: Launch Claude Code
echo.
echo  ======================================================
echo   Launching Claude Code audit on: %rname%
echo  ======================================================
echo.
echo  Claude Code will run the full audit in this window.
echo  Results will be saved to the registry automatically.
echo.
set /p "confirm=  Launch now? (y/n): "
if /i not "%confirm%"=="y" goto MENU

pushd "%rpath%"
claude -p PROJECT-DOCTOR.md
set "audit_exit=%errorlevel%"
popd

echo.
if !audit_exit! neq 0 (
    echo  [WARNING] Claude Code exited with errors.
)

:: Verify audit was saved
echo.
echo  Verifying registry...
python "%REGISTRY%" history "%rname%" 2>nul | findstr /c:"Score:" >nul 2>&1
if errorlevel 1 (
    echo  [WARNING] No audit found in registry for %rname%.
    echo  The audit may not have saved its results.
    echo  You can re-run or manually import results.
) else (
    echo  [OK] Audit saved to registry.
)
echo.
python "%REGISTRY%" status "%rname%"
echo.
pause
goto MENU

:: -------------------------------------------------------
:BATCHCRAWL
start "" "%~dp0Batch Crawler.bat"
goto MENU

:: -------------------------------------------------------
:REGISTER
cls
echo.
echo  ======================================================
echo   REGISTER PROJECT (without auditing)
echo  ======================================================
echo.
set /p "rpath=  Project path (e.g. C:\Projects\my-app): "
if "%rpath%"=="" goto MENU

:: Validate path exists
if not exist "%rpath%" (
    echo.
    echo  [ERROR] Path does not exist: %rpath%
    echo.
    pause
    goto MENU
)

:: Derive repo name from folder
for %%I in ("%rpath%") do set "rname=%%~nxI"
echo.
echo  Detected repo name: %rname%
set /p "rname_override=  Repo name [press Enter to keep '%rname%']: "
if not "%rname_override%"=="" set "rname=%rname_override%"

set /p "rremote=  Remote URL (optional, press Enter to skip): "
set /p "rdesc=  Description (optional, press Enter to skip): "

set "cmd=python "%REGISTRY%" register "%rpath%" "%rname%""
if not "%rremote%"=="" set "cmd=%cmd% --remote "%rremote%""
if not "%rdesc%"=="" set "cmd=%cmd% --desc "%rdesc%""

echo.
%cmd%
echo.
pause
goto MENU

:: -------------------------------------------------------
:DASHBOARD
cls
echo.
echo  ======================================================
echo   DASHBOARD
echo  ======================================================
echo.
python "%REGISTRY%" dashboard
echo.
pause
goto MENU

:: -------------------------------------------------------
:STATUS
cls
echo.
echo  ======================================================
echo   ALL REPOS
echo  ======================================================
echo.
python "%REGISTRY%" status
echo.
pause
goto MENU

:: -------------------------------------------------------
:PORTFOLIO
cls
echo.
echo  ======================================================
echo   PORTFOLIO - Business Intelligence View
echo  ======================================================
echo.
python "%REGISTRY%" portfolio
echo.
pause
goto MENU

:: -------------------------------------------------------
:BRIEF
cls
echo.
echo  ======================================================
echo   PROJECT BRIEF
echo  ======================================================
echo.
echo  Current projects:
echo.
python "%REGISTRY%" status
echo.
set /p "repo=  Enter project name: "
if "%repo%"=="" goto MENU
echo.
python "%REGISTRY%" brief "%repo%"
echo.
set /p "exprt=  Export to markdown? (y/n): "
if /i "%exprt%"=="y" python "%REGISTRY%" brief-export "%repo%"
echo.
pause
goto MENU

:: -------------------------------------------------------
:DIFF
cls
echo.
echo  ======================================================
echo   AUDIT DIFF - Compare Last 2 Audits
echo  ======================================================
echo.
echo  Current projects:
echo.
python "%REGISTRY%" status
echo.
set /p "repo=  Enter project name: "
if "%repo%"=="" goto MENU
echo.
python "%REGISTRY%" diff "%repo%"
echo.
pause
goto MENU

:: -------------------------------------------------------
:ACTIONS
cls
echo.
echo  ======================================================
echo   ACTION ITEMS - All Open Issues, All Projects
echo  ======================================================
echo.
python "%REGISTRY%" actions
echo.
pause
goto MENU

:: -------------------------------------------------------
:STALE
cls
echo.
echo  ======================================================
echo   STALE PROJECTS - Needing Attention
echo  ======================================================
echo.
python "%REGISTRY%" stale
echo.
pause
goto MENU

:: -------------------------------------------------------
:OVERLAP
cls
echo.
echo  ======================================================
echo   TECH OVERLAP - Shared Across Projects
echo  ======================================================
echo.
python "%REGISTRY%" overlap
echo.
pause
goto MENU

:: -------------------------------------------------------
:VALUE
cls
echo.
echo  ======================================================
echo   SET BUSINESS VALUE
echo  ======================================================
echo.
echo  Current projects:
echo.
python "%REGISTRY%" status
echo.
set /p "repo=  Enter project name: "
if "%repo%"=="" goto MENU
set /p "vrev=  Monthly revenue (e.g. 2k/mo, press Enter to skip): "
set /p "vclient=  Client name (press Enter to skip): "
set /p "vpri=  Priority 1-5 (1=highest, press Enter to skip): "

set "cmd=python "%REGISTRY%" value "%repo%""
if not "%vrev%"=="" set "cmd=%cmd% --revenue "%vrev%""
if not "%vclient%"=="" set "cmd=%cmd% --client "%vclient%""
if not "%vpri%"=="" set "cmd=%cmd% --priority "%vpri%""

echo.
%cmd%
echo.
pause
goto MENU

:: -------------------------------------------------------
:HISTORY
cls
echo.
echo  ======================================================
echo   AUDIT HISTORY
echo  ======================================================
echo.
echo  Current repos:
echo.
python "%REGISTRY%" status
echo.
set /p "repo=  Enter repo name: "
if "%repo%"=="" goto MENU
echo.
python "%REGISTRY%" history "%repo%"
echo.
pause
goto MENU

:: -------------------------------------------------------
:SEARCH
cls
echo.
echo  ======================================================
echo   SEARCH REPOS
echo  ======================================================
echo.
set /p "query=  Search for (name, language, tag): "
if "%query%"=="" goto MENU
echo.
python "%REGISTRY%" search "%query%"
echo.
pause
goto MENU

:: -------------------------------------------------------
:ME
cls
echo.
echo  ======================================================
echo   PERSONAL DEVELOPMENT REPORT
echo  ======================================================
echo.
python "%REGISTRY%" me
echo.
set /p "exprt=  Export to file? (y/n): "
if /i "%exprt%"=="y" python "%REGISTRY%" me-export
echo.
pause
goto MENU

:: -------------------------------------------------------
:DOCSCAN
cls
echo.
echo  ======================================================
echo   DOCUMENT SCAN - Extract + Index Documents
echo  ======================================================
echo.
echo  Current projects:
echo.
python "%REGISTRY%" status
echo.
set /p "repo=  Enter project name to scan: "
if "%repo%"=="" goto MENU
echo.
python "%~dp0doc-intel.py" scan "%repo%"
echo.
pause
goto MENU

:: -------------------------------------------------------
:DOCSEARCH
cls
echo.
echo  ======================================================
echo   DOCUMENT SEARCH - Full-Text Across All Projects
echo  ======================================================
echo.
set /p "query=  Search for: "
if "%query%"=="" goto MENU
set /p "proj=  Limit to project (press Enter for all): "
echo.
if "%proj%"=="" (
    python "%~dp0doc-intel.py" search "%query%"
) else (
    python "%~dp0doc-intel.py" search "%query%" --project "%proj%"
)
echo.
pause
goto MENU

:: -------------------------------------------------------
:DOCENTITIES
cls
echo.
echo  ======================================================
echo   ENTITIES - Dates, Amounts, Emails, Phones, Cases
echo  ======================================================
echo.
echo  Current projects:
echo.
python "%REGISTRY%" status
echo.
set /p "repo=  Enter project name: "
if "%repo%"=="" goto MENU
echo.
echo  Filter by type (optional): date, amount, email, phone, case_number
set /p "etype=  Entity type (Enter for all): "
echo.
if "%etype%"=="" (
    python "%~dp0doc-intel.py" entities "%repo%"
) else (
    python "%~dp0doc-intel.py" entities "%repo%" "%etype%"
)
echo.
pause
goto MENU

:: -------------------------------------------------------
:DOCINFO
cls
echo.
echo  ======================================================
echo   DOCUMENT INFO - Stats for a Project
echo  ======================================================
echo.
echo  Current projects:
echo.
python "%REGISTRY%" status
echo.
set /p "repo=  Enter project name: "
if "%repo%"=="" goto MENU
echo.
python "%~dp0doc-intel.py" info "%repo%"
echo.
pause
goto MENU

:: -------------------------------------------------------
:OCRCHECK
cls
echo.
echo  ======================================================
echo   OCR DEPENDENCY CHECK
echo  ======================================================
echo.
python "%~dp0doc-intel.py" ocr-check
echo.
echo  Install missing tools, then re-scan your projects.
echo.
pause
goto MENU

:: -------------------------------------------------------
:TAGS
cls
echo.
echo  ======================================================
echo   TAG A REPO
echo  ======================================================
echo.
echo  Current repos:
echo.
python "%REGISTRY%" status
echo.
set /p "repo=  Enter repo name: "
if "%repo%"=="" goto MENU
set /p "tags=  Enter tags (space-separated, e.g. client production v2): "
if "%tags%"=="" goto MENU
echo.
python "%REGISTRY%" tags "%repo%" %tags%
echo.
pause
goto MENU

:: -------------------------------------------------------
:NOTE
cls
echo.
echo  ======================================================
echo   ADD NOTE TO REPO
echo  ======================================================
echo.
echo  Current repos:
echo.
python "%REGISTRY%" status
echo.
set /p "repo=  Enter repo name: "
if "%repo%"=="" goto MENU
set /p "note=  Enter note: "
if "%note%"=="" goto MENU
echo.
python "%REGISTRY%" note "%repo%" "%note%"
echo.
pause
goto MENU

:: -------------------------------------------------------
:RELATE
cls
echo.
echo  ======================================================
echo   LINK TWO REPOS
echo  ======================================================
echo.
echo  Current repos:
echo.
python "%REGISTRY%" status
echo.
set /p "src=  Source repo name: "
if "%src%"=="" goto MENU
set /p "tgt=  Target repo name: "
if "%tgt%"=="" goto MENU
echo.
echo  Relationship types: depends_on, fork_of, related_to, deploys_to
set /p "rel=  Relationship: "
if "%rel%"=="" goto MENU
set /p "rnotes=  Notes (optional): "
echo.
if "%rnotes%"=="" (
    python "%REGISTRY%" relate "%src%" "%tgt%" "%rel%"
) else (
    python "%REGISTRY%" relate "%src%" "%tgt%" "%rel%" "%rnotes%"
)
echo.
pause
goto MENU

:: -------------------------------------------------------
:EXPORT
cls
echo.
echo  ======================================================
echo   EXPORT REGISTRY
echo  ======================================================
echo.
set "EXPORT_FILE=%~dp0registry-export-%date:~-4%%date:~4,2%%date:~7,2%.json"
echo  Exporting to: %EXPORT_FILE%
echo.
python "%REGISTRY%" export --format json > "%EXPORT_FILE%"
echo  Done! Exported to %EXPORT_FILE%
echo.
pause
goto MENU

:: -------------------------------------------------------
:OPENDB
explorer "%~dp0"
goto MENU
