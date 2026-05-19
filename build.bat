@echo off
title J.A.R.V.I.S. Builder
color 0b
echo =========================================================
echo  [+] Guncellenmeler Oxunur ve J.A.R.V.I.S. Yenidən Yigilir...
echo =========================================================
echo.
pyinstaller Jarvis.spec
echo.
echo =========================================================
echo  [+] UGURLU! Yeni My.Jarvis.exe hazirdir: dist/My.Jarvis.exe
echo =========================================================
echo.
pause
