import customtkinter as ctk
import threading
import numpy as np
import sounddevice as sd
import wave
import json
from tkinter import filedialog

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class VoiceChangerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Voice Changer")
        self.geometry("800x600")
        self.resizable(False, False)

        # App state
        self.pitch_shift = ctk.DoubleVar(value=1.0)
        self.volume = ctk.DoubleVar(value=1.0)
        self.monitor = ctk.BooleanVar(value=True)
        self.running = False
        self.recording = False

        # Devices
        self.input_device = None
        self.output_device = None
        self.input_devices = []
        self.output_devices = []

        self.wav_file = None

        self.set_default_devices()
        self.build_ui()

    def set_default_devices(self):
        try:
            devices = sd.query_devices()
            self.input_devices = [d['name'] for d in devices if d['max_input_channels'] > 0]
            self.output_devices = [d['name'] for d in devices if d['max_output_channels'] > 0]

            self.input_device = self.input_devices[0] if self.input_devices else None
            self.output_device = self.output_devices[0] if self.output_devices else None
        except Exception as e:
            print("Device error:", e)

    def build_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")

        title = ctk.CTkLabel(self.sidebar, text="Voice Changer", font=("Arial", 20, "bold"))
        title.pack(pady=(20, 10))

        self.start_button = ctk.CTkButton(self.sidebar, text="Start", command=self.start_voice_changer)
        self.start_button.pack(pady=(20, 10), padx=10)

        self.stop_button = ctk.CTkButton(self.sidebar, text="Stop", command=self.stop_voice_changer, state="disabled")
        self.stop_button.pack(pady=10, padx=10)

        self.record_button = ctk.CTkButton(self.sidebar, text="● Record", text_color="red", command=self.start_recording)
        self.record_button.pack(pady=(30, 10), padx=10)

        self.stop_record_button = ctk.CTkButton(self.sidebar, text="■ Stop Rec", command=self.stop_recording, state="disabled")
        self.stop_record_button.pack(pady=10, padx=10)

        self.status_label = ctk.CTkLabel(self.sidebar, text="Status: Idle", font=("Arial", 12))
        self.status_label.pack(pady=(40, 10))

        self.save_profile_btn = ctk.CTkButton(self.sidebar, text="Save Profile", command=self.save_profile)
        self.save_profile_btn.pack(pady=5, padx=10)

        self.load_profile_btn = ctk.CTkButton(self.sidebar, text="Load Profile", command=self.load_profile)
        self.load_profile_btn.pack(pady=5, padx=10)

        # Main content
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # Pitch Control
        pitch_section = ctk.CTkFrame(self.main_frame)
        pitch_section.pack(fill="x", pady=(10, 20), padx=20)

        pitch_label = ctk.CTkLabel(pitch_section, text="Pitch Shift", font=("Arial", 16, "bold"))
        pitch_label.pack(anchor="w", pady=(5, 2))

        self.pitch_slider = ctk.CTkSlider(pitch_section, from_=0.5, to=2.0, variable=self.pitch_shift)
        self.pitch_slider.pack(fill="x", pady=5)

        self.effect_menu = ctk.CTkOptionMenu(pitch_section, values=["Normal", "Alien", "Robot", "Deep", "Chipmunk"],
                                             command=self.apply_preset)
        self.effect_menu.set("Normal")
        self.effect_menu.pack(pady=5)

        # Volume Control
        volume_label = ctk.CTkLabel(pitch_section, text="Volume", font=("Arial", 16, "bold"))
        volume_label.pack(anchor="w", pady=(20, 2))

        self.volume_slider = ctk.CTkSlider(pitch_section, from_=0.0, to=2.0, variable=self.volume)
        self.volume_slider.pack(fill="x", pady=5)

        # Devices Section
        device_section = ctk.CTkFrame(self.main_frame)
        device_section.pack(fill="x", pady=(0, 20), padx=20)

        device_label = ctk.CTkLabel(device_section, text="Audio Devices", font=("Arial", 16, "bold"))
        device_label.pack(anchor="w", pady=(5, 2))

        self.input_selector = ctk.CTkOptionMenu(device_section, values=self.input_devices,
                                                command=self.set_input_device)
        self.input_selector.set(self.input_device)
        self.input_selector.pack(fill="x", pady=5)

        self.output_selector = ctk.CTkOptionMenu(device_section, values=self.output_devices,
                                                 command=self.set_output_device)
        self.output_selector.set(self.output_device)
        self.output_selector.pack(fill="x", pady=5)

        self.monitor_toggle = ctk.CTkCheckBox(device_section, text="Monitor Output", variable=self.monitor)
        self.monitor_toggle.pack(pady=10)

    def set_input_device(self, device_name):
        self.input_device = device_name

    def set_output_device(self, device_name):
        self.output_device = device_name

    def apply_preset(self, preset):
        presets = {
            "Normal": 1.0,
            "Alien": 1.6,
            "Robot": 0.9,
            "Deep": 0.6,
            "Chipmunk": 1.8,
        }
        self.pitch_shift.set(presets.get(preset, 1.0))

    def start_voice_changer(self):
        if not self.running:
            self.running = True
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.status_label.configure(text="Status: Running")
            threading.Thread(target=self.audio_loop, daemon=True).start()

    def stop_voice_changer(self):
        self.running = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_label.configure(text="Status: Stopped")

    def start_recording(self):
        if not self.recording:
            self.recording = True
            self.wav_file = wave.open("recorded_voice.wav", 'wb')
            self.wav_file.setnchannels(1)
            self.wav_file.setsampwidth(2)
            self.wav_file.setframerate(44100)
            self.record_button.configure(state="disabled")
            self.stop_record_button.configure(state="normal")
            self.status_label.configure(text="Status: Recording")

    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.wav_file.close()
            self.wav_file = None
            self.record_button.configure(state="normal")
            self.stop_record_button.configure(state="disabled")
            self.status_label.configure(text="Status: Idle")

    def audio_loop(self):
        samplerate = 44100
        blocksize = 1024

        try:
            with sd.Stream(device=(self.get_device_index(self.input_device, True),
                                   self.get_device_index(self.output_device, False)),
                           channels=1,
                           dtype='float32',
                           callback=self.audio_callback,
                           samplerate=samplerate,
                           blocksize=blocksize):
                while self.running:
                    sd.sleep(100)
        except Exception as e:
            self.status_label.configure(text=f"Stream error: {e}")
            print("Audio stream error:", e)

    def audio_callback(self, indata, outdata, frames, time, status):
        if not self.running:
            outdata[:] = np.zeros_like(indata)
            return

        try:
            pitch = self.pitch_shift.get()
            vol = self.volume.get()
            audio = indata[:, 0]
            indices = np.arange(0, len(audio), pitch)
            indices = indices[indices < len(audio)].astype(int)
            shifted_audio = audio[indices]

            if len(shifted_audio) < len(audio):
                shifted_audio = np.pad(shifted_audio, (0, len(audio) - len(shifted_audio)))
            elif len(shifted_audio) > len(audio):
                shifted_audio = shifted_audio[:len(audio)]

            output_audio = shifted_audio * vol

            if self.monitor.get():
                outdata[:, 0] = output_audio
            else:
                outdata[:, 0] = np.zeros_like(audio)

            if self.recording and self.wav_file:
                data_to_write = (output_audio * 32767).astype(np.int16).tobytes()
                self.wav_file.writeframes(data_to_write)

        except Exception as e:
            print("Callback error:", e)
            outdata[:, 0] = np.zeros(frames)

    def get_device_index(self, name, is_input=True):
        for i, d in enumerate(sd.query_devices()):
            if d['name'] == name and ((is_input and d['max_input_channels'] > 0) or
                                      (not is_input and d['max_output_channels'] > 0)):
                return i
        return None

    def save_profile(self):
        profile_data = {
            "pitch": self.pitch_shift.get(),
            "volume": self.volume.get()
        }
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "w") as f:
                json.dump(profile_data, f)
            self.status_label.configure(text="Profile saved")

    def load_profile(self):
        path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "r") as f:
                profile_data = json.load(f)
                self.pitch_shift.set(profile_data.get("pitch", 1.0))
                self.volume.set(profile_data.get("volume", 1.0))
            self.status_label.configure(text="Profile loaded")


if __name__ == "__main__":
    app = VoiceChangerApp()
    app.mainloop()
