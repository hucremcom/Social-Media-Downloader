import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import scrolledtext
import queue
import re
import json
import locale
import gettext
import shutil

class YoutubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("800x700")  # Yüksekliği artırdık
        self.root.minsize(800, 700)    # Minimum yüksekliği de artırdık
        
        # İkonu ayarla - pencere başlığında görünecek ikon
        if os.path.exists("youtube_icon.ico"):
            self.root.iconbitmap("youtube_icon.ico")
        
        # Kullanıcı klasörü bulma
        user_dir = os.path.expanduser("~")
        self.default_download_dir = os.path.join(user_dir, "Downloads")
        
        # Ayarları yükle
        self.config_file = self.get_config_path()
        self.settings = self.load_settings()
        
        # Console başlangıçta None olarak tanımla
        self.console = None
        
        # Tema renklerini tanımla
        self.dark_colors = {
            "bg": "#2b2b2b",
            "fg": "#ffffff",
            "select_bg": "#404040",
            "select_fg": "#ffffff",
            "button_bg": "#404040",
            "button_fg": "#ffffff",
            "hover_bg": "#505050",  # Hover için daha açık bir renk
            "hover_fg": "#ffffff",
            "entry_bg": "#404040",
            "entry_fg": "#ffffff",
            "console_bg": "#1e1e1e",
            "console_fg": "#ffffff"
        }
        
        self.light_colors = {
            "bg": "#f0f0f0",
            "fg": "#000000",
            "select_bg": "#0078d7",
            "select_fg": "#ffffff",
            "button_bg": "#e1e1e1",
            "button_fg": "#000000",
            "hover_bg": "#d1d1d1",  # Hover için daha koyu bir renk 
            "hover_fg": "#000000",
            "entry_bg": "#ffffff",
            "entry_fg": "#000000",
            "console_bg": "#ffffff",
            "console_fg": "#000000"
        }
        
        # Tema ve dil ayarları
        self.current_theme = self.settings.get("theme", "light")
        self.current_lang = self.settings.get("language", "tr")
        
        # Dil dosyalarını bulalım
        self.available_languages = {}
        self.language_names = {}
        self.load_language_files()
        
        # Dil seçimi doğrulama - eğer ayarlanan dil yoksa varsayılan "tr" kullan
        if self.current_lang not in self.available_languages:
            self.current_lang = "tr"
            
        # "Hem MP3 hem MP4" ayarını yükle
        self.download_both_formats = tk.BooleanVar(
            value=self.settings.get("download_both", False)
        )
        
        # İndirme klasörü ayarı
        last_download_dir = self.settings.get("download_dir", self.default_download_dir)
        if not os.path.isdir(last_download_dir):
            last_download_dir = self.default_download_dir
        self.dir_var = tk.StringVar(value=last_download_dir)
        
        # Format ayarı
        self.format_var = tk.StringVar(value=self.settings.get("default_format", "mp4"))
        
        # Kalite ayarı
        self.quality_var = tk.StringVar(value="high")
        
        # İndirme işlemi değişkenleri
        self.download_thread = None
        self.downloads_queue = queue.Queue()
        self.is_downloading = False
        self.current_process = None
        
        # yt-dlp yolu - PyInstaller için düzeltme
        if getattr(sys, 'frozen', False):
            # PyInstaller ile derlenen sürüm
            bundle_dir = os.path.dirname(sys.executable)
            self.yt_dlp_path = os.path.join(bundle_dir, "appdata", "bin", "yt-dlp.exe")
        else:
            # Normal Python sürümü - Türkçe karakter sorununu önlemek için ASCII karakterli isim kullan
            bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "appdata", "bin")
            self.yt_dlp_path = os.path.join(bin_dir, "yt-dlp.exe")
        
        # Stil nesnesini başlat
        self.style = ttk.Style()
        
        # Durum ve ilerleme değişkenleri
        self.status_var = tk.StringVar(value="Hazır")
        self.progress_var = tk.DoubleVar()
        self.url_var = tk.StringVar()
        
        # Arayüzü oluştur
        self.create_ui()
        
        # Tema ve dil ayarlarını uygula
        self.setup_style()
        self.update_ui_texts()
        
        # Başlangıç kontrolü
        self.check_ytdlp()

    def get_config_path(self):
        """Yapılandırma dosyasının yolunu döndürür."""
        if getattr(sys, 'frozen', False):
            # PyInstaller ile derlenmişse exe'nin yanına
            app_dir = os.path.dirname(sys.executable)
        else:
            # Normal script ise scriptin yanına
            app_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(app_dir, "config.json")

    def load_settings(self):
        """Ayarları yapılandırma dosyasından yükler."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Eski config dosyalarında theme olmayabilir, varsayılan ekle
                    if "theme" not in loaded_settings:
                        loaded_settings["theme"] = "light"
                    return loaded_settings
            else:
                 # Varsayılan ayarları döndür ve dosyayı oluştur
                default_settings = {
                    "download_dir": self.default_download_dir,
                    "theme": "light",
                    "download_both": False,
                    "default_format": "mp4",
                    "language": "tr"
                }
                self.save_settings(default_settings) # İlk çalıştırmada dosyayı oluştur
                return default_settings
        except (json.JSONDecodeError, IOError) as e:
            self.log(f"Ayarlar yüklenirken hata oluştu: {e}")
            # Hata durumunda varsayılan ayarları döndür
            return {"download_dir": self.default_download_dir}

    def save_settings(self, settings_to_save=None):
        """Mevcut ayarları yapılandırma dosyasına kaydeder."""
        if settings_to_save is None:
             settings_to_save = {
                "download_dir": self.dir_var.get(),
                "theme": self.current_theme,
                "download_both": self.download_both_formats.get(),
                "default_format": self.format_var.get(),
                "language": self.current_lang
            }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings_to_save, f, indent=4, ensure_ascii=False)
        except IOError as e:
            self.log(f"Ayarlar kaydedilirken hata oluştu: {e}")
            messagebox.showwarning("Uyarı", f"Ayarlar kaydedilemedi:\n{e}")

    def check_ytdlp(self):
        """yt-dlp dosyasının var olduğunu kontrol et"""
        if not os.path.exists(self.yt_dlp_path):
            self.log("Uyarı: yt-dlp bulunamadı!")
            if not self.download_ytdlp():
                messagebox.showerror("Hata", 
                    "yt-dlp bulunamadı ve otomatik olarak indirilemedi.\n"
                    "İndirme özelliklerini kullanmak için lütfen yt-dlp'yi manuel olarak yükleyin:\n"
                    "1. https://github.com/yt-dlp/yt-dlp/releases adresinden indirin\n"
                    "2. İndirdiğiniz dosyayı appdata/bin klasörüne kopyalayın")
        else:
            self.log(f"{self.get_translation('ytdlp_found')} {self.yt_dlp_path}")
    
    def setup_style(self):
        """Tema ayarlarını yapılandırır."""
        colors = self.dark_colors if self.current_theme == "dark" else self.light_colors
        
        try:
            # Tema ayarı
            self.style.theme_use("clam")  # Daha iyi kontrol için
            
            # Widget stillerini yapılandır
            self.style.configure("TFrame", background=colors["bg"])
            self.style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
            
            # Butonlar için özel bir yapılandırma
            self.style.configure("TButton", 
                background=colors["button_bg"], 
                foreground=colors["button_fg"],
                focuscolor=colors["select_bg"])
            
            # Aktif buton durumu için
            self.style.map("TButton", 
                background=[('active', colors["hover_bg"]), ('pressed', colors["select_bg"])],
                foreground=[('active', colors["hover_fg"]), ('pressed', colors["select_fg"])])
            
            # RadioButton ve CheckButton için hover durumu
            self.style.configure("TRadiobutton", 
                background=colors["bg"], 
                foreground=colors["fg"])
            self.style.map("TRadiobutton",
                background=[('active', colors["hover_bg"])],
                foreground=[('active', colors["hover_fg"])])
                
            self.style.configure("TCheckbutton", 
                background=colors["bg"], 
                foreground=colors["fg"])
            self.style.map("TCheckbutton",
                background=[('active', colors["hover_bg"])],
                foreground=[('active', colors["hover_fg"])])
            
            self.style.configure("TEntry", fieldbackground=colors["entry_bg"], foreground=colors["entry_fg"])
            self.style.configure("TProgressbar", background=colors["select_bg"])
            self.style.configure("TLabelframe", background=colors["bg"], foreground=colors["fg"])
            self.style.configure("TLabelframe.Label", background=colors["bg"], foreground=colors["fg"])
            
            # Listbox ve diğer widget'lar için tema ayarları
            self.root.configure(bg=colors["bg"])
            
            # Menü renkleri
            if self.current_theme == "dark":
                self.root.option_add("*Menu.Background", colors["bg"])
                self.root.option_add("*Menu.Foreground", colors["fg"])
                self.root.option_add("*Menu.activeBackground", colors["hover_bg"]) 
                self.root.option_add("*Menu.activeForeground", colors["hover_fg"])
            else:
                self.root.option_add("*Menu.Background", colors["bg"])
                self.root.option_add("*Menu.Foreground", colors["fg"])
                self.root.option_add("*Menu.activeBackground", colors["hover_bg"])
                self.root.option_add("*Menu.activeForeground", colors["hover_fg"])
            
            # Eğer konsol varsa
            if hasattr(self, 'console') and self.console:
                self.console.configure(
                    bg=colors["console_bg"],
                    fg=colors["console_fg"],
                    insertbackground=colors["fg"]
                )
            
            # Eğer listbox varsa
            if hasattr(self, 'url_listbox') and self.url_listbox:
                self.url_listbox.configure(
                    bg=colors["entry_bg"],
                    fg=colors["entry_fg"],
                    selectbackground=colors["select_bg"],
                    selectforeground=colors["select_fg"]
                )
                
        except Exception as e:
            print(f"Tema ayarlama hatası: {str(e)}")

    def toggle_theme(self):
        """Temayı light ve dark arasında değiştirir."""
        if self.current_theme == "light":
            self.current_theme = "dark"
        else:
            self.current_theme = "light"
        
        self.settings["theme"] = self.current_theme
        self.save_settings()
        
        # Stili güncelle
        self.setup_style()
        # Frame'lerin ve root penceresinin arka planını güncelle
        # Bu, tüm widget'ların yeniden çizilmesini tetikler.
        self.update_widget_backgrounds(self.root, self.style.lookup(".", "background"))

    def update_widget_backgrounds(self, widget, bg_color):
        """Verilen widget ve tüm alt widget'larının arka planını günceller."""
        try:
            widget_class = widget.winfo_class()
            
            # Frame, LabelFrame gibi container widget'lar
            if widget_class in ['Frame', 'TFrame', 'Labelframe', 'TLabelframe']:
                for child in widget.winfo_children():
                    self.update_widget_backgrounds(child, bg_color)
            
            # Root windowun alt widget'ları için
            elif widget == self.root:
                for child in widget.winfo_children():
                    self.update_widget_backgrounds(child, bg_color)
            
        except Exception as e:
            print(f"Widget güncelleme hatası: {str(e)}")

    def add_url(self):
        url = self.url_var.get().strip()
        if url:
            if url not in [self.url_listbox.get(i) for i in range(self.url_listbox.size())]:
                self.url_listbox.insert(tk.END, url)
                self.url_var.set("")
    
    def bulk_add_urls(self):
        """Toplu URL ekleme iletişim kutusu göster"""
        bulk_window = tk.Toplevel(self.root)
        bulk_window.title("Toplu URL Ekle")
        bulk_window.geometry("500x300")
        bulk_window.transient(self.root)
        bulk_window.grab_set()
        
        ttk.Label(bulk_window, text="Her satıra bir URL ekleyin:").pack(pady=5)
        
        text_area = scrolledtext.ScrolledText(bulk_window, wrap=tk.WORD, height=10)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        def add_bulk():
            text = text_area.get("1.0", tk.END).strip()
            if text:
                urls = text.split("\n")
                count = 0
                for url in urls:
                    url = url.strip()
                    if url and url not in [self.url_listbox.get(i) for i in range(self.url_listbox.size())]:
                        self.url_listbox.insert(tk.END, url)
                        count += 1
                
                messagebox.showinfo("Bilgi", f"{count} URL başarıyla eklendi.")
                bulk_window.destroy()
        
        ttk.Button(bulk_window, text="Ekle", command=add_bulk).pack(pady=10)
    
    def add_playlist(self):
        """Playlist URL'sinden tüm videoları içe aktarma"""
        playlist_url = self.url_var.get().strip()
        if not playlist_url:
            messagebox.showinfo("Uyarı", "Lütfen önce bir playlist URL'si girin!")
            return
        
        if not os.path.exists(self.yt_dlp_path):
            messagebox.showerror("Hata", "yt-dlp bulunamadı!")
            return
        
        self.log(f"Playlist ayrıştırılıyor: {playlist_url}")
        
        try:
            # Playlist'teki video URL'lerini al
            cmd = [
                self.yt_dlp_path,
                "--flat-playlist",
                "--get-id",
                playlist_url
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            video_ids = []
            for line in process.stdout:
                video_id = line.strip()
                if video_id:
                    video_ids.append(video_id)
            
            process.wait()
            
            if process.returncode == 0:
                # URL'leri listeye ekle
                count = 0
                for video_id in video_ids:
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    if video_url not in [self.url_listbox.get(i) for i in range(self.url_listbox.size())]:
                        self.url_listbox.insert(tk.END, video_url)
                        count += 1
                
                self.log(f"Playlist'ten {count} video URL'si eklendi")
                messagebox.showinfo("Bilgi", f"Playlist'ten {count} video URL'si başarıyla eklendi.")
            else:
                self.log("Playlist ayrıştırma hatası!")
                messagebox.showerror("Hata", "Playlist ayrıştırılamadı. Geçerli bir playlist URL'si girdiğinizden emin olun.")
                
        except Exception as e:
            self.log(f"Hata: {str(e)}")
            messagebox.showerror("Hata", f"Playlist ayrıştırma hatası: {str(e)}")
    
    def delete_selected(self):
        try:
            selected_index = self.url_listbox.curselection()[0]
            self.url_listbox.delete(selected_index)
        except (IndexError, TypeError):
            messagebox.showinfo("Uyarı", "Silinecek öğe seçilmedi!")
    
    def clear_list(self):
        self.url_listbox.delete(0, tk.END)
    
    def browse_directory(self):
        """İndirme klasörünü seçer ve kaydeder."""
        current_dir = self.dir_var.get()
        if not os.path.isdir(current_dir):
            current_dir = self.default_download_dir
            
        selected_dir = filedialog.askdirectory(initialdir=current_dir)
        if selected_dir:
            self.dir_var.set(selected_dir)
            # Seçilen klasörü ayarlara kaydet
            self.settings["download_dir"] = selected_dir
            self.save_settings()
    
    def download_ytdlp(self):
        """yt-dlp dosyasını indir"""
        try:
            print("yt-dlp indiriliyor, lütfen bekleyin...")
            
            # Dizini oluştur
            if getattr(sys, 'frozen', False):
                # PyInstaller ile paketlenmiş sürüm
                bin_dir = os.path.join(os.path.dirname(sys.executable), "appdata", "bin")
            else:
                # Normal Python sürümü - Türkçe karakter sorununu önlemek için ASCII karakterli isim kullan
                bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "appdata", "bin")
            
            # Klasörün var olduğundan emin ol
            os.makedirs(bin_dir, exist_ok=True)
            
            # yt-dlp dosya yolunu güncelle
            self.yt_dlp_path = os.path.join(bin_dir, "yt-dlp.exe")
            
            # Windows için yt-dlp URL'si
            ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
            
            print(f"İndiriliyor: {ytdlp_url}")
            print(f"Kaydedilecek yer: {self.yt_dlp_path}")
            
            # Klasör yolunun doğru formatlanmış olduğundan emin ol
            bin_dir = bin_dir.replace("\\", "\\\\")
            yt_dlp_path_escaped = self.yt_dlp_path.replace("\\", "\\\\")
            
            # PowerShell ile indir - çift tırnak ve tek tırnak kullanımına dikkat et
            download_cmd = f'powershell -Command "(New-Object System.Net.WebClient).DownloadFile(\'{ytdlp_url}\', \'{yt_dlp_path_escaped}\')"'
            
            print(f"Çalıştırılan komut: {download_cmd}")
            subprocess.run(download_cmd, shell=True, check=True)
            
            # Dosyanın indirilip indirilmediğini kontrol et
            if os.path.exists(self.yt_dlp_path):
                print(f"yt-dlp başarıyla indirildi: {self.yt_dlp_path}")
                return True
            else:
                print(f"Hata: İndirme başarılı görünüyor ancak dosya bulunamadı: {self.yt_dlp_path}")
                return False
                
        except Exception as e:
            print(f"Hata: yt-dlp indirilemedi: {str(e)}")
            messagebox.showerror("Hata", f"yt-dlp indirilemedi: {str(e)}\nLütfen manuel olarak indirin.")
            return False
    
    def start_download(self):
        """İndirme işlemini başlatır."""
        if not self.url_listbox.size():
            messagebox.showwarning("Uyarı", "Lütfen en az bir URL ekleyin.")
            return
        
        if not os.path.exists(self.dir_var.get()):
            messagebox.showerror("Hata", "Geçersiz indirme klasörü!")
            return
        
        self.is_downloading = True
        self.download_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # URL'leri kuyruğa ekle
        for i in range(self.url_listbox.size()):
            url = self.url_listbox.get(i)
            self.downloads_queue.put(url)
        
        # İndirme iş parçacığını başlat
        self.download_thread = threading.Thread(target=self.download_worker)
        self.download_thread.daemon = True
        self.download_thread.start()
    
    def stop_download(self):
        """İndirme işlemini durdur"""
        if not self.is_downloading:
            return
            
        self.is_downloading = False
        
        # Mevcut işlemi sonlandır
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
        
        # Kuyruk temizle
        while not self.downloads_queue.empty():
            self.downloads_queue.get()
        
        # Arayüzü güncelle
        self.download_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set("İndirme durduruldu")
        
        self.log("İndirme kullanıcı tarafından durduruldu")
    
    def get_quality_params(self, format_choice):
        """Seçilen kaliteye göre yt-dlp parametrelerini döndür"""
        quality = self.quality_var.get()
        
        if format_choice == "mp3":
            if quality == "high":
                return ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
            elif quality == "medium":
                return ["-x", "--audio-format", "mp3", "--audio-quality", "5"]
            else:  # low
                return ["-x", "--audio-format", "mp3", "--audio-quality", "9"]
        else:  # mp4
            if quality == "high":
                return ["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"]
            elif quality == "medium":
                return ["-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best"]
            else:  # low
                return ["-f", "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best"]
    
    def on_format_change(self):
        """Format radyo butonu değiştiğinde ayarları kaydeder."""
        # Eğer "Hem MP3 hem MP4" seçili değilse, varsayılan formatı kaydet
        if not self.download_both_formats.get():
            self.settings["default_format"] = self.format_var.get()
            self.save_settings()

    def on_both_formats_toggle(self):
        """"Hem MP3 hem MP4" onay kutusu durumu değiştiğinde çağrılır."""
        self.settings["download_both"] = self.download_both_formats.get()
        self.save_settings()
        # Eğer "Hem MP3 hem MP4" seçiliyse, radyo butonlarını devre dışı bırakabiliriz
        # ya da sadece birincil format olarak kalmasını sağlayabiliriz.
        # Şimdilik radyo butonları aktif kalsın, kullanıcı tercihini belirleyebilir.
        # if self.download_both_formats.get():
        #     self.mp4_radio.config(state=tk.DISABLED) # Örnek
        #     self.mp3_radio.config(state=tk.DISABLED)
        # else:
        #     self.mp4_radio.config(state=tk.NORMAL)
        #     self.mp3_radio.config(state=tk.NORMAL)

    def _download_single_format(self, url, download_dir, format_to_download, original_url_for_log):
        """Belirli bir format için tek bir indirme işlemini gerçekleştirir."""
        try:
            self.log(f"İndiriliyor ({format_to_download.upper()}): {original_url_for_log}")
            
            cmd = [self.yt_dlp_path]
            cmd.extend(self.get_quality_params(format_to_download))
            
            # Çıktı dosya adını formatla belirginleştir (isteğe bağlı ama karışıklığı önler)
            # Örneğin: VideoAdi_mp3.mp3, VideoAdi_mp4.mp4
            # Ancak yt-dlp zaten uzantıyı doğru ayarlayacaktır. Şimdilik %(title)s.%(ext)s kullanalım.
            output_template = os.path.join(download_dir, "%(title)s.%(ext)s")
            cmd.extend(["-o", output_template])
            cmd.append(url)
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            for line in self.current_process.stdout:
                if not self.is_downloading:
                    # Eğer genel indirme durdurulduysa, bu alt işlemi de durdur.
                    if self.current_process.poll() is None: # Hala çalışıyorsa
                        self.current_process.terminate()
                        self.current_process.wait() # Sonlanmasını bekle
                    self.log(f"İndirme durduruldu ({format_to_download.upper()}): {original_url_for_log}")
                    return False # Başarısız oldu veya durduruldu
                
                self.log(line.strip()) 
                self.root.update_idletasks()
            
            self.current_process.wait()
            
            if self.current_process.returncode == 0:
                self.log(f"İndirme tamamlandı ({format_to_download.upper()}): {original_url_for_log}")
                return True
            else:
                self.log(f"İndirme hatası ({format_to_download.upper()}): {original_url_for_log}, kod: {self.current_process.returncode}")
                return False
                
        except Exception as e:
            self.log(f"Hata ({format_to_download.upper()} indirme - {original_url_for_log}): {str(e)}")
            return False

    def download_worker(self):
        """İndirme iş parçacığı."""
        while not self.downloads_queue.empty() and self.is_downloading:
            url = self.downloads_queue.get()
            download_dir = self.dir_var.get()

            try:
                if self.download_both_formats.get():
                    # Hem MP3 hem MP4 indir
                    self._download_single_format(url, download_dir, "mp4", url)
                    if self.is_downloading:  # MP4 indirme başarılı olduysa MP3'ü indir
                        self._download_single_format(url, download_dir, "mp3", url)
                else:
                    # Seçili formatta indir
                    format_choice = self.format_var.get()
                    self._download_single_format(url, download_dir, format_choice, url)
                    
            except Exception as e:
                self.log(f"Hata: {str(e)}")
                
            finally:
                self.downloads_queue.task_done()
                
        self.is_downloading = False
        self.root.after(0, self._reset_ui)

    def setup_language(self):
        """Dil ayarlarını yapılandırır."""
        self.current_lang = self.settings.get("language", "tr")
        self.update_ui_texts()

    def update_ui_texts(self):
        """Arayüz metinlerini seçili dile göre günceller."""
        
        # Ana pencere başlığı
        self.root.title(self.get_translation("app_title"))
        
        try:
            # Dil menüsünü güncelle
            menubar = self.root.winfo_children()[0]
            
            # Dil menüsünün index'ini bul
            for i in range(menu_bar.index("end") + 1):
                try:
                    label = menu_bar.entrycget(i, "label")
                    # İki dilde de olabileceğinden, kontrol etmeden güncelle
                    menu_bar.entryconfig(i, label=self.get_translation("language"))
                    break
                except:
                    continue
            
        except Exception as e:
            print(f"Menü güncelleme hatası: {e}")
        
        # Etiketler ve butonları güncelle
        if hasattr(self, 'url_label'):
            self.url_label.config(text=self.get_translation("youtube_url"))
        
        if hasattr(self, 'add_button'):
            self.add_button.config(text=self.get_translation("add"))
        
        if hasattr(self, 'bulk_add_button'):
            self.bulk_add_button.config(text=self.get_translation("bulk_add"))
        
        if hasattr(self, 'delete_button'):
            self.delete_button.config(text=self.get_translation("delete_selected"))
        
        if hasattr(self, 'clear_button'):
            self.clear_button.config(text=self.get_translation("clear_list"))
        
        if hasattr(self, 'playlist_button'):
            self.playlist_button.config(text=self.get_translation("add_playlist"))
        
        if hasattr(self, 'format_label'):
            self.format_label.config(text=self.get_translation("format"))
        
        if hasattr(self, 'quality_label'):
            self.quality_label.config(text=self.get_translation("quality"))
        
        if hasattr(self, 'high_radio'):
            self.high_radio.config(text=self.get_translation("high"))
        
        if hasattr(self, 'medium_radio'):
            self.medium_radio.config(text=self.get_translation("medium"))
        
        if hasattr(self, 'low_radio'):
            self.low_radio.config(text=self.get_translation("low"))
        
        if hasattr(self, 'download_folder_label'):
            self.download_folder_label.config(text=self.get_translation("download_folder"))
        
        if hasattr(self, 'browse_button'):
            self.browse_button.config(text=self.get_translation("browse"))
        
        if hasattr(self, 'download_button'):
            self.download_button.config(text=self.get_translation("start_download"))
        
        if hasattr(self, 'stop_button'):
            self.stop_button.config(text=self.get_translation("stop_download"))
        
        if hasattr(self, 'theme_button'):
            self.theme_button.config(text=self.get_translation("change_theme"))
        
        if hasattr(self, 'both_formats_checkbox'):
            self.both_formats_checkbox.config(text=self.get_translation("both_formats"))
        
        # LabelFrame başlıklarını güncelle - doğrudan referansla
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.LabelFrame) or isinstance(widget, tk.LabelFrame):
                # LabelFrame'in etiket metnini alıp kontrol et
                frame_text = widget.cget("text")
                
                # İndirilecek Videolar
                if "İndirilecek Videolar" in frame_text or "Videos to Download" in frame_text:
                    widget.configure(text=self.get_translation("download_list"))
                # İndirme Ayarları    
                elif "İndirme Ayarları" in frame_text or "Download Settings" in frame_text:
                    widget.configure(text=self.get_translation("download_settings"))
                # Konsol Çıktısı
                elif "Konsol Çıktısı" in frame_text or "Console Output" in frame_text:
                    widget.configure(text=self.get_translation("console_output"))
                    
        # Tüm alt widget'ları dolaşarak create_ui sırasında oluşturulan LabelFrame'leri bul
        for widget in self.root.winfo_children():
            if widget.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, ttk.LabelFrame) or isinstance(child, tk.LabelFrame):
                        # LabelFrame'in etiket metnini alıp kontrol et
                        frame_text = child.cget("text")
                        
                        # İndirilecek Videolar
                        if "İndirilecek Videolar" in frame_text or "Videos to Download" in frame_text:
                            child.configure(text=self.get_translation("download_list"))
                        # İndirme Ayarları
                        elif "İndirme Ayarları" in frame_text or "Download Settings" in frame_text:
                            child.configure(text=self.get_translation("download_settings"))
                        # Konsol Çıktısı
                        elif "Konsol Çıktısı" in frame_text or "Console Output" in frame_text:
                            child.configure(text=self.get_translation("console_output"))
        
        # Durum bilgisini güncelle
        if hasattr(self, 'status_var'):
            self.status_var.set(self.get_translation("ready"))

    def log(self, message):
        """Konsola çıktı yaz"""
        # Konsol henüz oluşturulmadıysa, mesajı standart çıktıya yazdır
        if self.console is None:
            print(message)
            return
            
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, str(message) + "\n")
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)
        
        # Arayüzü güncelle
        self.root.update_idletasks()

    def change_language(self, lang_code):
        """Dil ayarını değiştirir."""
        if self.current_lang == lang_code or lang_code not in self.available_languages:
            return
            
        self.current_lang = lang_code
        self.settings["language"] = lang_code
        self.save_settings()
        
        # Arayüz metinlerini güncelle
        self.update_ui_texts()


    def show_loading_screen(self):
        """yt-dlp kontrol edilirken loading ekranı gösterir."""
        # Loading penceresi
        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.title(self.get_translation("loading"))
        self.loading_window.geometry("400x150")
        self.loading_window.resizable(False, False)
        self.loading_window.transient(self.root)
        self.loading_window.grab_set()
        
        # Ekranın ortasına yerleştir
        width = 400
        height = 150
        screen_width = self.loading_window.winfo_screenwidth()
        screen_height = self.loading_window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.loading_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Frame
        frame = ttk.Frame(self.loading_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Başlık
        label = ttk.Label(frame, text=self.get_translation("checking_ytdlp"), font=("Arial", 12))
        label.pack(pady=10)
        
        # Progress bar
        progress = ttk.Progressbar(frame, mode="indeterminate")
        progress.pack(fill=tk.X, pady=10)
        progress.start(10)
        
        # Status label
        self.loading_status = tk.StringVar(value=self.get_translation("checking_ytdlp"))
        status_label = ttk.Label(frame, textvariable=self.loading_status)
        status_label.pack(pady=5)
        
        # Loading işlemi başlat
        self.root.after(100, self.check_ytdlp_with_loading)
        
    def check_ytdlp_with_loading(self):
        """Loading ekranı ile yt-dlp kontrol et ve gerekirse indir."""
        # yt-dlp'nin olup olmadığına bak
        if os.path.exists(self.yt_dlp_path):
            self.loading_status.set(self.get_translation("ytdlp_ready"))
            self.root.after(1000, self.close_loading_screen)
        else:
            # yt-dlp yoksa indirmeye başla
            self.loading_status.set(self.get_translation("ytdlp_downloading"))
            
            # Ayrı bir thread'de indir
            download_thread = threading.Thread(target=self.download_ytdlp_with_loading)
            download_thread.daemon = True
            download_thread.start()
    
    def download_ytdlp_with_loading(self):
        """Loading ekranı gösterirken yt-dlp indir."""
        success = self.download_ytdlp()
        if success:
            self.loading_status.set(self.get_translation("ytdlp_ready"))
            self.root.after(1000, self.close_loading_screen)
        else:
            # İndirme başarısız olduysa yine de loading ekranını kapat
            self.root.after(3000, self.close_loading_screen)
    
    def close_loading_screen(self):
        """Loading ekranını kapat."""
        if hasattr(self, 'loading_window'):
            self.loading_window.grab_release()
            self.loading_window.destroy()

    def load_language_files(self):
        """Mevcut dil dosyalarını lang/ klasöründen yükler ve eksikleri oluşturur"""
        try:
            # Kaynak ve dağıtım dizinlerini belirle
            if getattr(sys, 'frozen', False):
                resources_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
                dist_dir = os.path.dirname(sys.executable)
            else:
                resources_dir = os.path.dirname(os.path.abspath(__file__))
                dist_dir = resources_dir

            # İkon dosyasını paket kaynağından kullanıcı dizinine kopyala
            icon_src = os.path.join(resources_dir, 'youtube_icon.ico')
            icon_dst = os.path.join(dist_dir, 'youtube_icon.ico')
            if os.path.exists(icon_src) and not os.path.exists(icon_dst):
                shutil.copy(icon_src, icon_dst)

            resources_lang_dir = os.path.join(resources_dir, 'lang')
            dist_lang_dir = os.path.join(dist_dir, 'lang')

            # Varsayılan dil dosyalarını paket kaynağından kullanıcı klasörüne kopyala
            if os.path.exists(resources_lang_dir):
                if not os.path.exists(dist_lang_dir):
                    shutil.copytree(resources_lang_dir, dist_lang_dir)
                else:
                    # Eksik dosyaları kopyala
                    for file in os.listdir(resources_lang_dir):
                        if file.endswith('.txt'):
                            src = os.path.join(resources_lang_dir, file)
                            dst = os.path.join(dist_lang_dir, file)
                            if not os.path.exists(dst):
                                shutil.copy(src, dst)
            else:
                os.makedirs(dist_lang_dir, exist_ok=True)

            # Kullanıcı dizinindeki dil dosyalarını tara ve yükle
            for lang_file in os.listdir(dist_lang_dir):
                if not lang_file.endswith('.txt'):
                    continue
                lang_code = lang_file.rsplit('.', 1)[0]
                lang_path = os.path.join(dist_lang_dir, lang_file)
                try:
                    with open(lang_path, 'r', encoding='utf-8') as f:
                        lang_name = f.readline().strip()
                        self.language_names[lang_code] = lang_name
                        translations = {}
                        for line in f:
                            line = line.strip()
                            if not line or '=' not in line:
                                continue
                            key, value = line.split('=', 1)
                            translations[key.strip()] = value.strip()
                        self.available_languages[lang_code] = translations
                except Exception as e:
                    print(f"Dil dosyası yüklenirken hata: {lang_path} - {e}")
        except Exception as e:
            print(f"Dil dosyaları yüklenirken hata oluştu: {e}")
            self._create_default_translations()
    
    def create_default_language_files(self, lang_dir):
        """Varsayılan dil dosyalarını oluşturur"""
        # Varsayılan çevirileri tanımla
        self._create_default_translations()
        # Eksik dil dosyalarını oluştur
        for lang_code, translations in self.available_languages.items():
            lang_name = self.language_names.get(lang_code, lang_code.upper())
            lang_path = os.path.join(lang_dir, f"{lang_code}.txt")
            # Mevcut dosya varsa atla
            if os.path.exists(lang_path):
                continue
            try:
                with open(lang_path, 'w', encoding='utf-8') as f:
                    f.write(f"{lang_name}\n")
                    for key, value in translations.items():
                        f.write(f"{key}={value}\n")
                print(f"Varsayılan dil dosyası oluşturuldu: {lang_path}")
            except Exception as e:
                print(f"Dil dosyası oluşturulurken hata: {lang_path} - {str(e)}")
    
    def _create_default_translations(self):
        """Varsayılan çevirileri oluşturur"""
        # Dil adları
        self.language_names = {
            "tr": "Türkçe",
            "en": "English",
            "ar": "العربية",
            "es": "Español",
            "fr": "Français",
            "zh": "中文",
            "hi": "हिंदी",
            "bn": "বাংলা",
            "pt": "Português",
            "ru": "Русский",
            "ur": "اردو",
            "id": "Bahasa Indonesia"
        }
        
        # Türkçe çeviriler
        tr_translations = {
            "app_title": "YouTube Downloader",
            "youtube_url": "YouTube URL:",
            "add": "Ekle",
            "bulk_add": "Toplu Ekle",
            "download_list": "İndirilecek Videolar",
            "delete_selected": "Seçileni Sil",
            "clear_list": "Listeyi Temizle",
            "add_playlist": "Playlist Ekle",
            "download_settings": "İndirme Ayarları",
            "format": "Format:",
            "quality": "Kalite:",
            "high": "Yüksek",
            "medium": "Orta",
            "low": "Düşük",
            "download_folder": "İndirme Klasörü:",
            "browse": "Gözat",
            "start_download": "İndirmeyi Başlat",
            "stop_download": "İndirmeyi Durdur",
            "change_theme": "Temayı Değiştir",
            "console_output": "Konsol Çıktısı",
            "ready": "Hazır",
            "both_formats": "Hem MP3 hem MP4 İndir",
            "language": "Dil",
            "turkish": "Türkçe",
            "english": "English",
            "loading": "Yükleniyor...",
            "checking_ytdlp": "yt-dlp kontrol ediliyor...",
            "ytdlp_downloading": "yt-dlp indiriliyor...",
            "ytdlp_ready": "yt-dlp hazır",
            "language_changed": "Dil değiştirildi",
            "ytdlp_found": "yt-dlp bulundu:"
        }
        
        # İngilizce çeviriler
        en_translations = {
            "app_title": "YouTube Downloader",
            "youtube_url": "YouTube URL:",
            "add": "Add",
            "bulk_add": "Bulk Add",
            "download_list": "Videos to Download",
            "delete_selected": "Delete Selected",
            "clear_list": "Clear List",
            "add_playlist": "Add Playlist",
            "download_settings": "Download Settings",
            "format": "Format:",
            "quality": "Quality:",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "download_folder": "Download Folder:",
            "browse": "Browse",
            "start_download": "Start Download",
            "stop_download": "Stop Download",
            "change_theme": "Change Theme",
            "console_output": "Console Output",
            "ready": "Ready",
            "both_formats": "Download Both MP3 and MP4",
            "language": "Language",
            "turkish": "Turkish",
            "english": "English",
            "loading": "Loading...",
            "checking_ytdlp": "Checking yt-dlp...",
            "ytdlp_downloading": "Downloading yt-dlp...",
            "ytdlp_ready": "yt-dlp ready",
            "language_changed": "Language changed",
            "ytdlp_found": "yt-dlp found:"
        }

        # Arapça çeviriler
        ar_translations = {
            "app_title": "شاه يوتيوب داونلودر",
            "youtube_url": "رابط يوتيوب:",
            "add": "إضافة",
            "bulk_add": "إضافة مجمعة",
            "download_list": "مقاطع فيديو للتنزيل",
            "delete_selected": "حذف المحدد",
            "clear_list": "مسح القائمة",
            "add_playlist": "إضافة قائمة تشغيل",
            "download_settings": "إعدادات التنزيل",
            "format": "التنسيق:",
            "quality": "الجودة:",
            "high": "عالية",
            "medium": "متوسطة",
            "low": "منخفضة",
            "download_folder": "مجلد التنزيل:",
            "browse": "تصفح",
            "start_download": "بدء التنزيل",
            "stop_download": "إيقاف التنزيل",
            "change_theme": "تغيير السمة",
            "console_output": "مخرجات وحدة التحكم",
            "ready": "جاهز",
            "both_formats": "تنزيل كل من MP3 و MP4",
            "language": "اللغة",
            "turkish": "التركية",
            "english": "الإنجليزية",
            "loading": "جار التحميل...",
            "checking_ytdlp": "التحقق من yt-dlp...",
            "ytdlp_downloading": "جار تنزيل yt-dlp...",
            "ytdlp_ready": "yt-dlp جاهز",
            "language_changed": "تم تغيير اللغة",
            "ytdlp_found": "تم العثور على yt-dlp:"
        }

        # İspanyolca çeviriler
        es_translations = {
            "app_title": "YouTube Downloader",
            "youtube_url": "URL de YouTube:",
            "add": "Añadir",
            "bulk_add": "Añadir en masa",
            "download_list": "Vídeos para descargar",
            "delete_selected": "Eliminar seleccionado",
            "clear_list": "Limpiar lista",
            "add_playlist": "Añadir lista de reproducción",
            "download_settings": "Ajustes de descarga",
            "format": "Formato:",
            "quality": "Calidad:",
            "high": "Alta",
            "medium": "Media",
            "low": "Baja",
            "download_folder": "Carpeta de descarga:",
            "browse": "Explorar",
            "start_download": "Iniciar descarga",
            "stop_download": "Detener descarga",
            "change_theme": "Cambiar tema",
            "console_output": "Salida de consola",
            "ready": "Listo",
            "both_formats": "Descargar tanto MP3 como MP4",
            "language": "Idioma",
            "turkish": "Turco",
            "english": "Inglés",
            "loading": "Cargando...",
            "checking_ytdlp": "Comprobando yt-dlp...",
            "ytdlp_downloading": "Descargando yt-dlp...",
            "ytdlp_ready": "yt-dlp listo",
            "language_changed": "Idioma cambiado",
            "ytdlp_found": "yt-dlp encontrado:"
        }

        # Fransızca çeviriler
        fr_translations = {
            "app_title": "YouTube Downloader",
            "youtube_url": "URL YouTube :",
            "add": "Ajouter",
            "bulk_add": "Ajout en masse",
            "download_list": "Vidéos à télécharger",
            "delete_selected": "Supprimer la sélection",
            "clear_list": "Effacer la liste",
            "add_playlist": "Ajouter une playlist",
            "download_settings": "Paramètres de téléchargement",
            "format": "Format :",
            "quality": "Qualité :",
            "high": "Haute",
            "medium": "Moyenne",
            "low": "Basse",
            "download_folder": "Dossier de téléchargement :",
            "browse": "Parcourir",
            "start_download": "Démarrer le téléchargement",
            "stop_download": "Arrêter le téléchargement",
            "change_theme": "Changer de thème",
            "console_output": "Sortie console",
            "ready": "Prêt",
            "both_formats": "Télécharger MP3 et MP4",
            "language": "Langue",
            "turkish": "Turc",
            "english": "Anglais",
            "loading": "Chargement...",
            "checking_ytdlp": "Vérification de yt-dlp...",
            "ytdlp_downloading": "Téléchargement de yt-dlp...",
            "ytdlp_ready": "yt-dlp prêt",
            "language_changed": "Langue modifiée",
            "ytdlp_found": "yt-dlp trouvé:"
        }

        # Diğer diller placeholder: İngilizce çevirilerini kullan
        zh_translations = en_translations.copy()
        hi_translations = en_translations.copy()
        bn_translations = en_translations.copy()
        pt_translations = en_translations.copy()
        ru_translations = en_translations.copy()
        ur_translations = en_translations.copy()
        id_translations = en_translations.copy()

        # Çevirileri dil kodlarına göre sakla
        self.available_languages = {
            "tr": tr_translations,
            "en": en_translations,
            "ar": ar_translations,
            "es": es_translations,
            "fr": fr_translations,
            "zh": zh_translations,
            "hi": hi_translations,
            "bn": bn_translations,
            "pt": pt_translations,
            "ru": ru_translations,
            "ur": ur_translations,
            "id": id_translations
        }

    def get_translation(self, key, default=""):
        """Mevcut dilde çeviriyi döndürür, yoksa varsayılanı kullanır"""
        if self.current_lang not in self.available_languages:
            # Varsayılan dile geri dön
            if "tr" in self.available_languages:
                self.current_lang = "tr"
            elif "en" in self.available_languages:
                self.current_lang = "en"
            else:
                # Mevcut diller listesi boşsa veya geçersizse
                return default
                
        translations = self.available_languages[self.current_lang]
        return translations.get(key, default)

    def create_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        # Menü Çubuğu
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Dil Menüsü
        self.language_menu = tk.Menu(menubar, tearoff=0)
        
        # Dil menüsünün başlığını ayarla
        menubar.add_cascade(label=self.get_translation("language"), menu=self.language_menu)
        
        # Dil seçeneklerini ekle - mevcut tüm dil dosyalarından
        for lang_code, lang_name in self.language_names.items():
            self.language_menu.add_command(
                label=lang_name,
                command=lambda code=lang_code: self.change_language(code)
            )

        # Ana çerçeve
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL giriş alanı
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=5)
        
        self.url_label = ttk.Label(url_frame, text=self.get_translation("youtube_url"))
        self.url_label.pack(side=tk.LEFT, padx=5)
        
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.url_entry.bind("<Return>", lambda e: self.add_url())
        
        self.add_button = ttk.Button(url_frame, text=self.get_translation("add"), command=self.add_url)
        self.add_button.pack(side=tk.RIGHT, padx=5)
        
        self.bulk_add_button = ttk.Button(url_frame, text=self.get_translation("bulk_add"), command=self.bulk_add_urls)
        self.bulk_add_button.pack(side=tk.RIGHT, padx=5)
        
        # URL listesi
        list_frame = ttk.LabelFrame(main_frame, text=self.get_translation("download_list"), padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.url_listbox = tk.Listbox(list_frame, height=10)
        self.url_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.url_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.url_listbox.config(yscrollcommand=scrollbar.set)
        
        # Liste kontrol butonları
        list_control_frame = ttk.Frame(main_frame)
        list_control_frame.pack(fill=tk.X, pady=5)
        
        self.delete_button = ttk.Button(list_control_frame, text=self.get_translation("delete_selected"), command=self.delete_selected)
        self.delete_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(list_control_frame, text=self.get_translation("clear_list"), command=self.clear_list)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        self.playlist_button = ttk.Button(list_control_frame, text=self.get_translation("add_playlist"), command=self.add_playlist)
        self.playlist_button.pack(side=tk.LEFT, padx=5)
        
        # İndirme ayarları
        settings_frame = ttk.LabelFrame(main_frame, text=self.get_translation("download_settings"), padding="5")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # Format seçimi
        format_selection_frame = ttk.Frame(settings_frame)
        format_selection_frame.pack(fill=tk.X, pady=5)

        self.format_label = ttk.Label(format_selection_frame, text=self.get_translation("format"))
        self.format_label.pack(side=tk.LEFT, padx=5)
        
        self.mp4_radio = ttk.Radiobutton(format_selection_frame, text="MP4", variable=self.format_var, value="mp4", command=self.on_format_change)
        self.mp4_radio.pack(side=tk.LEFT, padx=5)
        
        self.mp3_radio = ttk.Radiobutton(format_selection_frame, text="MP3", variable=self.format_var, value="mp3", command=self.on_format_change)
        self.mp3_radio.pack(side=tk.LEFT, padx=5)

        # "Hem MP3 hem MP4" onay kutusu
        self.both_formats_checkbox = ttk.Checkbutton(
            format_selection_frame, 
            text=self.get_translation("both_formats"), 
            variable=self.download_both_formats,
            command=self.on_both_formats_toggle
        )
        self.both_formats_checkbox.pack(side=tk.LEFT, padx=10)
        
        # Kalite seçimi
        quality_frame = ttk.Frame(settings_frame)
        quality_frame.pack(fill=tk.X, pady=5)
        
        self.quality_label = ttk.Label(quality_frame, text=self.get_translation("quality"))
        self.quality_label.pack(side=tk.LEFT, padx=5)
        
        self.high_radio = ttk.Radiobutton(quality_frame, text=self.get_translation("high"), variable=self.quality_var, value="high")
        self.high_radio.pack(side=tk.LEFT, padx=5)
        
        self.medium_radio = ttk.Radiobutton(quality_frame, text=self.get_translation("medium"), variable=self.quality_var, value="medium")
        self.medium_radio.pack(side=tk.LEFT, padx=5)
        
        self.low_radio = ttk.Radiobutton(quality_frame, text=self.get_translation("low"), variable=self.quality_var, value="low")
        self.low_radio.pack(side=tk.LEFT, padx=5)
        
        # İndirme klasörü
        dir_frame = ttk.Frame(settings_frame)
        dir_frame.pack(fill=tk.X, pady=5)
        
        self.download_folder_label = ttk.Label(dir_frame, text=self.get_translation("download_folder"))
        self.download_folder_label.pack(side=tk.LEFT, padx=5)
        
        dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var, width=50)
        dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.browse_button = ttk.Button(dir_frame, text=self.get_translation("browse"), command=self.browse_directory)
        self.browse_button.pack(side=tk.RIGHT, padx=5)
        
        # İndirme butonu ve Tema Değiştir Butonu
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=10)
        
        self.download_button = ttk.Button(controls_frame, text=self.get_translation("start_download"), command=self.start_download)
        self.download_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(controls_frame, text=self.get_translation("stop_download"), command=self.stop_download, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.theme_button = ttk.Button(controls_frame, text=self.get_translation("change_theme"), command=self.toggle_theme)
        self.theme_button.pack(side=tk.RIGHT, padx=5)
        
        # İlerleme çubuğu
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5)
        
        # Durum bilgisi
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # Çıktı konsolu
        console_frame = ttk.LabelFrame(main_frame, text=self.get_translation("console_output"), padding="5")
        console_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.console = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, height=12)
        self.console.pack(fill=tk.BOTH, expand=True)
        self.console.config(state=tk.DISABLED)

if __name__ == "__main__":
    # Global _ fonksiyonunu tanımla (gettext'in sağladığı)
    # Başlangıçta, hiçbir çeviri yüklenmemişse, sadece orijinal metni döndürür.
    _ = gettext.gettext

    root = tk.Tk()
    app = YoutubeDownloader(root)
    # Ana pencereyi gizle ve loading ekranını göster
    root.withdraw()
    app.show_loading_screen()
    # Loading ekranı kapandığında ana pencereyi göster
    def show_main_window():
        if not hasattr(app, 'loading_window') or not app.loading_window.winfo_exists():
            root.deiconify()
        else:
            root.after(100, show_main_window)
    root.after(500, show_main_window)
    root.mainloop()
