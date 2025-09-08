# Установка FFmpeg для работы с аудио

FFmpeg необходим для извлечения и объединения аудио с видео в высоком качестве.

## Windows

### Способ 1: Через Chocolatey (рекомендуется)
```powershell
# Установить Chocolatey (если не установлен)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Установить FFmpeg
choco install ffmpeg
```

### Способ 2: Ручная установка
1. Скачайте FFmpeg с https://ffmpeg.org/download.html
2. Распакуйте архив в папку `C:\ffmpeg`
3. Добавьте `C:\ffmpeg\bin` в переменную PATH:
   - Откройте "Система" → "Дополнительные параметры системы"
   - Нажмите "Переменные среды"
   - В разделе "Системные переменные" найдите "Path" и нажмите "Изменить"
   - Добавьте `C:\ffmpeg\bin`
   - Нажмите "ОК"

### Способ 3: Через winget
```cmd
winget install FFmpeg
```

## macOS

### Через Homebrew
```bash
brew install ffmpeg
```

### Через MacPorts
```bash
sudo port install ffmpeg
```

## Linux

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

### CentOS/RHEL/Fedora
```bash
# CentOS/RHEL
sudo yum install ffmpeg

# Fedora
sudo dnf install ffmpeg
```

### Arch Linux
```bash
sudo pacman -S ffmpeg
```

## Проверка установки

Откройте командную строку/терминал и выполните:
```bash
ffmpeg -version
```

Если FFmpeg установлен правильно, вы увидите информацию о версии.

## Что дает FFmpeg

- **Извлечение аудио** из видео низкого качества
- **Объединение** видео высокого качества с аудио
- **Конвертация** форматов для совместимости
- **Проверка** наличия аудиодорожки в файле

## Без FFmpeg

Приложение будет работать, но с ограничениями:
- Может не скачать аудио для некоторых видео
- Ограниченный выбор форматов
- Возможны проблемы с объединением видео и аудио

## Устранение проблем

### "FFmpeg не найден"
- Убедитесь, что FFmpeg добавлен в PATH
- Перезапустите приложение после установки
- Проверьте установку командой `ffmpeg -version`

### "Ошибка ffmpeg"
- Обновите FFmpeg до последней версии
- Проверьте права доступа к папкам
- Убедитесь, что достаточно места на диске
