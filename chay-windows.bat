@echo off
chcp 65001 >nul
rem Windows: bam dup file nay la render xong va tu mo video.
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
  echo ^>^> Chua co uv, dang cai ^(chi mot lan^)...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
  where uv >nul 2>nul
  if errorlevel 1 (
    echo Cai uv that bai. Kiem tra mang roi thu lai.
    pause
    exit /b 1
  )
)
echo ^>^> Dang render video ^(khoang 1-3 phut^)...
uv run render_v11.py --output noel-ascii.mp4
if errorlevel 1 (
  echo Render that bai.
  pause
  exit /b 1
)
echo ^>^> Xong: %cd%\noel-ascii.mp4
start "" "noel-ascii.mp4"
pause
