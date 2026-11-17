@echo off
chcp 65001 >nul
echo ==========================================
echo 🔥 Сборка Campfire.exe... Подожди 20 сек
echo ==========================================

:: Проверяем, установлен ли pyinstaller, если нет — ставим
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Устанавливаю PyInstaller...
    pip install pyinstaller
)

:: Собираем игру в один .exe файл без консоли
pyinstaller --onefile --noconsole --clean --name "Campfire" main.py

echo.
echo ==========================================
echo ✅ Готово! Файл лежит в папке: dist\Campfire.exe
echo ==========================================
pause