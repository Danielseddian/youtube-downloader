@echo off
echo ========================================
echo    YouTube Downloader - Сборка EXE
echo ========================================
echo.

echo [1/4] Установка зависимостей...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ОШИБКА: Не удалось установить зависимости
    pause
    exit /b 1
)

echo.
echo [1.1/4] Проверка/установка FFmpeg...
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo FFmpeg не найден. Пытаюсь установить через winget...
    winget install --id=Gyan.FFmpeg -e --source=winget || winget install FFmpeg
)

echo.
echo [2/4] Очистка предыдущих сборок...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del "*.spec"

echo.
echo [3/4] Создание spec файла...
pyi-makespec --onefile --windowed --name "YouTube Downloader" youtube_downloader.py
if %errorlevel% neq 0 (
    echo ОШИБКА: Не удалось создать spec файл
    pause
    exit /b 1
)

echo.
echo [4/4] Сборка EXE файла...
pyinstaller "YouTube Downloader.spec"
if %errorlevel% neq 0 (
    echo ОШИБКА: Не удалось собрать EXE файл
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Сборка завершена успешно!
echo ========================================
echo.
echo EXE файл находится в папке: dist\YouTube Downloader.exe
echo.
echo Нажмите любую клавишу для открытия папки с результатом...
pause >nul

if exist "dist\YouTube Downloader.exe" (
    start "" "dist"
) else (
    echo ОШИБКА: EXE файл не найден!
    pause
)
