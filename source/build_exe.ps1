# YouTube Downloader - PowerShell скрипт сборки
Write-Host "========================================" -ForegroundColor Green
Write-Host "   YouTube Downloader - Сборка EXE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Проверка Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[✓] Python найден: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[✗] ОШИБКА: Python не найден!" -ForegroundColor Red
    Write-Host "Установите Python 3.7+ с https://python.org" -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host ""
Write-Host "[1/4] Установка зависимостей..." -ForegroundColor Cyan
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[✗] ОШИБКА: Не удалось установить зависимости" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host ""
Write-Host "[1.1/4] Проверка/установка FFmpeg..." -ForegroundColor Cyan
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "FFmpeg не найден. Пытаюсь установить через winget..." -ForegroundColor Yellow
    try {
        winget install --id=Gyan.FFmpeg -e --source=winget | Out-Null
    } catch {
        winget install FFmpeg | Out-Null
    }
}

Write-Host ""
Write-Host "[2/4] Очистка предыдущих сборок..." -ForegroundColor Cyan
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
Get-ChildItem -Name "*.spec" | Remove-Item -Force

Write-Host ""
Write-Host "[3/4] Создание spec файла..." -ForegroundColor Cyan
pyi-makespec --onefile --windowed --name "YouTube Downloader" youtube_downloader.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[✗] ОШИБКА: Не удалось создать spec файл" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host ""
Write-Host "[4/4] Сборка EXE файла..." -ForegroundColor Cyan
pyinstaller "YouTube Downloader.spec"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[✗] ОШИБКА: Не удалось собрать EXE файл" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "    Сборка завершена успешно!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

if (Test-Path "dist\YouTube Downloader.exe") {
    $fileSize = (Get-Item "dist\YouTube Downloader.exe").Length / 1MB
    Write-Host "EXE файл: dist\YouTube Downloader.exe" -ForegroundColor Green
    Write-Host "Размер: $([math]::Round($fileSize, 2)) МБ" -ForegroundColor Green
    Write-Host ""
    Write-Host "Нажмите Enter для открытия папки с результатом..." -ForegroundColor Yellow
    Read-Host
    Start-Process "dist"
} else {
    Write-Host "[✗] ОШИБКА: EXE файл не найден!" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
}
