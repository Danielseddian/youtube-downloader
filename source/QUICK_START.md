# 🚀 Быстрый старт - YouTube Downloader

## Создание EXE файла

### 1. Автоматическая сборка (рекомендуется)
```bash
# Просто запустите один из файлов:
build_exe.bat        # Windows Batch
.\build_exe.ps1      # PowerShell
```

### 2. Проверка готовности
```bash
python test_build.py
```

### 3. Ручная сборка
```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name "YouTube Downloader" youtube_downloader.py
```

## Результат

После сборки в папке `dist/` появится файл:
- `YouTube Downloader.exe` (~50-80 МБ)

## Использование

1. Запустите `YouTube Downloader.exe`
2. Вставьте URL YouTube видео
3. Нажмите "Получить информацию"
4. Выберите качество
5. Нажмите "Скачать видео"

## Особенности

- ✅ Работает без установки Python
- ✅ Скачивает видео с аудио
- ✅ Выбор качества видео
- ✅ Проверка дубликатов
- ✅ Красивый интерфейс

## Проблемы?

- **Антивирус блокирует**: Добавьте папку в исключения
- **Медленный запуск**: Первый запуск всегда медленный
- **Большой размер**: Это нормально для приложений с yt-dlp

## Файлы проекта

```
youtube downloader/
├── youtube_downloader.py      # Основной код
├── requirements.txt           # Зависимости
├── build_exe.bat             # Сборка (Batch)
├── build_exe.ps1             # Сборка (PowerShell)
├── test_build.py             # Тест готовности
├── BUILD_INSTRUCTIONS.md     # Подробные инструкции
└── dist/                     # Готовый EXE (после сборки)
    └── YouTube Downloader.exe
```
