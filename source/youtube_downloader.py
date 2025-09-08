import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp
import os
import threading
import subprocess
import platform
import hashlib
import time
import shutil
from pathlib import Path

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # Переменные
        self.download_path = tk.StringVar()
        self.url = tk.StringVar()
        self.is_downloading = False
        self.available_formats = []
        self.selected_format = tk.StringVar()
        self.video_info = None
        
        # Переменные для отслеживания ошибок и возобновления
        self.errors_count = 0
        self.temp_file_size = 0
        self.current_temp_file = None
        self.download_cancelled = False
        self.download_thread = None
        self.is_resuming = False

        # Пути к ffmpeg/ffprobe (автодетект)
        self.ffmpeg_path = None
        self.ffprobe_path = None
        
        # Отслеживание этапов
        self.current_stage = 0
        self.total_stages = 4
        self.stage_names = [
            "Скачивание основного видео потока",
            "Скачивание дополнительного потока", 
            "Получение звуковой дорожки",
            "Объединение звуковой дорожки с основным видео потоком"
        ]
        
        # Установить папку Downloads по умолчанию
        self.set_default_download_path()
        
        # Сначала инициализируем UI
        self.setup_ui()
        
        # Затем проверяем наличие временных файлов (теперь log_text уже существует)
        self.check_for_temp_files()

        # Определить пути к ffmpeg/ffprobe
        self.detect_ffmpeg_paths()
        
    def set_default_download_path(self):
        """Установить папку Downloads по умолчанию"""
        home = Path.home()
        downloads_path = home / "Downloads"
        self.download_path.set(str(downloads_path))
        
    def check_for_temp_files(self):
        """Проверить наличие временных файлов при запуске"""
        try:
            download_dir = Path(self.download_path.get())
            if not download_dir.exists():
                return
                
            # Ищем временные файлы
            temp_files = list(download_dir.glob("temp_*"))
            if temp_files:
                # Найти самый новый временный файл
                latest_temp = max(temp_files, key=os.path.getmtime)
                self.current_temp_file = str(latest_temp)
                self.temp_file_size = os.path.getsize(latest_temp)
                self.log_message(f"🔄 Найден временный файл: {latest_temp.name}")
                self.log_message("Можно возобновить загрузку")
        except Exception as e:
            self.log_message(f"⚠️ Ошибка проверки временных файлов: {e}")

    def detect_ffmpeg_paths(self):
        """Автоматически определить пути к ffmpeg/ffprobe и сохранить в self.ffmpeg_path/self.ffprobe_path"""
        try:
            # 1) Если доступны в PATH — используем их
            import shutil as _sh
            ff = _sh.which('ffmpeg')
            fp = _sh.which('ffprobe')
            if ff:
                self.ffmpeg_path = ff
            if fp:
                self.ffprobe_path = fp

            # 2) WinGet путь Gyan.FFmpeg (частый случай)
            if platform.system() == 'Windows' and (not self.ffmpeg_path or not self.ffprobe_path):
                base = os.path.join(os.getenv('LOCALAPPDATA') or '', 'Microsoft', 'WinGet', 'Packages')
                try:
                    # Ищем каталог Gyan.FFmpeg*
                    for name in os.listdir(base):
                        if name.lower().startswith('gyan.ffmpeg'):
                            bin_dir = os.path.join(base, name, 'ffmpeg-8.0-full_build', 'bin')
                            ff_cand = os.path.join(bin_dir, 'ffmpeg.exe')
                            fp_cand = os.path.join(bin_dir, 'ffprobe.exe')
                            if os.path.exists(ff_cand):
                                self.ffmpeg_path = self.ffmpeg_path or ff_cand
                            if os.path.exists(fp_cand):
                                self.ffprobe_path = self.ffprobe_path or fp_cand
                except Exception:
                    pass

            # Лог
            if self.ffmpeg_path:
                self.log_message(f"FFmpeg: {self.ffmpeg_path}")
            else:
                self.log_message("FFmpeg не найден в PATH. Можно указать путь вручную.")
            if self.ffprobe_path:
                self.log_message(f"FFprobe: {self.ffprobe_path}")
        except Exception as e:
            self.log_message(f"⚠️ Автоопределение FFmpeg не удалось: {e}")
        
    def open_download_folder(self):
        """Открыть папку с загруженными файлами"""
        folder_path = self.download_path.get()
        if os.path.exists(folder_path):
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])
        else:
            messagebox.showerror("Ошибка", "Папка не найдена")
            
    def show_success_dialog(self, title, file_path):
        """Показать диалог успешного скачивания с кнопкой открытия папки"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Скачивание завершено")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрировать диалог
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"400x200+{x}+{y}")
        
        # Содержимое диалога
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Иконка успеха
        success_label = ttk.Label(frame, text="✅", font=("Arial", 24))
        success_label.pack(pady=(0, 10))
        
        # Сообщение
        message_label = ttk.Label(frame, text=f"Видео '{title}' успешно скачано!", 
                                font=("Arial", 12, "bold"))
        message_label.pack(pady=(0, 10))
        
        # Путь к файлу
        path_label = ttk.Label(frame, text=f"Сохранено в:\n{file_path}", 
                             font=("Arial", 9), foreground="gray")
        path_label.pack(pady=(0, 20))
        
        # Кнопки
        button_frame = ttk.Frame(frame)
        button_frame.pack()
        
        open_button = ttk.Button(button_frame, text="Открыть папку", 
                               command=lambda: [self.open_download_folder(), dialog.destroy()])
        open_button.pack(side=tk.LEFT, padx=(0, 10))
        
        close_button = ttk.Button(button_frame, text="Закрыть", 
                                command=dialog.destroy)
        close_button.pack(side=tk.LEFT)
        
    def show_error_dialog(self, error_msg, temp_file_path=None):
        """Показать диалог с ошибкой и рекомендациями"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Ошибка загрузки")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрировать диалог
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (400 // 2)
        dialog.geometry(f"500x400+{x}+{y}")
        
        # Содержимое диалога
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Иконка ошибки
        error_label = ttk.Label(frame, text="❌", font=("Arial", 24))
        error_label.pack(pady=(0, 10))
        
        # Заголовок
        title_label = ttk.Label(frame, text="Ошибка при загрузке", 
                              font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Анализ ошибки и рекомендации
        recommendations = self.analyze_error(error_msg)
        
        # Текстовое поле с ошибкой и рекомендациями
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        text_widget = tk.Text(text_frame, height=12, width=60, wrap=tk.WORD)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Вставить текст
        text_content = f"ОШИБКА:\n{error_msg}\n\n"
        text_content += f"РЕКОМЕНДАЦИИ:\n{recommendations}\n\n"
        if temp_file_path and os.path.exists(temp_file_path):
            file_size = os.path.getsize(temp_file_path) / (1024 * 1024)
            text_content += f"ВРЕМЕННЫЙ ФАЙЛ:\n{temp_file_path}\nРазмер: {file_size:.1f} МБ"
        
        text_widget.insert(tk.END, text_content)
        text_widget.config(state="disabled")
        
        # Кнопки
        button_frame = ttk.Frame(frame)
        button_frame.pack()
        
        if temp_file_path and os.path.exists(temp_file_path):
            resume_button = ttk.Button(button_frame, text="Возобновить", 
                                     command=lambda: [self.resume_download(), dialog.destroy()])
            resume_button.pack(side=tk.LEFT, padx=(0, 10))
            
            delete_button = ttk.Button(button_frame, text="Прервать и удалить", 
                                     command=lambda: [self.delete_temp_file(temp_file_path), dialog.destroy()])
            delete_button.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_button = ttk.Button(button_frame, text="Прервать", 
                                 command=lambda: [self.cancel_download(), dialog.destroy()])
        cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        
        close_button = ttk.Button(button_frame, text="Закрыть", 
                                command=dialog.destroy)
        close_button.pack(side=tk.LEFT)
        
    def analyze_error(self, error_msg):
        """Анализировать ошибку и дать рекомендации"""
        error_lower = error_msg.lower()
        
        if any(keyword in error_lower for keyword in ['connection', 'network', 'timeout', 'unreachable']):
            return """• Проверьте подключение к интернету
• Попробуйте перезапустить роутер
• Проверьте настройки брандмауэра
• Попробуйте использовать VPN"""
        
        elif any(keyword in error_lower for keyword in ['disk', 'space', 'no space', 'full']):
            return """• Освободите место на диске
• Удалите ненужные файлы
• Выберите другую папку для сохранения
• Очистите корзину"""
        
        elif any(keyword in error_lower for keyword in ['permission', 'access denied', 'denied']):
            return """• Запустите программу от имени администратора
• Проверьте права доступа к папке
• Выберите другую папку для сохранения
• Закройте другие программы, использующие файл"""
        
        elif any(keyword in error_lower for keyword in ['format', 'codec', 'unsupported']):
            return """• Попробуйте другое разрешение видео
• Обновите yt-dlp: pip install --upgrade yt-dlp
• Проверьте, поддерживается ли формат вашей системой"""
        
        elif any(keyword in error_lower for keyword in ['url', 'video', 'not found', 'private']):
            return """• Проверьте правильность URL
• Убедитесь, что видео не приватное
• Попробуйте другой URL
• Проверьте, доступно ли видео в вашем регионе"""
        
        else:
            return f"• Попробуйте перезапустить программу\n• Обновите yt-dlp: pip install --upgrade yt-dlp\n• Проверьте логи для подробной информации\n• Обратитесь за помощью с текстом ошибки"
            
    def delete_temp_file(self, temp_file_path):
        """Удалить временный файл"""
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                self.log_message("🗑️ Временный файл удален")
            self.current_temp_file = None
            self.update_button_states("idle")
        except Exception as e:
            self.log_message(f"❌ Ошибка при удалении временного файла: {e}")
            
    def download_audio_separately(self, url, output_path):
        """Скачать только аудио"""
        try:
            base_no_ext = os.path.splitext(output_path)[0]
            ydl_outtmpl = base_no_ext + ".%(ext)s"

            if self.has_ffmpeg():
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': ydl_outtmpl,
                    'quiet': True,
                    'no_warnings': True,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'aac',
                        'preferredquality': '192',
                    }],
                    **({'ffmpeg_location': os.path.dirname(self.ffmpeg_path)} if self.ffmpeg_path else {}),
                }
            else:
                # Без ffmpeg нельзя гарантировать m4a; попытаемся выбрать m4a, иначе любой bestaudio
                ydl_opts = {
                    'format': 'bestaudio[ext=m4a]/bestaudio',
                    'outtmpl': ydl_outtmpl,
                    'quiet': True,
                    'no_warnings': True,
                }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Найти итоговый файл и переименовать в ожидаемый output_path
            expected_m4a = base_no_ext + '.m4a'
            if os.path.exists(expected_m4a):
                if output_path != expected_m4a:
                    try:
                        if os.path.exists(output_path):
                            os.remove(output_path)
                    except Exception:
                        pass
                    os.replace(expected_m4a, output_path)
                return True

            # Если не вышло m4a, попробуем найти любой созданный аудио файл
            for ext in ('.mp3', '.opus', '.webm', '.aac'):
                candidate = base_no_ext + ext
                if os.path.exists(candidate):
                    # Если есть ffmpeg — перекодируем в m4a/aac как output_path
                    if self.has_ffmpeg():
                        try:
                            import subprocess
                            cmd = [(self.ffmpeg_path or 'ffmpeg'), '-y', '-i', candidate, '-c:a', 'aac', '-b:a', '192k', output_path]
                            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            try:
                                os.remove(candidate)
                            except Exception:
                                pass
                            return True
                        except Exception as e:
                            self.log_message(f"❌ Ошибка перекодирования аудио: {e}")
                            return False
                    else:
                        # Без ffmpeg вернуть как есть (хотя объединение позже потребует ffmpeg)
                        if output_path != candidate:
                            os.replace(candidate, output_path)
                        return True

            return False
        except Exception as e:
            self.log_message(f"❌ Ошибка скачивания аудио: {e}")
            return False

    def extract_audio_from_video(self, video_path, audio_path):
        """Извлечь аудио из видео файла в AAC (m4a)"""
        try:
            import subprocess
            
            cmd = [
                (self.ffmpeg_path or 'ffmpeg'), '-y', '-i', video_path,
                '-vn', '-c:a', 'aac', '-b:a', '192k',
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                return True
            else:
                self.log_message(f"❌ Ошибка ffmpeg: {result.stderr}")
                return False
                
        except FileNotFoundError:
            self.log_message("❌ FFmpeg не найден. Установите FFmpeg для извлечения аудио")
            return False
        except Exception as e:
            self.log_message(f"❌ Ошибка извлечения аудио: {e}")
            return False
            
    def merge_video_audio(self, video_path, audio_path, output_path):
        """Объединить видео и аудио"""
        try:
            import subprocess
            
            cmd = [
                (self.ffmpeg_path or 'ffmpeg'), '-y', '-i', video_path, '-i', audio_path,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                return True
            else:
                self.log_message(f"❌ Ошибка объединения: {result.stderr}")
                return False
                
        except FileNotFoundError:
            self.log_message("❌ FFmpeg не найден. Установите FFmpeg для объединения")
            return False
        except Exception as e:
            self.log_message(f"❌ Ошибка объединения: {e}")
            return False
        
    def setup_ui(self):
        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="YouTube Video Downloader", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Поле для URL
        url_label = ttk.Label(main_frame, text="URL видео:")
        url_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.url_entry = ttk.Entry(main_frame, textvariable=self.url, width=50)
        self.url_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Привязка событий клавиатуры для корректной работы с русской раскладкой
        self.url_entry.bind('<Control-v>', self.paste_url)
        self.url_entry.bind('<Control-V>', self.paste_url)
        self.url_entry.bind('<Control-c>', self.copy_text)
        self.url_entry.bind('<Control-C>', self.copy_text)
        self.url_entry.bind('<Control-x>', self.cut_text)
        self.url_entry.bind('<Control-X>', self.cut_text)
        self.url_entry.bind('<Control-a>', self.select_all)
        self.url_entry.bind('<Control-A>', self.select_all)
        self.url_entry.bind('<Button-3>', self.show_context_menu)  # Правый клик
        
        # Выбор папки
        folder_label = ttk.Label(main_frame, text="Папка для сохранения:")
        folder_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.folder_entry = ttk.Entry(main_frame, textvariable=self.download_path, width=40, state="readonly")
        self.folder_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        browse_button = ttk.Button(main_frame, text="Обзор", command=self.browse_folder)
        browse_button.grid(row=2, column=2, pady=5, padx=(10, 0))
        
        # Выбор разрешения
        format_label = ttk.Label(main_frame, text="Разрешение:")
        format_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        
        self.format_combo = ttk.Combobox(main_frame, textvariable=self.selected_format, 
                                       state="readonly", width=20)
        self.format_combo.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        get_info_button = ttk.Button(main_frame, text="Получить информацию", 
                                   command=self.get_video_info)
        get_info_button.grid(row=3, column=2, pady=5, padx=(10, 0))
        
        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        self.download_button = ttk.Button(button_frame, text="Скачать видео", 
                                        command=self.start_download, style="Accent.TButton")
        self.download_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.cancel_button = ttk.Button(button_frame, text="Прервать скачивание", 
                                      command=self.cancel_download, state="disabled")
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.resume_button = ttk.Button(button_frame, text="Возобновить скачивание", 
                                      command=self.resume_download, state="disabled")
        self.resume_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.open_folder_button = ttk.Button(button_frame, text="Открыть папку", 
                                           command=self.open_download_folder)
        self.open_folder_button.pack(side=tk.LEFT)
        
        # Прогресс бар
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Текстовое поле для логов
        log_label = ttk.Label(main_frame, text="Лог скачивания:")
        log_label.grid(row=6, column=0, sticky=tk.W, pady=(10, 5))
        
        self.log_text = tk.Text(main_frame, height=10, width=70, wrap=tk.WORD)
        self.log_text.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Скроллбар для логов
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=7, column=3, sticky=(tk.N, tk.S), pady=5)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Настройка растягивания
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Обновить состояние кнопок при запуске
        self.update_button_states("idle")
        
    def browse_folder(self):
        """Открыть диалог выбора папки"""
        folder = filedialog.askdirectory(title="Выберите папку для сохранения видео")
        if folder:
            self.download_path.set(folder)
            
    def log_message(self, message):
        """Добавить сообщение в лог"""
        try:
            if hasattr(self, 'log_text') and self.log_text:
                self.log_text.insert(tk.END, f"{message}\n")
                self.log_text.see(tk.END)
                self.root.update_idletasks()
        except Exception:
            # fail-safe: не падаем, если UI еще не готов
            pass
        
    def get_video_info(self):
        """Получить информацию о видео и доступные форматы"""
        if not self.url.get().strip():
            messagebox.showerror("Ошибка", "Пожалуйста, введите URL видео")
            return
            
        try:
            self.log_message("Получение информации о видео...")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url.get(), download=False)
                self.video_info = info
                
                title = info.get('title', 'Неизвестное название')
                duration = info.get('duration', 0)
                self.log_message(f"Название: {title}")
                self.log_message(f"Длительность: {duration // 60}:{duration % 60:02d}")
                
                # Получить доступные форматы
                formats = info.get('formats', [])
                video_formats = []
                
                for f in formats:
                    # Показываем все видео-форматы (с аудио или без), чтобы расширить список разрешений
                    if (f.get('vcodec') != 'none' and f.get('height')):
                        height = f.get('height', 0)
                        ext = f.get('ext', 'unknown')
                        format_id = f.get('format_id', 'unknown')
                        filesize = f.get('filesize', 0)
                        
                        if filesize:
                            size_mb = filesize / (1024 * 1024)
                            format_desc = f"{height}p ({ext}) - {size_mb:.1f}MB"
                        else:
                            format_desc = f"{height}p ({ext})"
                            
                        video_formats.append((format_desc, format_id))
                
                # Сортировать по разрешению (по убыванию)
                video_formats.sort(key=lambda x: int(x[0].split('p')[0]), reverse=True)
                
                if video_formats:
                    self.available_formats = video_formats
                    format_names = [f[0] for f in video_formats]
                    self.format_combo['values'] = format_names
                    self.format_combo.set(format_names[0])  # Выбрать лучшее качество по умолчанию
                    self.log_message(f"Найдено {len(format_names)} доступных форматов")
                else:
                    self.log_message("❌ Не удалось получить информацию о форматах")
                    
        except Exception as e:
            error_msg = f"Ошибка при получении информации: {str(e)}"
            self.log_message(f"❌ {error_msg}")
            messagebox.showerror("Ошибка", error_msg)
            
    def generate_file_hash(self, url, format_id, title):
        """Создать хеш для уникального имени временного файла"""
        content = f"{url}_{format_id}_{title}_{int(time.time())}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
        
    def get_unique_filename(self, title, extension, is_redownload=False):
        """Получить уникальное имя файла"""
        download_dir = Path(self.download_path.get())
        if not download_dir.exists():
            download_dir.mkdir(parents=True, exist_ok=True)
            
        base_name = title
        counter = 1
        
        if is_redownload:
            # При перескачивании добавляем _copy_
            while True:
                if counter == 1:
                    filename = f"{base_name}_copy.{extension}"
                else:
                    filename = f"{base_name}_copy_{counter}.{extension}"
                    
                file_path = download_dir / filename
                if not file_path.exists():
                    return str(file_path)
                counter += 1
        else:
            # Обычное скачивание
            while True:
                if counter == 1:
                    filename = f"{base_name}.{extension}"
                else:
                    filename = f"{base_name}_{counter}.{extension}"
                    
                file_path = download_dir / filename
                if not file_path.exists():
                    return str(file_path)
                counter += 1
                
    def check_existing_file(self, title):
        """Проверить, существует ли уже файл с таким названием"""
        download_dir = Path(self.download_path.get())
        if not download_dir.exists():
            return None
            
        # Ищем файлы с похожим названием
        for ext in ['mp4', 'webm', 'mkv', 'avi']:
            pattern = f"*{title}*.{ext}"
            existing_files = list(download_dir.glob(pattern))
            if existing_files:
                return existing_files[0]
        return None
        
    def reset_download_state(self):
        """Сбросить состояние загрузки"""
        self.errors_count = 0
        self.temp_file_size = 0
        self.current_temp_file = None
        self.download_cancelled = False
        
    def check_temp_file_progress(self, temp_path):
        """Проверить прогресс временного файла"""
        if not os.path.exists(temp_path):
            return False
            
        current_size = os.path.getsize(temp_path)
        if current_size > self.temp_file_size:
            self.temp_file_size = current_size
            self.errors_count = 0  # Сброс счетчика ошибок при прогрессе
            return True
        return False
        
    def cancel_download(self):
        """Прервать загрузку"""
        self.download_cancelled = True
        self.is_downloading = False
        self.log_message("⏹️ Загрузка прервана пользователем")
        self.update_button_states("cancelled")
        
    def resume_download(self):
        """Возобновить загрузку"""
        # проверяем также вариант с .part
        real_temp = self.resolve_existing_temp_variant(self.current_temp_file) if self.current_temp_file else None
        if real_temp and os.path.exists(real_temp):
            self.log_message("🔄 Возобновление загрузки...")
            self.is_resuming = True
            self.start_download()
        else:
            messagebox.showerror("Ошибка", "Временный файл не найден для возобновления")
            
    def update_button_states(self, state):
        """Обновить состояние кнопок"""
        if state == "downloading":
            self.download_button.config(state="disabled")
            self.cancel_button.config(state="normal")
            self.resume_button.config(state="disabled")
        elif state == "cancelled":
            self.download_button.config(state="normal")
            self.cancel_button.config(state="disabled")
            self.resume_button.config(state="normal" if self.current_temp_file else "disabled")
        elif state == "idle":
            self.download_button.config(state="normal")
            self.cancel_button.config(state="disabled")
            self.resume_button.config(state="disabled")
        elif state == "error":
            self.download_button.config(state="normal")
            self.cancel_button.config(state="disabled")
            self.resume_button.config(state="normal" if self.current_temp_file else "disabled")
        
    def progress_hook(self, d):
        """Обработчик прогресса скачивания"""
        # Корректная отмена загрузки
        if getattr(self, 'download_cancelled', False):
            raise yt_dlp.utils.DownloadError('Отменено пользователем')
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes']:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                self.log_message(f"Скачивание: {percent:.1f}%")
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                self.log_message(f"Скачивание: {percent:.1f}%")
        elif d['status'] == 'finished':
            self.log_message("Скачивание завершено!")
            
    def start_stage(self, stage_num, stage_name):
        """Начать новый этап"""
        self.current_stage = stage_num
        self.log_message(f"Этап {stage_num}/{self.total_stages}:")
        self.log_message(f"{stage_name}.")
        
    def log_stage_progress(self, progress_text):
        """Логировать прогресс текущего этапа"""
        self.log_message(progress_text)
        
    def finish_stage(self, stage_num, completion_text):
        """Завершить этап"""
        self.log_message(completion_text)
        
    def paste_url(self, event):
        """Обработчик вставки URL из буфера обмена"""
        try:
            # Получаем содержимое буфера обмена
            clipboard_content = self.root.clipboard_get()
            if clipboard_content:
                # Очищаем поле и вставляем содержимое
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, clipboard_content)
                return "break"  # Предотвращаем стандартную обработку
        except tk.TclError:
            # Буфер обмена пуст или недоступен
            pass
        return None
        
    def show_context_menu(self, event):
        """Показать контекстное меню с опциями вставки"""
        try:
            # Создаем контекстное меню
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="Вставить (Ctrl+V)", command=self.paste_from_menu)
            context_menu.add_command(label="Вырезать (Ctrl+X)", command=self.cut_text)
            context_menu.add_command(label="Копировать (Ctrl+C)", command=self.copy_text)
            context_menu.add_separator()
            context_menu.add_command(label="Выделить всё (Ctrl+A)", command=self.select_all)
            
            # Показываем меню в позиции курсора
            context_menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass
            
    def paste_from_menu(self):
        """Вставка из контекстного меню"""
        self.paste_url(None)
        
    def cut_text(self):
        """Вырезать выделенный текст"""
        try:
            if self.url_entry.selection_present():
                self.url_entry.event_generate("<<Cut>>")
        except Exception:
            pass
            
    def copy_text(self):
        """Копировать выделенный текст"""
        try:
            if self.url_entry.selection_present():
                self.url_entry.event_generate("<<Copy>>")
        except Exception:
            pass
            
    def select_all(self):
        """Выделить весь текст"""
        self.url_entry.select_range(0, tk.END)
        self.url_entry.icursor(tk.END)
            
    def download_video(self):
        """Скачать видео с улучшенной обработкой ошибок и аудио"""
        try:
            if not self.url.get().strip():
                messagebox.showerror("Ошибка", "Пожалуйста, введите URL видео")
                return
                
            if not self.download_path.get():
                messagebox.showerror("Ошибка", "Пожалуйста, выберите папку для сохранения")
                return
                
            # Сбросить состояние при новой загрузке
            if not self.is_downloading:
                self.reset_download_state()
                
            # Получить информацию о видео, если еще не получена
            if not self.video_info:
                self.log_message("Получение информации о видео...")
                ydl_opts = {'quiet': True, 'no_warnings': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    self.video_info = ydl.extract_info(self.url.get(), download=False)
            
            title = self.video_info.get('title', 'Неизвестное название')
            
            # Проверить, существует ли уже файл
            existing_file = self.check_existing_file(title)
            is_redownload = False
            if existing_file and not self.is_downloading:
                result = messagebox.askyesno(
                    "Файл уже существует", 
                    f"Файл с похожим названием уже существует:\n{existing_file.name}\n\nСкачать заново?",
                    icon='question'
                )
                if not result:
                    self.log_message("Скачивание отменено пользователем")
                    return
                else:
                    self.log_message("Пользователь выбрал скачать заново")
                    is_redownload = True
            
            # Выбрать формат
            selected_format_desc = self.selected_format.get()
            if not selected_format_desc or not self.available_formats:
                messagebox.showerror("Ошибка", "Пожалуйста, сначала получите информацию о видео")
                return
                
            # Найти format_id для выбранного формата
            format_id = None
            for desc, fid in self.available_formats:
                if desc == selected_format_desc:
                    format_id = fid
                    break
                    
            if not format_id:
                format_id = 'best'  # Fallback
                
            # Получить расширение файла из формата
            file_extension = 'mp4'  # исходное расширение выбранного формата
            for desc, fid in self.available_formats:
                if desc == selected_format_desc:
                    if '(' in desc and ')' in desc:
                        ext_part = desc.split('(')[1].split(')')[0]
                        if ext_part in ['mp4', 'webm', 'mkv', 'avi']:
                            file_extension = ext_part
                    break
            # Всегда финализируем в MP4 для максимальной совместимости
            container_ext = 'mp4'
                
            # Создать уникальное имя файла
            final_filename = self.get_unique_filename(title, container_ext, is_redownload)
            
            # Создать уникальное имя для временного файла
            temp_hash = self.generate_file_hash(self.url.get(), format_id, title)
            temp_filename = f"temp_{temp_hash}.{container_ext}"
            temp_path = os.path.join(self.download_path.get(), temp_filename)
            self.current_temp_file = temp_path
            
            self.is_downloading = True
            self.update_button_states("downloading")
            self.progress.start()
            
            # Этап 1: Скачиваем выбранный формат (как есть)
            self.start_stage(1, "Скачивание основного видео потока")
            success = self.download_with_retry(temp_path, format_id, file_extension)

            if success and not self.download_cancelled:
                # Если уже есть аудиодорожка — просто финализируем
                if self.has_audio_track(temp_path) or not self.has_ffmpeg():
                    part_path = temp_path + '.part'
                    if os.path.exists(part_path):
                        self.update_button_states("error")
                        self.show_error_dialog("Файл ещё не докачан (обнаружен .part). Попробуйте возобновить загрузку.", part_path)
                        return
                    if os.path.exists(temp_path):
                        os.rename(temp_path, final_filename)
                    self.finish_stage(1, "✅ Видео успешно скачано!")
                    self.show_success_dialog(title, final_filename)
                    self.update_button_states("idle")
                else:
                    # Этап 2: Скачивание дополнительного потока (аудио)
                    self.start_stage(2, "Скачивание дополнительного потока")
                    video_only_path = temp_path  # сохранённый выбранный формат
                    audio_path = os.path.splitext(temp_path)[0] + '.m4a'
                    audio_ok = self.download_audio_separately(self.url.get(), audio_path)
                    if not audio_ok:
                        # скачать маленькое видео со звуком и извлечь
                        small_with_audio = os.path.splitext(temp_path)[0] + '_small.mp4'
                        try:
                            with yt_dlp.YoutubeDL({'outtmpl': small_with_audio, 'format': 'worst[acodec!=none]', **({'ffmpeg_location': os.path.dirname(self.ffmpeg_path)} if self.ffmpeg_path else {})}) as ydl:
                                ydl.download([self.url.get()])
                            audio_ok = self.extract_audio_from_video(small_with_audio, audio_path)
                        finally:
                            if os.path.exists(small_with_audio):
                                try:
                                    os.remove(small_with_audio)
                                except Exception:
                                    pass
                    if not audio_ok:
                        raise Exception("Не удалось получить аудиодорожку")
                    self.finish_stage(2, "Скачивание завершено!")
                    
                    # Этап 3: Получение звуковой дорожки
                    self.start_stage(3, "Получение звуковой дорожки")
                    self.log_stage_progress("Получено: 100%")
                    self.finish_stage(3, "Звуковая дорожка получена!")
                    
                    # Этап 4: Объединение звуковой дорожки с основным видео потоком
                    self.start_stage(4, "Объединение звуковой дорожки с основным видео потоком")
                    merged_ok = self.merge_video_audio(video_only_path, audio_path, final_filename)
                    # Удаляем временные отдельные файлы
                    for f in [video_only_path, audio_path]:
                        if os.path.exists(f):
                            try:
                                os.remove(f)
                            except Exception:
                                pass
                    if not merged_ok:
                        raise Exception("Не удалось объединить видео и звук")
                    # Доп. совместимость: при наличии ffmpeg перекодируем в h264/aac
                    try:
                        if self.has_ffmpeg():
                            import subprocess as _sp
                            tmp_compat = final_filename + '.tmp.mp4'
                            cmd = [(self.ffmpeg_path or 'ffmpeg'), '-y', '-i', final_filename, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-preset', 'veryfast', '-crf', '20', '-c:a', 'aac', '-b:a', '192k', tmp_compat]
                            _sp.run(cmd, check=True, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
                            os.replace(tmp_compat, final_filename)
                    except Exception:
                        pass
                    self.finish_stage(4, "✅ Видео со звуком готово!")
                    self.show_success_dialog(title, final_filename)
                    self.update_button_states("idle")
            elif self.download_cancelled:
                self.log_message("⏹️ Скачивание прервано пользователем")
                self.update_button_states("cancelled")
            else:
                # показать диалог действий после неудачных попыток
                self.update_button_states("error")
                self.show_error_dialog("Не удалось скачать видео после нескольких попыток", self.current_temp_file)
                return
            
        except Exception as e:
            error_msg = f"Ошибка при скачивании: {str(e)}"
            self.log_message(f"❌ {error_msg}")
            self.update_button_states("error")
            self.show_error_dialog(error_msg, self.current_temp_file)
            
        finally:
            if not self.download_cancelled:
                self.is_downloading = False
                self.progress.stop()
                
    def download_with_retry(self, temp_path, format_id, file_extension):
        """Скачать выбранный видео-формат (без аудио) с повторами"""
        max_retries = 3
        attempts = 0
        
        while attempts < max_retries and not self.download_cancelled:
            try:
                # Проверить прогресс временного файла
                if os.path.exists(temp_path):
                    if not self.check_temp_file_progress(temp_path):
                        # не было прогресса — засчитываем попытку
                        attempts += 1
                        self.log_message(f"🔄 Попытка возобновления {attempts}/{max_retries}")
                        if attempts >= max_retries:
                            break
                
                # Скачиваем выбранный видео-формат (возможен и со звуком, если прогрессивный)
                if self.download_selected_video(temp_path, format_id):
                    return True
                    
            except Exception as e:
                attempts += 1
                self.log_message(f"❌ Ошибка (попытка {attempts}/{max_retries}): {e}")
                if attempts >= max_retries:
                    break
                    
                # Проверить, есть ли прогресс в файле
                if os.path.exists(temp_path):
                    if not self.check_temp_file_progress(temp_path):
                        self.log_message("🔄 Нет прогресса, повторяем...")
                    else:
                        self.log_message("📈 Есть прогресс, продолжаем...")
                        
        return False

    def download_selected_video(self, temp_video_path, format_id):
        """Скачать видео выбранного формата format_id как есть (может быть со звуком, если прогрессивный)"""
        ydl_opts = {
            'outtmpl': temp_video_path,
            'progress_hooks': [self.progress_hook],
            'format': format_id,
            'continuedl': True,
            'nopart': False,
            'concurrent_fragment_downloads': 1,
            'quiet': False,
            **({'ffmpeg_location': os.path.dirname(self.ffmpeg_path)} if self.ffmpeg_path else {}),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.url.get()])
        return True
        
    def download_with_audio_separation(self, temp_path, format_id, file_extension):
        """Скачать видео с раздельным аудио"""
        try:
            # Сначала попробуем скачать видео+аудио вместе
            ydl_opts = {
                'outtmpl': temp_path,
                'progress_hooks': [self.progress_hook],
                # Формат: если есть ffmpeg — видео+лучшее аудио; иначе пробуем прогрессивный
                'format': (f'{format_id}+bestaudio/best' if self.has_ffmpeg() else (self.find_progressive_format_by_height(None) or 'best[acodec!=none]')),
                'merge_output_format': ('mkv' if self.has_ffmpeg() else None),
                # Включаем возобновление
                'continuedl': True,
                'nopart': False,
                'concurrent_fragment_downloads': 1,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url.get()])
                
            # Проверить, есть ли аудио в файле
            if self.has_audio_track(temp_path):
                self.log_message("✅ Видео с аудио скачано успешно")
                return True
            else:
                self.log_message("⚠️ Аудио не найдено, пробуем раздельное скачивание...")
                return self.download_separate_audio_video(temp_path, format_id, file_extension)
                
        except Exception as e:
            self.log_message(f"❌ Ошибка совместного скачивания: {e}")
            return self.download_separate_audio_video(temp_path, format_id, file_extension)
            
    def download_separate_audio_video(self, temp_path, format_id, file_extension):
        """Скачать видео и аудио раздельно"""
        try:
            # Создать временные файлы
            video_temp = temp_path.replace(f'.{file_extension}', f'_video.{file_extension}')
            audio_temp = temp_path.replace(f'.{file_extension}', '_audio.m4a')
            
            # Скачать только видео
            self.log_message("📹 Скачивание видео...")
            ydl_opts = {
                'outtmpl': video_temp,
                'progress_hooks': [self.progress_hook],
                'format': format_id,
                'continuedl': True,
                'nopart': False,
                'concurrent_fragment_downloads': 1,
                **({'ffmpeg_location': os.path.dirname(self.ffmpeg_path)} if self.ffmpeg_path else {}),
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url.get()])
                
            # Попробовать скачать аудио отдельно (только если есть ffmpeg для объединения)
            self.log_message("🎵 Скачивание аудио...")
            if self.has_ffmpeg() and self.download_audio_separately(self.url.get(), audio_temp):
                # Объединить видео и аудио
                self.log_message("🔗 Объединение видео и аудио...")
                if self.merge_video_audio(video_temp, audio_temp, temp_path):
                    # Удалить временные файлы
                    for temp_file in [video_temp, audio_temp]:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    return True
            else:
                # Если не удалось скачать аудио отдельно, извлечь из самого маленького видео
                if self.has_ffmpeg():
                    self.log_message("🎵 Извлечение аудио из видео...")
                    return self.extract_and_merge_audio(video_temp, temp_path, file_extension)
                else:
                    # Без ffmpeg не сможем объединить — оставим прогрессивный или исходный video_temp как результат
                    try:
                        import shutil as _sh
                        _sh.copyfile(video_temp, temp_path)
                        return True
                    except Exception:
                        return False
                
        except Exception as e:
            self.log_message(f"❌ Ошибка раздельного скачивания: {e}")
            return False
            
    def extract_and_merge_audio(self, video_path, output_path, file_extension):
        """Извлечь аудио из видео и объединить с выбранным качеством"""
        try:
            # Скачать самое маленькое видео с аудио
            small_video = video_path.replace(f'_video.{file_extension}', '_small.mp4')
            
            ydl_opts = {
                'outtmpl': small_video,
                'format': 'worst[height<=480]',  # Самое маленькое качество
                **({'ffmpeg_location': os.path.dirname(self.ffmpeg_path)} if self.ffmpeg_path else {}),
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url.get()])
                
            # Извлечь аудио
            audio_temp = video_path.replace(f'_video.{file_extension}', '_audio.m4a')
            if self.extract_audio_from_video(small_video, audio_temp):
                # Объединить с выбранным видео
                if self.merge_video_audio(video_path, audio_temp, output_path):
                    # Удалить временные файлы
                    for temp_file in [small_video, audio_temp]:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    return True
                    
        except Exception as e:
            self.log_message(f"❌ Ошибка извлечения аудио: {e}")
            
        return False
        
    def has_audio_track(self, video_path):
        """Проверить, есть ли аудио в видео файле"""
        try:
            import subprocess as _sp
            if shutil.which('ffprobe') is not None or (self.ffprobe_path and os.path.exists(self.ffprobe_path)):
                cmd = [(self.ffprobe_path or 'ffprobe'), '-v', 'quiet', '-select_streams', 'a', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', video_path]
                result = _sp.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                return 'audio' in (result.stdout or '')
            if shutil.which('ffmpeg') is not None or (self.ffmpeg_path and os.path.exists(self.ffmpeg_path)):
                result = _sp.run([(self.ffmpeg_path or 'ffmpeg'), '-i', video_path], capture_output=True, text=True, encoding='utf-8', errors='ignore')
                probe = (result.stderr or '') + (result.stdout or '')
                return ('Audio:' in probe) or (' Stream #' in probe and 'Audio' in probe)
        except Exception:
            pass
        return False
            
    def start_download(self):
        """Запустить скачивание в отдельном потоке"""
        if not self.is_downloading:
            # Если это не резюмирование — чистим лог и сбрасываем состояние
            if not getattr(self, 'is_resuming', False):
                self.log_text.delete(1.0, tk.END)
                self.reset_download_state()
            else:
                # сбрасываем флаг резюма перед стартом
                self.is_resuming = False
            # всегда снимаем флаг отмены перед стартом
            self.download_cancelled = False
            # Запустить скачивание в отдельном потоке
            self.download_thread = threading.Thread(target=self.download_video)
            self.download_thread.daemon = True
            self.download_thread.start()

    def has_ffmpeg(self):
        """Проверить наличие ffmpeg в системе"""
        try:
            if self.ffmpeg_path and os.path.exists(self.ffmpeg_path):
                return True
            if shutil.which('ffmpeg') is not None:
                return True
            subprocess.run([(self.ffmpeg_path or 'ffmpeg'), '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def is_progressive_format(self, format_id):
        """Проверить, содержит ли формат и видео, и аудио"""
        if not self.video_info:
            return False
        for f in self.video_info.get('formats', []):
            if f.get('format_id') == format_id:
                return f.get('vcodec') != 'none' and f.get('acodec') != 'none'
        return False

    def find_progressive_format_by_height(self, height):
        """Найти прогрессивный формат с заданным или ближайшим разрешением"""
        candidates = []
        for f in self.video_info.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('height'):
                candidates.append(f)
        if not candidates:
            return None
        # выбрать по минимальной разнице высоты, затем по максимальному битрейту
        candidates.sort(key=lambda x: (abs((x.get('height') or 0) - (height or 0)), -(x.get('tbr') or 0)))
        chosen = candidates[0]
        return chosen.get('format_id')

    def resolve_existing_temp_variant(self, base_temp_path):
        """Вернуть существующий путь временного файла с учетом .part"""
        variants = [
            base_temp_path,
            base_temp_path + '.part',
        ]
        for v in variants:
            if os.path.exists(v):
                return v
        return base_temp_path

def main():
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()

if __name__ == "__main__":
    main()
