#!/usr/bin/env python3
"""
Тестовый скрипт для проверки готовности к сборке EXE
"""

import sys
import importlib

def test_imports():
    """Проверить все необходимые импорты"""
    required_modules = [
        'tkinter',
        'yt_dlp',
        'threading',
        'subprocess',
        'platform',
        'hashlib',
        'time',
        'pathlib',
        'os'
    ]
    
    print("Проверка импортов...")
    failed_imports = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e}")
            failed_imports.append(module)
    
    return failed_imports

def test_main_script():
    """Проверить основной скрипт"""
    print("\nПроверка основного скрипта...")
    try:
        with open('youtube_downloader.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверить основные компоненты
        checks = [
            ('class YouTubeDownloader', 'Основной класс'),
            ('def __init__', 'Конструктор'),
            ('def download_video', 'Метод скачивания'),
            ('def get_video_info', 'Метод получения информации'),
            ('tkinter', 'GUI библиотека'),
            ('yt_dlp', 'YouTube библиотека'),
        ]
        
        for check, description in checks:
            if check in content:
                print(f"✓ {description}")
            else:
                print(f"✗ {description}")
                return False
                
        return True
    except FileNotFoundError:
        print("✗ Файл youtube_downloader.py не найден")
        return False

def test_requirements():
    """Проверить файл requirements.txt"""
    print("\nПроверка requirements.txt...")
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
        
        required_packages = ['yt-dlp', 'pyinstaller']
        for package in required_packages:
            if package in content:
                print(f"✓ {package}")
            else:
                print(f"✗ {package}")
                return False
        return True
    except FileNotFoundError:
        print("✗ Файл requirements.txt не найден")
        return False

def main():
    print("=" * 50)
    print("  YouTube Downloader - Тест готовности к сборке")
    print("=" * 50)
    
    # Проверки
    failed_imports = test_imports()
    script_ok = test_main_script()
    requirements_ok = test_requirements()
    
    print("\n" + "=" * 50)
    print("  РЕЗУЛЬТАТЫ ПРОВЕРКИ")
    print("=" * 50)
    
    if not failed_imports and script_ok and requirements_ok:
        print("✓ Все проверки пройдены успешно!")
        print("✓ Готов к сборке EXE файла")
        print("\nДля сборки запустите:")
        print("  build_exe.bat  (Windows Batch)")
        print("  .\\build_exe.ps1  (PowerShell)")
        return True
    else:
        print("✗ Обнаружены проблемы:")
        if failed_imports:
            print(f"  - Отсутствуют модули: {', '.join(failed_imports)}")
        if not script_ok:
            print("  - Проблемы с основным скриптом")
        if not requirements_ok:
            print("  - Проблемы с requirements.txt")
        print("\nУстановите недостающие зависимости:")
        print("  pip install -r requirements.txt")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
