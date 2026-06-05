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

# --- FFMPEG SETUP ---
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

ffmpeg_path = (glob.glob(os.path.join(application_path, 'ffmpeg-*-essentials_build', 'ffmpeg-*-essentials_build', 'bin')) or
               glob.glob(os.path.join(application_path, 'ffmpeg-*-essentials_build', 'bin')))

if ffmpeg_path:
    os.environ["PATH"] += os.pathsep + ffmpeg_path[0]
else:
    pass

# --- VALIDATION FUNCTIONS ---
def is_valid_youtube_url(url):
    if 'list=' in url:
        return False
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


# --- MAIN GUI APP ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Audio Downloader")
        self.geometry("600x450") 
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        if not ffmpeg_path:
            messagebox.showerror("Error", "FFMPEG path not found.\nPlease make sure ffmpeg is extracted in the root directory.")
            self.destroy()
            return

        self.create_widgets()

    def create_widgets(self):
        # --- TAB VIEW ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=(10, 0), fill="both", expand=True)

        self.tabview.add("Full Audio")
        self.tabview.add("Segment")
        self.tabview.add("Playlist")

        # --- TAB 1: FULL AUDIO ---
        self.lbl_url_full = ctk.CTkLabel(self.tabview.tab("Full Audio"), text="YouTube Video URL:", font=("Arial", 14, "bold"))
        self.lbl_url_full.pack(pady=(20, 5), anchor="w", padx=20)
        
        self.entry_url_full = ctk.CTkEntry(self.tabview.tab("Full Audio"), placeholder_text="https://www.youtube.com/watch?v=...")
        self.entry_url_full.pack(pady=5, padx=20, fill="x")

        self.btn_full = ctk.CTkButton(self.tabview.tab("Full Audio"), text="Download Full Audio", command=self.download_full)
        self.btn_full.pack(pady=30)

        # --- TAB 2: SEGMENT ---
        self.lbl_url_seg = ctk.CTkLabel(self.tabview.tab("Segment"), text="YouTube Video URL:", font=("Arial", 14, "bold"))
        self.lbl_url_seg.pack(pady=(10, 5), anchor="w", padx=20)
        
        self.entry_url_seg = ctk.CTkEntry(self.tabview.tab("Segment"), placeholder_text="https://www.youtube.com/watch?v=...")
        self.entry_url_seg.pack(pady=5, padx=20, fill="x")

        self.frame_time = ctk.CTkFrame(self.tabview.tab("Segment"), fg_color="transparent")
        self.frame_time.pack(pady=10, fill="x")

        self.lbl_start = ctk.CTkLabel(self.frame_time, text="Start (HH:MM:SS):")
        self.lbl_start.pack(side="left", padx=(20, 10))
        self.entry_start = ctk.CTkEntry(self.frame_time, width=90, placeholder_text="00:00:00")
        self.entry_start.pack(side="left", padx=5)

        self.lbl_end = ctk.CTkLabel(self.frame_time, text="End (HH:MM:SS):")
        self.lbl_end.pack(side="left", padx=(30, 10))
        self.entry_end = ctk.CTkEntry(self.frame_time, width=90, placeholder_text="00:01:00")
        self.entry_end.pack(side="left", padx=5)

        self.btn_segment = ctk.CTkButton(self.tabview.tab("Segment"), text="Download Segment", command=self.download_segment)
        self.btn_segment.pack(pady=20)

        # --- TAB 3: PLAYLIST ---
        self.lbl_url_pl = ctk.CTkLabel(self.tabview.tab("Playlist"), text="YouTube Playlist URL:", font=("Arial", 14, "bold"))
        self.lbl_url_pl.pack(pady=(20, 5), anchor="w", padx=20)
        
        self.entry_url_pl = ctk.CTkEntry(self.tabview.tab("Playlist"), placeholder_text="https://www.youtube.com/playlist?list=...")
        self.entry_url_pl.pack(pady=5, padx=20, fill="x")

        self.btn_playlist = ctk.CTkButton(self.tabview.tab("Playlist"), text="Download Playlist", command=self.download_playlist)
        self.btn_playlist.pack(pady=30)

        # --- GLOBAL PROGRESS BAR (Outside Tabs) ---
        self.frame_progress = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_progress.pack(pady=(10, 20), padx=20, fill="x", side="bottom")

        self.lbl_progress = ctk.CTkLabel(self.frame_progress, text="Ready", font=("Arial", 12))
        self.lbl_progress.pack(pady=(0, 5), anchor="w")

        self.progress_bar = ctk.CTkProgressBar(self.frame_progress)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

    # --- UI HELPERS ---
    def update_progress(self, percent, text="Downloading..."):
        self.after(0, self.progress_bar.set, percent)
        self.after(0, self.lbl_progress.configure, text=text)

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
                self.update_progress(1.0, "Processing audio...")
        return hook

    # --- DOWNLOAD HANDLERS ---
    def download_full(self):
        url = self.entry_url_full.get().strip()
        if not is_valid_youtube_url(url):
            messagebox.showerror("Invalid URL", "Please enter a valid single YouTube video URL.")
            return

        self.toggle_buttons(False)
        self.update_progress(0, "Starting download...")
        threading.Thread(target=self.task_full, args=(url,), daemon=True).start()

    def download_segment(self):
        url = self.entry_url_seg.get().strip()
        start = self.entry_start.get().strip()
        end = self.entry_end.get().strip()

        if not is_valid_youtube_url(url):
            messagebox.showerror("Invalid URL", "Please enter a valid single YouTube video URL.")
            return

        start_sec = validate_time(start)
        end_sec = validate_time(end)

        if start_sec is None or end_sec is None:
            messagebox.showerror("Invalid Time", "Please use HH:MM:SS format.")
            return
        if start_sec >= end_sec:
            messagebox.showerror("Invalid Time", "Start time must be less than end time.")
            return

        self.toggle_buttons(False)
        self.update_progress(0, "Starting segment download...")
        threading.Thread(target=self.task_segment, args=(url, start, end), daemon=True).start()

    def download_playlist(self):
        url = self.entry_url_pl.get().strip()
        if not is_valid_youtube_playlist_url(url):
            messagebox.showerror("Invalid URL", "Please enter a valid YouTube Playlist URL.")
            return

        self.toggle_buttons(False)
        self.update_progress(0, "Fetching playlist...")
        threading.Thread(target=self.task_playlist, args=(url,), daemon=True).start()

    # --- BACKGROUND THREADS ---
    def task_full(self, url):
        try:
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
                "progress_hooks": [self.generate_progress_hook()],
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                video_title = info_dict.get('title', 'untitled')
                sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-')).rstrip()
                output_filename = os.path.join(output_dir, f"{sanitized_title}.mp3")
                downloaded_file = ydl.prepare_filename(info_dict).replace(info_dict['ext'], 'mp3')
                
                if os.path.exists(downloaded_file) and downloaded_file != output_filename:
                    os.rename(downloaded_file, output_filename)
                
            self.after(0, lambda: self.update_progress(1.0, "Ready"))
            self.after(0, lambda: messagebox.showinfo("Success", f"Full audio saved to:\n{output_filename}"))
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Download Error", str(err)))
            self.after(0, lambda: self.update_progress(0, "Ready"))
        finally:
            self.after(0, self.toggle_buttons, True)

    def task_segment(self, url, start_time, end_time):
        try:
            os.makedirs("temp", exist_ok=True)
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "temp/%(id)s.%(ext)s",
                "progress_hooks": [self.generate_progress_hook()],
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                audio_file = ydl.prepare_filename(info_dict).replace(info_dict['ext'], 'mp3')
                video_title = info_dict.get('title', 'untitled')

            self.after(0, lambda: self.update_progress(1.0, "Trimming audio..."))
            sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-')).rstrip()
            output_filename = os.path.join(output_dir, f"{sanitized_title}_{start_time.replace(':', '-')}_{end_time.replace(':', '-')}.mp3")

            (
                ffmpeg
                .input(audio_file, ss=start_time, to=end_time)
                .output(output_filename)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            os.remove(audio_file)
            self.after(0, lambda: self.update_progress(1.0, "Ready"))
            self.after(0, lambda: messagebox.showinfo("Success", f"Audio segment saved to:\n{output_filename}"))
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Download Error", str(err)))
            self.after(0, lambda: self.update_progress(0, "Ready"))
        finally:
            if os.path.exists("temp"):
                shutil.rmtree("temp", ignore_errors=True)
            self.after(0, self.toggle_buttons, True)

    def task_playlist(self, url):
        try:
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)

            ydl_opts_info = {'extract_flat': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                playlist_title = info_dict.get('title', 'untitled_playlist')
                sanitized_playlist_title = "".join(c for c in playlist_title if c.isalnum() or c in (' ', '-')).rstrip()
                playlist_output_dir = os.path.join(output_dir, sanitized_playlist_title)

            os.makedirs(playlist_output_dir, exist_ok=True)
            total_videos = len(info_dict.get('entries', []))

            completed_videos = 0
            def playlist_hook(d):
                nonlocal completed_videos
                if d['status'] == 'finished':
                    completed_videos += 1
                    percent = completed_videos / total_videos
                    self.update_progress(percent, f"Downloaded {completed_videos} of {total_videos} videos...")

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(playlist_output_dir, "%(title)s.%(ext)s"),
                "progress_hooks": [playlist_hook],
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                'ignoreerrors': True,
            }
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