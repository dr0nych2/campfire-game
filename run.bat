@echo off
chcp 65001 > nul
title Костёр — Симулятор розжига
echo Запуск симулятора костра...
python main.py
if errorlevel 1 (
    echo.
    echo Ошибка при запуске! Убедитесь, что установлен pygame: pip install pygame
    pause
)
