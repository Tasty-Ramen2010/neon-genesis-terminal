@echo off
REM ============================================================================
REM  NERV Console - Windows "app" launcher.
REM  Starts the stdlib backend and opens a chromeless standalone window
REM  (Edge/Chrome in --app mode). Falls back to your default browser.
REM
REM    nerv-app-windows.bat [PROJECT_DIR]
REM
REM  Requires Python 3 on PATH (https://www.python.org/downloads/ - tick
REM  "Add python.exe to PATH"). For the full embedded terminal, run under WSL.
REM ============================================================================
setlocal
set "HERE=%~dp0"
where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python "%HERE%nerv-launch.py" --app %*
) else (
  where py >nul 2>nul
  if %ERRORLEVEL%==0 (
    py -3 "%HERE%nerv-launch.py" --app %*
  ) else (
    echo Python 3 was not found on PATH. Install it from https://www.python.org/downloads/
    echo and be sure to tick "Add python.exe to PATH", then re-run this file.
    pause
  )
)
endlocal
