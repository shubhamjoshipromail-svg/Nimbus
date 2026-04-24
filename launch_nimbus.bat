@echo off
setlocal

set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

set BASE_URL=%~1
if "%BASE_URL%"=="" set BASE_URL=%NIMBUS_BASE_URL%
if "%BASE_URL%"=="" set BASE_URL=http://localhost:8000

for /f "tokens=1 delims=?" %%A in ("%BASE_URL%") do set URL_NO_QUERY=%%A
if "%BASE_URL%"=="%URL_NO_QUERY%" (
  set APP_URL=%BASE_URL%?mode=app^&fresh=%RANDOM%
) else (
  set APP_URL=%BASE_URL%^&mode=app^&fresh=%RANDOM%
)
set SERVER_URL=%URL_NO_QUERY%/health

set IS_LOCALHOST=0
if /i "%URL_NO_QUERY%"=="http://localhost:8000" set IS_LOCALHOST=1
if /i "%URL_NO_QUERY%"=="http://127.0.0.1:8000" set IS_LOCALHOST=1

if "%IS_LOCALHOST%"=="1" (
  netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
  if errorlevel 1 (
    echo Starting Nimbus server on port 8000...
    start "" /B uvicorn backend.main:app --port 8000
    timeout /t 3 /nobreak >nul
  ) else (
    echo Nimbus server already running on port 8000.
  )
)

powershell -Command "try { $r = Invoke-WebRequest -UseBasicParsing '%SERVER_URL%'; if ($r.StatusCode -ne 200) { exit 1 } } catch { exit 1 }"
if errorlevel 1 (
  echo Nimbus launch failed: server did not respond at %SERVER_URL%
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
