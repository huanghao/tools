import tkinter as tk
from tkinter import filedialog, messagebox
import pygame
from pydub import AudioSegment
import io

class AudioLooper:
    def __init__(self, root):
        self.root = root
        self.root.title("音频循环工具")
        pygame.mixer.init()

        self.audio_files = []
        self.current_audio = None
        self.play_segment = None
        self.is_playing = False

        # 添加音频缓存字典
        self.audio_cache = {}
        self.current_cache_key = None

        self.start_ms = 0
        self.end_ms = 0
        self.speed = 1.0
        self.volume = 1.0

        self._create_widgets()
        self.update_playback()

    def _create_widgets(self):
        tk.Button(self.root, text="加载MP3", command=self.load_files).pack()
        self.listbox = tk.Listbox(self.root)
        self.listbox.pack(fill=tk.X)
        self.listbox.bind("<<ListboxSelect>>", self.select_file)

        # 控制区
        frame = tk.Frame(self.root)
        frame.pack()

        tk.Label(frame, text="Start (秒)").grid(row=0, column=0)
        self.start_var = tk.DoubleVar(value=0)
        tk.Entry(frame, textvariable=self.start_var, width=6).grid(row=0, column=1)

        tk.Label(frame, text="End (秒)").grid(row=0, column=2)
        self.end_var = tk.DoubleVar(value=0)
        tk.Entry(frame, textvariable=self.end_var, width=6).grid(row=0, column=3)

        tk.Label(frame, text="速度").grid(row=1, column=0)
        self.speed_var = tk.DoubleVar(value=1.0)
        tk.Entry(frame, textvariable=self.speed_var, width=6).grid(row=1, column=1)

        tk.Label(frame, text="音量").grid(row=1, column=2)
        self.volume_var = tk.DoubleVar(value=1.0)
        tk.Entry(frame, textvariable=self.volume_var, width=6).grid(row=1, column=3)

        tk.Button(frame, text="播放循环", command=self.start_loop).grid(row=2, column=0, columnspan=2)
        tk.Button(frame, text="停止", command=self.stop).grid(row=2, column=2, columnspan=2)

        # 进度条
        self.progress = tk.Scale(self.root, from_=0, to=100, orient=tk.HORIZONTAL, length=300)
        self.progress.pack()

    def load_files(self):
        files = filedialog.askopenfilenames(filetypes=[("MP3文件", "*.mp3")])
        for f in files:
            if f not in self.audio_files:
                self.audio_files.append(f)
                self.listbox.insert(tk.END, f.split("/")[-1])

    def select_file(self, event):
        if not self.listbox.curselection():
            return
        index = self.listbox.curselection()[0]
        path = self.audio_files[index]
        self.current_audio = AudioSegment.from_file(path)
        self.start_var.set(0)
        self.end_var.set(self.current_audio.duration_seconds)
        # 切换文件时清空缓存
        self.audio_cache.clear()
        self.current_cache_key = None

    def _get_cache_key(self):
        """生成缓存键，基于开始时间、结束时间和速度"""
        return (self.start_ms, self.end_ms, self.speed)

    def _get_cached_audio(self):
        """获取缓存的音频数据，如果不存在则生成并缓存"""
        cache_key = self._get_cache_key()

        # 如果缓存键没变，直接返回当前缓存的音频
        if cache_key == self.current_cache_key and cache_key in self.audio_cache:
            return self.audio_cache[cache_key]

        # 如果缓存键变了，需要生成新的音频
        if cache_key not in self.audio_cache:
            # 生成新的音频段
            segment = self.current_audio[self.start_ms:self.end_ms]
            segment = segment._spawn(segment.raw_data, overrides={
                "frame_rate": int(segment.frame_rate * self.speed)
            }).set_frame_rate(segment.frame_rate)
            segment = segment + (self.volume * 20 - 20)

            # 导出为wav格式并缓存
            buf = io.BytesIO()
            segment.export(buf, format="wav")
            buf.seek(0)

            # 缓存音频数据
            self.audio_cache[cache_key] = buf
            print(f"生成新的音频段并缓存: start={self.start_ms}ms, end={self.end_ms}ms, speed={self.speed}")
        else:
            print(f"使用缓存的音频段: start={self.start_ms}ms, end={self.end_ms}ms, speed={self.speed}")

        # 更新当前缓存键
        self.current_cache_key = cache_key
        return self.audio_cache[cache_key]

    def start_loop(self):
        if self.current_audio is None:
            messagebox.showerror("错误", "请先选择文件")
            return
        self.is_playing = True
        self.play_audio_segment()

    def play_audio_segment(self):
        if not self.is_playing:
            return

        self.start_ms = int(self.start_var.get() * 1000)
        self.end_ms = int(self.end_var.get() * 1000)
        self.speed = float(self.speed_var.get())
        self.volume = float(self.volume_var.get())

        if self.start_ms >= self.end_ms:
            return

        # 获取缓存的音频数据
        cached_audio = self._get_cached_audio()

        # 重新设置音量（音量变化不需要重新生成音频）
        pygame.mixer.music.load(cached_audio)
        pygame.mixer.music.set_volume(self.volume)
        pygame.mixer.music.play()

    def stop(self):
        self.is_playing = False
        pygame.mixer.music.stop()

    def update_playback(self):
        if self.is_playing and not pygame.mixer.music.get_busy():
            self.play_audio_segment()
        self.root.after(100, self.update_playback)


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioLooper(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), root.destroy()))
    root.mainloop()
