@echo off
title Update Bot ke Cloud (GitHub & Render)
cd /d "%~dp0"
cls
echo ==============================================================
echo        MENGIRIM PERUBAHAN KE CLOUD (GITHUB & RENDER)
echo ==============================================================
echo.
git add .
git commit -m "Update konfigurasi dan data kalkulator kredit"
"C:\Program Files\GitHub CLI\gh.exe" auth setup-git
git push origin master
echo.
echo ==============================================================
echo  BERHASIL! Render akan otomatis memperbarui bot dalam 1-2 menit.
echo ==============================================================
echo.
pause
