import customtkinter as ctk
import tkinter.messagebox as messagebox
import yt_dlp
import ffmpeg
import os
import shutil
import re
import glob
import threading
import sys
import os
import tkinter as tk

# --- FFMPEG SETUP ---
def get_ffmpeg_dir():
    """Find bundled or local FFmpeg directory."""
    # Check if running as PyInstaller bundle
    if getattr(sys, 'frozen', False):
        # PyInstaller onefile: files are extracted to sys._MEIPASS
        # PyInstaller onedir: files are next to the executable
        possible_paths = [
            sys._MEIPASS if hasattr(sys, '_MEIPASS') else None,  # onefile mode
            os.path.dirname(sys.executable),  # onedir mode
        ]
    else:
        # Normal Python execution
        possible_paths = [
            os.path.dirname(os.path.abspath(__file__)),
        ]
    
    for base_path in possible_paths:
        if not base_path:
            continue
            
        # Check for ffmpeg.exe directly in the path
        if os.path.exists(os.path.join(base_path, 'ffmpeg.exe')):
            return base_path
            
        # Check for ffmpeg folder structure (backward compatibility)
        glob_paths = (
            glob.glob(os.path.join(base_path, 'ffmpeg-*-essentials_build', 'ffmpeg-*-essentials_build', 'bin')) or
            glob.glob(os.path.join(base_path, 'ffmpeg-*-essentials_build', 'bin'))
        )
        if glob_paths:
            return glob_paths[0]
    
    # Fallback: check if ffmpeg is in system PATH
    return None

ffmpeg_dir = get_ffmpeg_dir()

if ffmpeg_dir:
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    ffmpeg_path = [ffmpeg_dir]
else:
    ffmpeg_path = None


# --- VALIDATION FUNCTIONS ---
def is_valid_youtube_url(url):
    youtube_regex = re.compile(
        r'^(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?.*v=|embed/|v/|.+\?v=)?([^&=%?]{11})')
    return re.match(youtube_regex, url) is not None

def validate_time(time_str):
    try:
        h, m, s = map(int, time_str.split(':'))
        if not (0 <= h and 0 <= m <= 59 and 0 <= s <= 59):
            return None
        return h * 3600 + m * 60 + s
    except (ValueError, TypeError):
        return None

def is_valid_youtube_playlist_url(url):
    playlist_regex = re.compile(r'^(https?://)?(www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)')
    return re.match(playlist_regex, url) is not None

def strip_playlist_param(url):
    """Remove playlist parameters from a YouTube video URL."""
    cleaned = re.sub(r'&list=[^&]+', '', url)
    cleaned = re.sub(r'&index=\d+', '', cleaned)
    return cleaned


