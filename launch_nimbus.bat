@echo off
setlocal

set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

set APP_URL=http://localhost:8000?mode=app&fresh=%RANDOM%

netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
if errorlevel 1 (
  echo Starting Nimbus server on port 8000...
  start "" /B uvicorn backend.main:app --port 8000
  timeout /t 3 /nobreak >nul
) else (
  echo Nimbus server already running on port 8000.
)

powershell -Command "try { $r = Invoke-WebRequest -UseBasicParsing http://localhost:8000/health; if ($r.StatusCode -ne 200) { exit 1 } } catch { exit 1 }"
if errorlevel 1 (
  echo Nimbus launch failed: server did not respond at http://localhost:8000/health
  exit /b 1
)

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
  start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app="%APP_URL%" --window-size=130,150 --window-position=1750,100 --no-default-browser-check --disable-features=TranslateUI
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
  start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --app="%APP_URL%" --window-size=130,150 --window-position=1750,100 --no-default-browser-check --disable-features=TranslateUI
) else (
  start "" "%APP_URL%"
)

echo ✨ Nimbus is floating on your desktop. Drag it anywhere you like.
