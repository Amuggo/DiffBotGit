@echo off
start "EasyDiffusion" "D:\Rabota\EasyDiffusion\Start Stable Diffusion UI.cmd"
timeout /t 10 /nobreak >nul
start "Telegram Bot" cmd /k "python D:\Rabota\DiffBotGit\DiffBot\main.py"
exit