# --- MAIN GUI APP ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Downloader")
        self.geometry("600x425") 
        self.resizable(False, False)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, 'app_icon.ico')
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_icon.ico')
        
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass 
        

        if not ffmpeg_path:
            messagebox.showerror("Error", "FFMPEG path not found.\nPlease make sure ffmpeg is extracted in the root directory.")
            self.destroy()
            return

        self.create_widgets()

    def create_widgets(self):
        # --- TAB VIEW ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=(10, 0), fill="both", expand=True)

        self.tabview.add("Full Download")
        self.tabview.add("Segment")
        self.tabview.add("Playlist")

        # --- TAB 1: FULL DOWNLOAD ---
        self.lbl_url_full = ctk.CTkLabel(self.tabview.tab("Full Download"), text="YouTube Video URL:", font=("Arial", 14, "bold"))
        self.lbl_url_full.pack(pady=(20, 5), anchor="w", padx=20)
        
        self.entry_url_full = ctk.CTkEntry(self.tabview.tab("Full Download"), placeholder_text="https://www.youtube.com/watch?v=...")
        self.entry_url_full.pack(pady=5, padx=20, fill="x")

        self.frame_format_full = ctk.CTkFrame(self.tabview.tab("Full Download"), fg_color="transparent")
        self.frame_format_full.pack(pady=10, fill="x")
        
        self.lbl_format_full = ctk.CTkLabel(self.frame_format_full, text="Format:", font=("Arial", 12, "bold"))
        self.lbl_format_full.pack(side="left", padx=(20, 10))
        
        self.format_var_full = ctk.StringVar(value="mp3")
        self.radio_mp3_full = ctk.CTkRadioButton(self.frame_format_full, text="Audio", variable=self.format_var_full, value="mp3")
        self.radio_mp3_full.pack(side="left", padx=10)
        self.radio_mp4_full = ctk.CTkRadioButton(self.frame_format_full, text="Video", variable=self.format_var_full, value="mp4")
        self.radio_mp4_full.pack(side="left", padx=10)

        self.btn_full = ctk.CTkButton(self.tabview.tab("Full Download"), text="Download", command=self.download_full)
        self.btn_full.pack(pady=20)

        # --- TAB 2: SEGMENT ---
        self.lbl_url_seg = ctk.CTkLabel(self.tabview.tab("Segment"), text="YouTube Video URL:", font=("Arial", 14, "bold"))
        self.lbl_url_seg.pack(pady=(10, 5), anchor="w", padx=20)
        
        self.entry_url_seg = ctk.CTkEntry(self.tabview.tab("Segment"), placeholder_text="https://www.youtube.com/watch?v=...")
        self.entry_url_seg.pack(pady=5, padx=20, fill="x")

        # --- START TIME FRAME ---
        self.frame_start = ctk.CTkFrame(self.tabview.tab("Segment"), fg_color="transparent")
        self.frame_start.pack(pady=(10, 5), fill="x")
        
        self.lbl_start = ctk.CTkLabel(self.frame_start, text="Start Time:", font=("Arial", 12, "bold"))
        self.lbl_start.pack(side="left", padx=(20, 10))
        
        self.entry_start_h = ctk.CTkEntry(self.frame_start, width=50, placeholder_text="HH")
        self.entry_start_h.pack(side="left", padx=2)
        self.lbl_start_colon1 = ctk.CTkLabel(self.frame_start, text=":")
        self.lbl_start_colon1.pack(side="left")
        self.entry_start_m = ctk.CTkEntry(self.frame_start, width=50, placeholder_text="MM")
        self.entry_start_m.pack(side="left", padx=2)
        self.lbl_start_colon2 = ctk.CTkLabel(self.frame_start, text=":")
        self.lbl_start_colon2.pack(side="left")
        self.entry_start_s = ctk.CTkEntry(self.frame_start, width=50, placeholder_text="SS")
        self.entry_start_s.pack(side="left", padx=2)

        # --- END TIME FRAME ---
        self.frame_end = ctk.CTkFrame(self.tabview.tab("Segment"), fg_color="transparent")
        self.frame_end.pack(pady=(5, 10), fill="x")
        
        self.lbl_end = ctk.CTkLabel(self.frame_end, text="End Time:  ", font=("Arial", 12, "bold"))
        self.lbl_end.pack(side="left", padx=(20, 10))
        
        self.entry_end_h = ctk.CTkEntry(self.frame_end, width=50, placeholder_text="HH")
        self.entry_end_h.pack(side="left", padx=2)
        self.lbl_end_colon1 = ctk.CTkLabel(self.frame_end, text=":")
        self.lbl_end_colon1.pack(side="left")
        self.entry_end_m = ctk.CTkEntry(self.frame_end, width=50, placeholder_text="MM")
        self.entry_end_m.pack(side="left", padx=2)
        self.lbl_end_colon2 = ctk.CTkLabel(self.frame_end, text=":")
        self.lbl_end_colon2.pack(side="left")
        self.entry_end_s = ctk.CTkEntry(self.frame_end, width=50, placeholder_text="SS")
        self.entry_end_s.pack(side="left", padx=2)

        self.frame_format_seg = ctk.CTkFrame(self.tabview.tab("Segment"), fg_color="transparent")
        self.frame_format_seg.pack(pady=10, fill="x")
        
        self.lbl_format_seg = ctk.CTkLabel(self.frame_format_seg, text="Format:", font=("Arial", 12, "bold"))
        self.lbl_format_seg.pack(side="left", padx=(20, 10))
        
        self.format_var_seg = ctk.StringVar(value="mp3")
        self.radio_mp3_seg = ctk.CTkRadioButton(self.frame_format_seg, text="Audio", variable=self.format_var_seg, value="mp3")
        self.radio_mp3_seg.pack(side="left", padx=10)
        self.radio_mp4_seg = ctk.CTkRadioButton(self.frame_format_seg, text="Video", variable=self.format_var_seg, value="mp4")
        self.radio_mp4_seg.pack(side="left", padx=10)

        self.btn_segment = ctk.CTkButton(self.tabview.tab("Segment"), text="Download Segment", command=self.download_segment)
        self.btn_segment.pack(pady=20)

        # --- TAB 3: PLAYLIST ---
        self.lbl_url_pl = ctk.CTkLabel(self.tabview.tab("Playlist"), text="YouTube Playlist URL:", font=("Arial", 14, "bold"))
        self.lbl_url_pl.pack(pady=(20, 5), anchor="w", padx=20)
        
        self.entry_url_pl = ctk.CTkEntry(self.tabview.tab("Playlist"), placeholder_text="https://www.youtube.com/playlist?list=...")
        self.entry_url_pl.pack(pady=5, padx=20, fill="x")

        self.frame_format_pl = ctk.CTkFrame(self.tabview.tab("Playlist"), fg_color="transparent")
        self.frame_format_pl.pack(pady=10, fill="x")
        
        self.lbl_format_pl = ctk.CTkLabel(self.frame_format_pl, text="Format:", font=("Arial", 12, "bold"))
        self.lbl_format_pl.pack(side="left", padx=(20, 10))
        
        self.format_var_pl = ctk.StringVar(value="mp3")
        self.radio_mp3_pl = ctk.CTkRadioButton(self.frame_format_pl, text="Audio", variable=self.format_var_pl, value="mp3")
        self.radio_mp3_pl.pack(side="left", padx=10)
        self.radio_mp4_pl = ctk.CTkRadioButton(self.frame_format_pl, text="Video", variable=self.format_var_pl, value="mp4")
        self.radio_mp4_pl.pack(side="left", padx=10)

        self.btn_playlist = ctk.CTkButton(self.tabview.tab("Playlist"), text="Download Playlist", command=self.download_playlist)
        self.btn_playlist.pack(pady=20)

        # --- GLOBAL PROGRESS BAR (Outside Tabs) ---
        self.frame_progress = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_progress.pack(pady=(10, 20), padx=20, fill="x", side="bottom")

        self.lbl_progress = ctk.CTkLabel(self.frame_progress, text="Ready", font=("Arial", 12))
        self.lbl_progress.pack(pady=(0, 5), anchor="w")

        self.progress_bar = ctk.CTkProgressBar(self.frame_progress)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

        for entry in [
            self.entry_url_full,
            self.entry_url_seg,
            self.entry_url_pl,
        ]:
            self.setup_context_menu(entry)

    # --- UI HELPERS ---
    def update_progress(self, percent, text="Downloading..."):
        self.after(0, self.progress_bar.set, percent)
        self.after(0, self.lbl_progress.configure, text=text)

    def setup_context_menu(self, widget):
        """Attach a right-click Cut/Copy/Paste/Select All menu to a CTkEntry."""
        menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white",
                       activebackground="#3b3b3b", activeforeground="white",
                       borderwidth=0, font=("Roboto", 12))
        menu.add_command(label="Cut", command=lambda: self.cut_text(widget))
        menu.add_command(label="Copy", command=lambda: self.copy_text(widget))
        menu.add_command(label="Paste", command=lambda: self.paste_text(widget))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: self.select_all(widget))

        def show_menu(event):
            widget.focus_set()
            menu.post(event.x_root, event.y_root)
            menu.grab_release()

        widget.bind("<Button-3>", show_menu)
        widget.bind("<Button-2>", show_menu)

    def cut_text(self, widget):
        try:
            entry = widget._entry if hasattr(widget, '_entry') else widget
            text = entry.selection_get()
            self.clipboard_clear()
            self.clipboard_append(text)
            entry.delete("sel.first", "sel.last")
        except tk.TclError:
            pass

    def copy_text(self, widget):
        try:
            entry = widget._entry if hasattr(widget, '_entry') else widget
            text = entry.selection_get()
            self.clipboard_clear()
            self.clipboard_append(text)
        except tk.TclError:
            pass

    def paste_text(self, widget):
        try:
            text = self.clipboard_get()
            entry = widget._entry if hasattr(widget, '_entry') else widget
            entry.insert("insert", text)
        except tk.TclError:
            pass

    def select_all(self, widget):
        widget.select_range(0, "end")
        widget.icursor("end")

    def toggle_buttons(self, state):
        mode = "normal" if state else "disabled"
        self.btn_full.configure(state=mode)
        self.btn_segment.configure(state=mode)
        self.btn_playlist.configure(state=mode)

    def generate_progress_hook(self):
        def hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                if total:
                    percent = d['downloaded_bytes'] / total
                    self.update_progress(percent, f"Downloading: {int(percent * 100)}%")
            elif d['status'] == 'finished':
                self.update_progress(1.0, "Processing...")
        return hook

    def get_ydl_opts(self, output_template, format_type, progress_hooks=None):
        """Build yt-dlp options based on format type (mp3 or mp4)."""
        opts = {
            "outtmpl": output_template,
        }
        if progress_hooks:
            opts["progress_hooks"] = progress_hooks
            
        if format_type == "mp3":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:  # mp4
            opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            opts["postprocessors"] = [{
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }]
        return opts

    # --- DOWNLOAD HANDLERS ---
    def download_full(self):
        url = self.entry_url_full.get().strip()
        if not is_valid_youtube_url(url):
            messagebox.showerror("Invalid URL", "Please enter a valid single YouTube video URL.")
            return

        self.toggle_buttons(False)
        self.update_progress(0, "Starting download...")
        format_type = self.format_var_full.get()
        threading.Thread(target=self.task_full, args=(url, format_type), daemon=True).start()

    def download_segment(self):
        url = self.entry_url_seg.get().strip()
        
        start_h = self.entry_start_h.get().strip() or "0"
        start_m = self.entry_start_m.get().strip() or "0"
        start_s = self.entry_start_s.get().strip() or "0"
        end_h = self.entry_end_h.get().strip() or "0"
        end_m = self.entry_end_m.get().strip() or "0"
        end_s = self.entry_end_s.get().strip() or "0"
        
        start = f"{start_h}:{start_m}:{start_s}"
        end = f"{end_h}:{end_m}:{end_s}"

        if not is_valid_youtube_url(url):
            messagebox.showerror("Invalid URL", "Please enter a valid single YouTube video URL.")
            return

        start_sec = validate_time(start)
        end_sec = validate_time(end)

        if start_sec is None or end_sec is None:
            messagebox.showerror("Invalid Time", "Please enter valid numbers for hours, minutes, and seconds.")
            return
        if start_sec >= end_sec:
            messagebox.showerror("Invalid Time", "Start time must be less than end time.")
            return

        self.toggle_buttons(False)
        self.update_progress(0, "Starting segment download...")
        format_type = self.format_var_seg.get()
        threading.Thread(target=self.task_segment, args=(url, start, end, format_type), daemon=True).start()

    def download_playlist(self):
        url = self.entry_url_pl.get().strip()
        if not is_valid_youtube_playlist_url(url):
            messagebox.showerror("Invalid URL", "Please enter a valid YouTube Playlist URL.")
            return

        self.toggle_buttons(False)
        self.update_progress(0, "Fetching playlist...")
        format_type = self.format_var_pl.get()
        threading.Thread(target=self.task_playlist, args=(url, format_type), daemon=True).start()

    # --- BACKGROUND THREADS ---
    def task_full(self, url, format_type):
        try:
            url = strip_playlist_param(url)
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            ext = "mp3" if format_type == "mp3" else "mp4"

            ydl_opts = self.get_ydl_opts(
                os.path.join(output_dir, f"%(title)s.{ext}"),
                format_type,
                [self.generate_progress_hook()]
            )
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                video_title = info_dict.get('title', 'untitled')
                sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-')).rstrip()
                output_filename = os.path.join(output_dir, f"{sanitized_title}.{ext}")
                downloaded_file = ydl.prepare_filename(info_dict).replace(info_dict['ext'], ext)
                
                if os.path.exists(downloaded_file) and downloaded_file != output_filename:
                    os.rename(downloaded_file, output_filename)
                
            self.after(0, lambda: self.update_progress(1.0, "Ready"))
            self.after(0, lambda: messagebox.showinfo("Success", f"Download saved to:\n{output_filename}"))
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Download Error", str(err)))
            self.after(0, lambda: self.update_progress(0, "Ready"))
        finally:
            self.after(0, self.toggle_buttons, True)

    def task_segment(self, url, start_time, end_time, format_type):
        try:
            url = strip_playlist_param(url)
            os.makedirs("temp", exist_ok=True)
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            ext = "mp3" if format_type == "mp3" else "mp4"

            ydl_opts = self.get_ydl_opts(
                "temp/%(id)s.%(ext)s",
                format_type,
                [self.generate_progress_hook()]
            )
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info_dict)
                base_file = downloaded_file.rsplit('.', 1)[0]
                media_file = f"{base_file}.{ext}"
                video_title = info_dict.get('title', 'untitled')

            self.after(0, lambda: self.update_progress(1.0, "Trimming..."))
            sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-')).rstrip()
            output_filename = os.path.join(output_dir, f"{sanitized_title}_{start_time.replace(':', '-')}_{end_time.replace(':', '-')}.{ext}")

            if format_type == "mp3":
                # Audio trim
                (
                    ffmpeg
                    .input(media_file, ss=start_time, to=end_time)
                    .output(output_filename, acodec='libmp3lame', ab='192k')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            else:
                (
                    ffmpeg
                    .input(media_file, ss=start_time, to=end_time)
                    .output(output_filename, c='copy')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )

            os.remove(media_file)
            self.after(0, lambda: self.update_progress(1.0, "Ready"))
            self.after(0, lambda: messagebox.showinfo("Success", f"Segment saved to:\n{output_filename}"))
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Download Error", str(err)))
            self.after(0, lambda: self.update_progress(0, "Ready"))
        finally:
            if os.path.exists("temp"):
                shutil.rmtree("temp", ignore_errors=True)
            self.after(0, self.toggle_buttons, True)

    def task_playlist(self, url, format_type):
        try:
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            ext = "mp3" if format_type == "mp3" else "mp4"

            ydl_opts_info = {'extract_flat': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                playlist_title = info_dict.get('title', 'untitled_playlist')
                sanitized_playlist_title = "".join(c for c in playlist_title if c.isalnum() or c in (' ', '-')).rstrip()
                playlist_output_dir = os.path.join(output_dir, sanitized_playlist_title)

            os.makedirs(playlist_output_dir, exist_ok=True)
            
            entries = [e for e in info_dict.get('entries', []) if e and e.get('id')]
            total_videos = len(entries)

            completed_videos = 0
            def playlist_hook(d):
                nonlocal completed_videos
                if d['status'] == 'finished':
                    completed_videos += 1
                    display_completed = min(completed_videos, total_videos)
                    percent = display_completed / total_videos if total_videos > 0 else 0
                    self.update_progress(percent, f"Downloaded {display_completed} of {total_videos} videos...")

            ydl_opts = self.get_ydl_opts(
                os.path.join(playlist_output_dir, f"%(title)s.{ext}"),
                format_type,
                [playlist_hook]
            )
            ydl_opts['ignoreerrors'] = True

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.after(0, lambda: self.update_progress(1.0, "Ready"))
            self.after(0, lambda: messagebox.showinfo("Success", f"Playlist downloaded to:\n{playlist_output_dir}"))
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Download Error", str(err)))
            self.after(0, lambda: self.update_progress(0, "Ready"))
        finally:
            self.after(0, self.toggle_buttons, True)

if __name__ == "__main__":
    app = App()
    app.mainloop()
    
    if os.path.exists("temp"):
        shutil.rmtree("temp", ignore_errors=True)