import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import threading
import time
import psutil
import os
import pyzipper
import subprocess
import io
from multiprocessing import Queue, Process, cpu_count
from PIL import Image  # Logo ve resim işlemleri için eklendi

# PDF desteği için pypdf kontrolü / importu
try:
    import pypdf
except ImportError:
    pypdf = None

# Office (Word, Excel & PowerPoint) desteği için msoffcrypto kontrolü / importu
try:
    import msoffcrypto
except ImportError:
    msoffcrypto = None

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- GLOBAL ÇALIŞTIRICI FONKSİYONLAR (Worker) ---

def worker_crack_rar(unrar_exe, archive_path, password_chunk, result_queue, stop_event):
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    for password in password_chunk:
        if stop_event.is_set(): break
        try:
            result = subprocess.run(
                [unrar_exe, "t", f"-p{password}", archive_path],
                startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3
            )
            if result.returncode == 0:
                result_queue.put(("FOUND", password))
                return
        except Exception:
            pass
        result_queue.put(("TICK", 1))
    result_queue.put(("DONE", None))

def worker_crack_7z(sevenzip_exe, archive_path, password_chunk, result_queue, stop_event):
    """7-Zip şifrelerini paralel olarak test eden çekirdek fonksiyonu."""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    for password in password_chunk:
        if stop_event.is_set(): break
        try:
            result = subprocess.run(
                [sevenzip_exe, "t", f"-p{password}", archive_path, "-y"],
                startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3
            )
            if result.returncode == 0:
                result_queue.put(("FOUND", password))
                return
        except Exception:
            pass
        result_queue.put(("TICK", 1))
    result_queue.put(("DONE", None))


class CrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NovaCrack - By KAYASLXS")
        self.geometry("850x740")
        self.resizable(False, False)

        # --- YENİ: Program Penceresi (Title Bar) Logosu ---
        self.setup_window_icon()

        self.is_running = False
        self.selected_archive = ""
        self.selected_dict = ""
        self.active_processes = []

        self.setup_ui()
        
        self.cpu_tracker_thread = threading.Thread(target=self.update_cpu_stats, daemon=True)
        self.cpu_tracker_thread.start()

    def setup_window_icon(self):
        """Pencere ikonunu (logo.ico veya logo.png) güvenli bir şekilde ayarlar."""
        if os.path.exists("logo.ico"):
            try:
                self.iconbitmap("logo.ico")
            except Exception:
                pass
        elif os.path.exists("logo.png"):
            try:
                icon_img = tk.PhotoImage(file="logo.png")
                self.iconphoto(True, icon_img)
            except Exception:
                pass

    def setup_ui(self):
        # --- 1. ÜST BÖLÜM: Logo ve Program Adı ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=15)

        # --- YENİ: Anasayfa Logo Desteği (Görsel varsa yükler, yoksa emojiyi yedek tutar) ---
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            try:
                pil_img = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(40, 40))
                self.logo_label = ctk.CTkLabel(self.header_frame, text="", image=self.logo_image, width=50, height=50)
            except Exception:
                self.logo_label = ctk.CTkLabel(self.header_frame, text="🔓", font=ctk.CTkFont(size=38), width=50, height=50)
        else:
            self.logo_label = ctk.CTkLabel(self.header_frame, text="🔓", font=ctk.CTkFont(size=38), width=50, height=50)
        
        self.logo_label.pack(side="left", padx=(0, 10))

        self.title_label = ctk.CTkLabel(self.header_frame, text="NovaCrack", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(side="left", anchor="center")

        # --- 2. DOSYA SEÇİM BÖLÜMÜ ---
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.pack(fill="x", padx=20, pady=10)

        self.file_title = ctk.CTkLabel(self.file_frame, text="Dosya ve Hedef Ayarları", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1F6AA5")
        self.file_title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")

        # Hedef Dosya Seçimi (.zip, .rar, .7z, .pdf, .xls, .xlsx, .doc, .docx, .ppt, .pptx)
        self.archive_label = ctk.CTkLabel(self.file_frame, text="Hedef Dosya / Arşiv:")
        self.archive_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        
        self.archive_entry = ctk.CTkEntry(self.file_frame, width=500, placeholder_text="Kırılacak .zip, .rar, .7z, .pdf, .xls, .xlsx, .doc, .docx, .ppt veya .pptx dosyasını seçin...")
        self.archive_entry.grid(row=1, column=1, padx=10, pady=10)
        
        self.archive_btn = ctk.CTkButton(self.file_frame, text="Gözat", width=100, command=self.select_archive_file)
        self.archive_btn.grid(row=1, column=2, padx=10, pady=10)

        # Sözlük Seçimi
        self.dict_label = ctk.CTkLabel(self.file_frame, text="Sözlük (Wordlist):")
        self.dict_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        
        self.dict_entry = ctk.CTkEntry(self.file_frame, width=500, placeholder_text="Mevcut şifrelerinizin olduğu .txt dosyasını seçin...")
        self.dict_entry.grid(row=2, column=1, padx=10, pady=10)
        
        self.dict_btn = ctk.CTkButton(self.file_frame, text="Seç", width=100, command=self.select_dict_file)
        self.dict_btn.grid(row=2, column=2, padx=10, pady=10)

        # --- 3. CANLI İSTATİSTİK PANELİ ---
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.pack(fill="x", padx=20, pady=10)

        self.stats_title = ctk.CTkLabel(self.stats_frame, text="Monitör", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1F6AA5")
        self.stats_title.grid(row=0, column=0, columnspan=2, padx=20, pady=(10, 5), sticky="w")

        self.lbl_target = ctk.CTkLabel(self.stats_frame, text="Hedef Dosya: -", font=ctk.CTkFont(size=13))
        self.lbl_target.grid(row=1, column=0, padx=20, pady=8, sticky="w")

        self.lbl_dict = ctk.CTkLabel(self.stats_frame, text="Kullanılan Sözlük: Seçilmedi", font=ctk.CTkFont(size=13))
        self.lbl_dict.grid(row=2, column=0, padx=20, pady=8, sticky="w")

        self.lbl_count = ctk.CTkLabel(self.stats_frame, text="Denenen Şifre: 0", font=ctk.CTkFont(size=13))
        self.lbl_count.grid(row=3, column=0, padx=20, pady=8, sticky="w")

        self.lbl_speed = ctk.CTkLabel(self.stats_frame, text="Hız: 0 şifre/sn", font=ctk.CTkFont(size=13))
        self.lbl_speed.grid(row=1, column=1, padx=40, pady=8, sticky="w")

        self.lbl_total_cpu = ctk.CTkLabel(self.stats_frame, text="Toplam CPU: %0", font=ctk.CTkFont(size=13))
        self.lbl_total_cpu.grid(row=2, column=1, padx=40, pady=8, sticky="w")

        self.lbl_app_cpu = ctk.CTkLabel(self.stats_frame, text="Program CPU: %0", font=ctk.CTkFont(size=13))
        self.lbl_app_cpu.grid(row=3, column=1, padx=40, pady=8, sticky="w")

        # --- 4. LOG KAYDI BÖLÜMÜ ---
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.log_title = ctk.CTkLabel(self.log_frame, text="İşlem Günlüğü (Logs)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1F6AA5")
        self.log_title.pack(anchor="w", padx=10, pady=(10, 5))

        self.log_textbox = ctk.CTkTextbox(self.log_frame, activate_scrollbars=True)
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_textbox.configure(state="disabled")
        self.log("[Sistem] Uygulama hazır. Hedef dosyayı seçip 'Başlat' butonuna basabilirsiniz.")

        # --- 5. KONTROL BUTONLARI ---
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.pack(fill="x", padx=30, pady=5)

        self.btn_stop = ctk.CTkButton(self.control_frame, text="🛑 Durdur", fg_color="#D32F2F", hover_color="#B71C1C", command=self.stop_cracking, state="disabled")
        self.btn_stop.pack(side="right", padx=10)

        self.btn_start = ctk.CTkButton(self.control_frame, text="🚀 Başlat", fg_color="#388E3C", hover_color="#1B5E20", command=self.start_cracking)
        self.btn_start.pack(side="right", padx=10)

    def log(self, message):
        current_time = time.strftime("%H:%M:%S")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{current_time}] {message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def select_archive_file(self):
        file_path = filedialog.askopenfilename(filetypes=[
            ("Desteklenen Dosyalar", "*.zip;*.rar;*.7z;*.pdf;*.xls;*.xlsx;*.doc;*.docx;*.ppt;*.pptx"),
            ("ZIP Arşivleri", "*.zip"),
            ("RAR Arşivleri", "*.rar"),
            ("7-Zip Arşivleri", "*.7z"),
            ("PDF Belgeleri", "*.pdf"),
            ("Excel Dosyaları", "*.xls;*.xlsx"),
            ("Word Dosyaları", "*.doc;*.docx"),
            ("PowerPoint Dosyaları", "*.ppt;*.pptx"),
            ("Tüm Dosyalar", "*.*")
        ])
        if file_path:
            self.selected_archive = file_path
            self.archive_entry.delete(0, "end")
            self.archive_entry.insert(0, file_path)
            self.lbl_target.configure(text=f"Hedef Dosya: {os.path.basename(file_path)}")
            self.log(f"[Dosya] Hedef seçildi: {file_path}")

    def select_dict_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Metin Dosyaları", "*.txt")])
        if file_path:
            self.selected_dict = file_path
            self.dict_entry.delete(0, "end")
            self.dict_entry.insert(0, file_path)
            self.lbl_dict.configure(text=f"Kullanılan Sözlük: {os.path.basename(file_path)}")
            self.log(f"[Sözlük] Mevcut şifre dosyası yüklendi: {file_path}")

    def update_cpu_stats(self):
        process = psutil.Process(os.getpid())
        while True:
            try:
                total_cpu = psutil.cpu_percentage(interval=0.5)
                app_cpu = process.cpu_percentage() / psutil.cpu_count()
                self.lbl_total_cpu.configure(text=f"Toplam CPU: %{total_cpu:.1f}")
                self.lbl_app_cpu.configure(text=f"Program CPU: %{app_cpu:.1f}")
            except Exception:
                pass
            time.sleep(0.5)

    def reset_buttons(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")

    def start_cracking(self):
        target = self.archive_entry.get().strip()
        dict_path = self.dict_entry.get().strip()

        if not target or not os.path.exists(target):
            self.log("[Hata] Lütfen geçerli bir hedef dosya seçin!")
            return

        if not dict_path or not os.path.exists(dict_path):
            self.log("[Hata] Lütfen geçerli bir şifre (.txt) dosyası seçin!")
            return

        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="enabled")
        
        ext = target.lower()
        if ext.endswith(".zip"):
            self.crack_thread = threading.Thread(target=self.crack_zip, args=(target, dict_path), daemon=True)
            self.crack_thread.start()
        elif ext.endswith(".pdf"):
            self.crack_thread = threading.Thread(target=self.crack_pdf, args=(target, dict_path), daemon=True)
            self.crack_thread.start()
        elif ext.endswith((".xls", ".xlsx", ".doc", ".docx", ".ppt", ".pptx")):
            self.crack_thread = threading.Thread(target=self.crack_office, args=(target, dict_path), daemon=True)
            self.crack_thread.start()
        elif ext.endswith(".rar"):
            self.crack_thread = threading.Thread(target=self.start_rar_multiprocessing, args=(target, dict_path), daemon=True)
            self.crack_thread.start()
        elif ext.endswith(".7z"):
            self.crack_thread = threading.Thread(target=self.start_7z_multiprocessing, args=(target, dict_path), daemon=True)
            self.crack_thread.start()
        else:
            self.log("[Hata] Desteklenmeyen dosya formatı!")
            self.reset_buttons()
            return

    def stop_cracking(self):
        self.is_running = False
        self.log("[Sistem] İşlem kullanıcı tarafından durduruluyor...")

    def crack_zip(self, archive_path, dict_path):
        self.log(f"[İşlem] ZIP kırma motoru başlatıldı: {os.path.basename(archive_path)}")
        try:
            zip_file = pyzipper.AESZipFile(archive_path)
            if not zip_file.namelist():
                self.log("[Hata] Seçilen ZIP dosyasının içi boş!")
                self.reset_buttons()
                zip_file.close()
                return
            first_file = zip_file.namelist()[0]
        except Exception as e:
            self.log(f"[Hata] ZIP dosyası okunamadı: {str(e)}")
            self.reset_buttons()
            return

        passwords = self.read_passwords(dict_path)
        if not passwords: return

        tested_count = 0
        start_time = time.time()
        found = False
        correct_password = ""

        for password in passwords:
            if not self.is_running: break
            tested_count += 1
            try:
                zip_file.read(first_file, pwd=password.encode('utf-8'))
                found = True
                correct_password = password
                break
            except Exception:
                pass
            
            if tested_count % 5 == 0:
                self.update_live_stats(tested_count, start_time)

        zip_file.close()
        self.finalize_crack_result(found, correct_password, tested_count, start_time)

    def crack_pdf(self, pdf_path, dict_path):
        self.log(f"[İşlem] PDF kırma motoru başlatıldı: {os.path.basename(pdf_path)}")
        
        if pypdf is None:
            self.log("[Hata] 'pypdf' kütüphanesi yüklü değil! Lütfen terminale 'pip install pypdf' yazarak kurun.")
            self.reset_buttons()
            return

        try:
            reader = pypdf.PdfReader(pdf_path)
            if not reader.is_encrypted:
                self.log("[Bilgi] Seçilen PDF dosyası şifreli değil.")
                self.reset_buttons()
                return
        except Exception as e:
            self.log(f"[Hata] PDF dosyası okunamadı: {str(e)}")
            self.reset_buttons()
            return

        passwords = self.read_passwords(dict_path)
        if not passwords: return

        tested_count = 0
        start_time = time.time()
        found = False
        correct_password = ""

        for password in passwords:
            if not self.is_running: break
            tested_count += 1
            try:
                if reader.decrypt(password) > 0:
                    found = True
                    correct_password = password
                    break
            except Exception:
                pass
            
            if tested_count % 5 == 0:
                self.update_live_stats(tested_count, start_time)

        self.finalize_crack_result(found, correct_password, tested_count, start_time)

    def crack_office(self, file_path, dict_path):
        """Office (Word, Excel, PowerPoint) Şifre Kırma Motoru"""
        self.log(f"[İşlem] Office kırma motoru başlatıldı: {os.path.basename(file_path)}")
        
        if msoffcrypto is None:
            self.log("[Hata] 'msoffcrypto-tool' kütüphanesi yüklü değil! Lütfen terminale 'pip install msoffcrypto-tool' yazarak kurun.")
            self.reset_buttons()
            return

        try:
            with open(file_path, "rb") as f:
                office_file = msoffcrypto.OfficeFile(f)
                if not office_file.is_encrypted():
                    self.log("[Bilgi] Seçilen Office dosyası şifreli değil.")
                    self.reset_buttons()
                    return
        except Exception as e:
            self.log(f"[Hata] Office dosyası okunamadı: {str(e)}")
            self.reset_buttons()
            return

        passwords = self.read_passwords(dict_path)
        if not passwords: return

        tested_count = 0
        start_time = time.time()
        found = False
        correct_password = ""

        for password in passwords:
            if not self.is_running: break
            tested_count += 1
            try:
                with open(file_path, "rb") as f:
                    office_file = msoffcrypto.OfficeFile(f)
                    office_file.load_key(password=password)
                    dummy_output = io.BytesIO()
                    office_file.decrypt(dummy_output)
                    found = True
                    correct_password = password
                    break
            except Exception:
                pass
            
            if tested_count % 5 == 0:
                self.update_live_stats(tested_count, start_time)

        self.finalize_crack_result(found, correct_password, tested_count, start_time)

    def start_rar_multiprocessing(self, archive_path, dict_path):
        unrar_exe = ""
        for winrar_path in [r"C:\Program Files\WinRAR\UnRAR.exe", r"C:\Program Files (x86)\WinRAR\UnRAR.exe"]:
            if os.path.exists(winrar_path):
                unrar_exe = winrar_path
                break
                
        if not unrar_exe:
            self.log("[Hata] Bilgisayarda WinRAR bulunamadı! Lütfen kurun.")
            self.reset_buttons()
            return

        passwords = self.read_passwords(dict_path)
        if not passwords: return

        num_cores = cpu_count()
        self.log(f"[İşlem] Paralel RAR Motoru Aktif. Kullanılan Çekirdek Sayısı: {num_cores}")

        chunks = [passwords[i::num_cores] for i in range(num_cores)]
        
        import multiprocessing
        result_queue = multiprocessing.Queue()
        stop_event = multiprocessing.Event()
        
        self.active_processes = []
        for i in range(num_cores):
            p = multiprocessing.Process(
                target=worker_crack_rar, 
                args=(unrar_exe, archive_path, chunks[i], result_queue, stop_event),
                daemon=True
            )
            self.active_processes.append(p)
            p.start()

        self.listen_queue(result_queue, stop_event, num_cores, passwords, start_time=time.time())

    def start_7z_multiprocessing(self, archive_path, dict_path):
        sevenzip_exe = ""
        for sz_path in [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"]:
            if os.path.exists(sz_path):
                sevenzip_exe = sz_path
                break
                
        if not sevenzip_exe:
            self.log("[Hata] Bilgisayarda 7-Zip programı bulunamadı! Lütfen 7-Zip'i bilgisayarınıza kurun.")
            self.reset_buttons()
            return

        passwords = self.read_passwords(dict_path)
        if not passwords: return

        num_cores = cpu_count()
        self.log(f"[İşlem] Paralel 7-Zip Motoru Aktif. Kullanılan Çekirdek Sayısı: {num_cores}")

        chunks = [passwords[i::num_cores] for i in range(num_cores)]
        
        import multiprocessing
        result_queue = multiprocessing.Queue()
        stop_event = multiprocessing.Event()
        
        self.active_processes = []
        for i in range(num_cores):
            p = multiprocessing.Process(
                target=worker_crack_7z, 
                args=(sevenzip_exe, archive_path, chunks[i], result_queue, stop_event),
                daemon=True
            )
            self.active_processes.append(p)
            p.start()

        self.listen_queue(result_queue, stop_event, num_cores, passwords, start_time=time.time())

    def listen_queue(self, result_queue, stop_event, num_cores, passwords, start_time):
        tested_count = 0
        found = False
        correct_password = ""
        active_workers = num_cores

        while active_workers > 0 and self.is_running:
            try:
                msg_type, data = result_queue.get(timeout=0.1)
                
                if msg_type == "TICK":
                    tested_count += data
                    if tested_count % 5 == 0:
                        self.update_live_stats(tested_count, start_time)
                elif msg_type == "FOUND":
                    found = True
                    correct_password = data
                    stop_event.set()
                    break
                elif msg_type == "DONE":
                    active_workers -= 1
            except Exception:
                if not self.is_running:
                    stop_event.set()
                    break

        for p in self.active_processes:
            p.terminate()
            p.join()
            
        self.finalize_crack_result(found, correct_password, tested_count, start_time)

    def read_passwords(self, dict_path):
        try:
            with open(dict_path, "r", encoding="utf-8", errors="ignore") as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.log(f"[Hata] Şifre dosyası okunamadı: {str(e)}")
            self.reset_buttons()
            return None

    def update_live_stats(self, tested_count, start_time):
        elapsed_time = time.time() - start_time
        speed = int(tested_count / max(elapsed_time, 0.001))
        self.lbl_count.configure(text=f"Denenen Şifre: {tested_count}")
        self.lbl_speed.configure(text=f"Hız: {speed} şifre/sn")

    def finalize_crack_result(self, found, correct_password, tested_count, start_time):
        elapsed_time = time.time() - start_time
        speed = int(tested_count / max(elapsed_time, 0.001))
        self.lbl_count.configure(text=f"Denenen Şifre: {tested_count}")
        self.lbl_speed.configure(text=f"Hız: {speed} şifre/sn")

        if found:
            self.log(f"[BAŞARILI] Şifre Bulundu! -> {correct_password}")
            messagebox.showinfo("Başarılı", f"Şifre Başarıyla Bulundu:\n\n{correct_password}")
        elif not self.is_running:
            self.log("[Sistem] İşlem durduruldu.")
        else:
            self.log(f"[Başarısız] Dosyadaki tüm ({tested_count}) şifreler denendi ama eşleşen bulunamadı.")

        self.reset_buttons()

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    app = CrackerApp()
    app.mainloop()