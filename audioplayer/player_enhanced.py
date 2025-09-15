import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pydub import AudioSegment
from pydub.playback import play
import pygame
import threading
import time
import numpy as np
import librosa
import soundfile as sf
import os
import tempfile

class EnhancedAudioLooperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced Audio Looper - 高质量音频播放器")
        self.audio_files = []
        self.current_audio = None
        self.current_audio_path = None
        self.play_thread = None
        self.is_playing = False
        self.temp_files = []  # 存储临时文件路径

        pygame.mixer.init()

        self.create_widgets()

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # 文件选择区
        file_frame = tk.LabelFrame(self.root, text="文件管理", padx=10, pady=5)
        file_frame.pack(fill=tk.X, padx=10, pady=5)

        self.btn_load = tk.Button(file_frame, text="加载MP3文件", command=self.load_files)
        self.btn_load.pack(side=tk.LEFT, padx=5)

        self.btn_clear = tk.Button(file_frame, text="清空列表", command=self.clear_files)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        self.listbox = tk.Listbox(file_frame, height=4)
        self.listbox.pack(fill=tk.X, pady=5)
        self.listbox.bind('<<ListboxSelect>>', self.on_file_select)

        # 播放控制区
        control_frame = tk.LabelFrame(self.root, text="播放控制", padx=10, pady=5)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # 第一行：时间控制
        time_frame = tk.Frame(control_frame)
        time_frame.pack(fill=tk.X, pady=2)

        tk.Label(time_frame, text="开始时间 (秒):").grid(row=0, column=0, sticky=tk.W)
        self.entry_start = tk.Entry(time_frame, width=8)
        self.entry_start.grid(row=0, column=1, padx=5)
        self.entry_start.insert(0, "0")

        tk.Label(time_frame, text="结束时间 (秒):").grid(row=0, column=2, sticky=tk.W)
        self.entry_end = tk.Entry(time_frame, width=8)
        self.entry_end.grid(row=0, column=3, padx=5)

        # 第二行：速度和音量控制
        param_frame = tk.Frame(control_frame)
        param_frame.pack(fill=tk.X, pady=2)

        tk.Label(param_frame, text="播放速度:").grid(row=0, column=0, sticky=tk.W)
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = tk.Scale(param_frame, from_=0.1, to=3.0, resolution=0.1,
                                   orient=tk.HORIZONTAL, variable=self.speed_var, length=150)
        self.speed_scale.grid(row=0, column=1, padx=5)

        self.speed_label = tk.Label(param_frame, text="1.0x")
        self.speed_label.grid(row=0, column=2, padx=5)
        self.speed_scale.config(command=self.update_speed_label)

        tk.Label(param_frame, text="音量:").grid(row=0, column=3, sticky=tk.W)
        self.volume_var = tk.DoubleVar(value=1.0)
        self.volume_scale = tk.Scale(param_frame, from_=0.0, to=2.0, resolution=0.1,
                                    orient=tk.HORIZONTAL, variable=self.volume_var, length=100)
        self.volume_scale.grid(row=0, column=4, padx=5)

        self.volume_label = tk.Label(param_frame, text="1.0")
        self.volume_label.grid(row=0, column=5, padx=5)
        self.volume_scale.config(command=self.update_volume_label)

        # 第三行：播放控制按钮
        button_frame = tk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)

        self.btn_play = tk.Button(button_frame, text="播放循环", command=self.play_loop,
                                 bg="#4CAF50", fg="white", width=12)
        self.btn_play.pack(side=tk.LEFT, padx=5)

        self.btn_stop = tk.Button(button_frame, text="停止", command=self.stop_audio,
                                 bg="#f44336", fg="white", width=12)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.btn_preview = tk.Button(button_frame, text="预览", command=self.preview_audio,
                                    bg="#2196F3", fg="white", width=12)
        self.btn_preview.pack(side=tk.LEFT, padx=5)

        # 播放进度
        progress_frame = tk.LabelFrame(self.root, text="播放进度", padx=10, pady=5)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                       maximum=100, length=400, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)

        self.progress_text = tk.Label(progress_frame, text="准备就绪")
        self.progress_text.pack()

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var,
                                  relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def update_speed_label(self, value):
        self.speed_label.config(text=f"{float(value):.1f}x")

    def update_volume_label(self, value):
        self.volume_label.config(text=f"{float(value):.1f}")

    def load_files(self):
        files = filedialog.askopenfilenames(
            title="选择音频文件",
            filetypes=[
                ("音频文件", "*.mp3 *.wav *.flac *.m4a *.ogg"),
                ("MP3文件", "*.mp3"),
                ("WAV文件", "*.wav"),
                ("所有文件", "*.*")
            ]
        )
        for f in files:
            if f not in self.audio_files:
                self.audio_files.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))
        self.status_var.set(f"已加载 {len(self.audio_files)} 个文件")

    def clear_files(self):
        self.audio_files.clear()
        self.listbox.delete(0, tk.END)
        self.current_audio = None
        self.current_audio_path = None
        self.status_var.set("文件列表已清空")

    def on_file_select(self, event):
        if not self.listbox.curselection():
            return
        index = self.listbox.curselection()[0]
        filepath = self.audio_files[index]
        self.current_audio_path = filepath

        try:
            self.current_audio = AudioSegment.from_file(filepath)
            duration = self.current_audio.duration_seconds

            self.entry_start.delete(0, tk.END)
            self.entry_start.insert(0, "0")
            self.entry_end.delete(0, tk.END)
            self.entry_end.insert(0, str(int(duration)))
            self.progress_var.set(0)

            self.status_var.set(f"已选择: {os.path.basename(filepath)} ({duration:.1f}秒)")
        except Exception as e:
            messagebox.showerror("错误", f"无法加载文件: {str(e)}")
            self.status_var.set("文件加载失败")

    def create_enhanced_audio_segment(self, start_time, end_time, speed, volume):
        """使用librosa创建高质量的音频片段"""
        try:
            self.status_var.set("正在处理音频...")

            # 使用librosa加载音频
            y, sr = librosa.load(self.current_audio_path, sr=None)

            # 转换为秒到采样点
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)

            # 截取音频片段
            segment = y[start_sample:end_sample]

            # 应用时间拉伸（高质量）
            if abs(speed - 1.0) > 0.01:  # 如果速度不是1.0
                self.status_var.set(f"正在应用{speed:.1f}x速度...")

                # 使用librosa的时间拉伸，保持音调
                # 对于慢速播放，使用更高质量的处理
                if speed < 1.0:
                    # 慢速播放：使用更精细的时间拉伸
                    segment = librosa.effects.time_stretch(segment, rate=speed)
                else:
                    # 快速播放：使用标准时间拉伸
                    segment = librosa.effects.time_stretch(segment, rate=speed)

            # 应用音量调整
            if abs(volume - 1.0) > 0.01:  # 如果音量不是1.0
                segment = segment * volume

            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            sf.write(temp_file.name, segment, sr)
            self.temp_files.append(temp_file.name)

            # 转换为pydub格式
            enhanced_segment = AudioSegment.from_wav(temp_file.name)

            self.status_var.set("音频处理完成")
            return enhanced_segment

        except Exception as e:
            messagebox.showerror("错误", f"音频处理失败: {str(e)}")
            self.status_var.set("音频处理失败")
            return None

    def play_loop(self):
        if self.current_audio is None:
            messagebox.showerror("错误", "请先选择一个音频文件")
            return

        try:
            start = float(self.entry_start.get())
            end = float(self.entry_end.get())
            speed = self.speed_var.get()
            volume = self.volume_var.get()
        except ValueError:
            messagebox.showerror("错误", "请输入正确的数字")
            return

        if start < 0 or end > self.current_audio.duration_seconds or start >= end:
            messagebox.showerror("错误", "起止时间无效")
            return

        self.is_playing = True
        self.btn_play.config(state=tk.DISABLED)
        self.status_var.set("正在播放...")

        # 创建高质量的音频片段
        enhanced_segment = self.create_enhanced_audio_segment(start, end, speed, volume)
        if enhanced_segment is None:
            self.is_playing = False
            self.btn_play.config(state=tk.NORMAL)
            return

        def play_loop_thread():
            try:
                while self.is_playing:
                    # 播放音频
                    play(enhanced_segment)

                    # 更新进度条
                    if not self.is_playing:
                        break

                    # 计算实际播放时长（考虑速度）
                    actual_duration = (end - start) / speed
                    for i in range(int(actual_duration * 10)):
                        if not self.is_playing:
                            break
                        progress = (i * 10) / (actual_duration * 10) * 100
                        self.progress_var.set(progress)
                        self.progress_text.config(text=f"播放中... {progress:.1f}%")
                        time.sleep(0.1)

                    self.progress_var.set(0)
                    self.progress_text.config(text="循环播放中...")

            except Exception as e:
                self.status_var.set(f"播放错误: {str(e)}")

        self.play_thread = threading.Thread(target=play_loop_thread, daemon=True)
        self.play_thread.start()

    def preview_audio(self):
        """预览音频片段（不循环）"""
        if self.current_audio is None:
            messagebox.showerror("错误", "请先选择一个音频文件")
            return

        try:
            start = float(self.entry_start.get())
            end = float(self.entry_end.get())
            speed = self.speed_var.get()
            volume = self.volume_var.get()
        except ValueError:
            messagebox.showerror("错误", "请输入正确的数字")
            return

        if start < 0 or end > self.current_audio.duration_seconds or start >= end:
            messagebox.showerror("错误", "起止时间无效")
            return

        self.status_var.set("正在预览...")

        # 创建高质量的音频片段
        enhanced_segment = self.create_enhanced_audio_segment(start, end, speed, volume)
        if enhanced_segment is None:
            return

        # 在新线程中播放预览
        def preview_thread():
            try:
                play(enhanced_segment)
                self.status_var.set("预览完成")
            except Exception as e:
                self.status_var.set(f"预览错误: {str(e)}")

        preview_thread = threading.Thread(target=preview_thread, daemon=True)
        preview_thread.start()

    def stop_audio(self):
        self.is_playing = False
        pygame.mixer.stop()
        pygame.mixer.quit()
        pygame.mixer.init()
        self.progress_var.set(0)
        self.progress_text.config(text="已停止")
        self.btn_play.config(state=tk.NORMAL)
        self.status_var.set("已停止播放")

    def cleanup(self):
        """清理资源，停止所有播放"""
        self.is_playing = False
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1.0)

        # 停止pygame
        pygame.mixer.stop()
        pygame.mixer.quit()

        # 清理临时文件
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        self.temp_files.clear()

    def on_closing(self):
        """窗口关闭时的处理"""
        self.cleanup()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("600x500")
    app = EnhancedAudioLooperApp(root)
    root.mainloop()
