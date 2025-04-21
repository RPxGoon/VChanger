import customtkinter as ctk
import threading
import numpy as np
import sounddevice as sd
import wave
import json
import time
import os
import math
from tkinter import filedialog, Canvas, PhotoImage
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
matplotlib.use("TkAgg")

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Define colors
COLORS = {
    "primary": "#3a7ebf",
    "secondary": "#2a5a8a",
    "accent": "#ff5722",
    "background": "#1a1a1a",
    "card": "#2d2d2d",
    "text": "#ffffff",
    "text_secondary": "#aaaaaa",
    "success": "#4caf50",
    "warning": "#ff9800",
    "error": "#f44336",
    "recording": "#f44336",
}

# Create assets directory if it doesn't exist
if not os.path.exists("assets"):
    os.makedirs("assets")


class AnimatedButton(ctk.CTkButton):
    """Custom button with animation effects"""
    
    def __init__(self, *args, **kwargs):
        self.hover_color = kwargs.pop("hover_color", None)
        self.pulse = kwargs.pop("pulse", False)
        self.pulse_color = kwargs.pop("pulse_color", COLORS["accent"])
        self.pulse_speed = kwargs.pop("pulse_speed", 1.0)
        self.is_pulsing = False
        self.original_fg_color = kwargs.get("fg_color", None)
        
        super().__init__(*args, **kwargs)
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        # Store original colors
        self._original_fg_color = self._fg_color
        
    def _on_enter(self, event):
        """Handle mouse enter event"""
        if self.hover_color and self._state != "disabled":
            self.configure(fg_color=self.hover_color)
            
    def _on_leave(self, event):
        """Handle mouse leave event"""
        if self.hover_color and self._state != "disabled":
            self.configure(fg_color=self._original_fg_color)
    
    def start_pulse(self):
        """Start pulsing animation"""
        if self.pulse and not self.is_pulsing:
            self.is_pulsing = True
            self._pulse_animation()
    
    def stop_pulse(self):
        """Stop pulsing animation"""
        self.is_pulsing = False
        self.configure(fg_color=self._original_fg_color)
    
    def _pulse_animation(self):
        """Animate button pulsing"""
        if not self.is_pulsing:
            return
        
        # Toggle between original and pulse color
        current_color = self.cget("fg_color")
        if current_color == self._original_fg_color:
            self.configure(fg_color=self.pulse_color)
        else:
            self.configure(fg_color=self._original_fg_color)
        
        # Schedule next pulse
        self.after(int(500 / self.pulse_speed), self._pulse_animation)


class VUMeter(ctk.CTkFrame):
    """Audio level VU meter widget"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.configure(fg_color="transparent")
        
        # Create canvas for drawing
        self.canvas = Canvas(self, bg=COLORS["background"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Initialize level
        self.level = 0
        self.target_level = 0
        self.is_animating = False
        
        # Draw initial meter
        self._draw_meter()
    
    def _draw_meter(self):
        """Draw the VU meter on canvas"""
        self.canvas.delete("all")
        
        # Get dimensions
        width = self.canvas.winfo_width() or 200
        height = self.canvas.winfo_height() or 30
        
        # Draw background
        self.canvas.create_rectangle(0, 0, width, height, fill=COLORS["card"], outline="")
        
        # Calculate level width
        level_width = int(width * self.level)
        
        # Determine color based on level
        if self.level < 0.6:
            color = COLORS["success"]
        elif self.level < 0.8:
            color = COLORS["warning"]
        else:
            color = COLORS["error"]
        
        # Draw level
        if level_width > 0:
            self.canvas.create_rectangle(0, 0, level_width, height, fill=color, outline="")
        
        # Draw segments
        for i in range(1, 10):
            x = width * (i / 10)
            self.canvas.create_line(x, 0, x, height, fill=COLORS["background"], width=1)
    
    def set_level(self, level):
        """Set the current audio level (0.0 to 1.0)"""
        self.target_level = max(0.0, min(1.0, level))
        
        if not self.is_animating:
            self.is_animating = True
            self._animate_level()
    
    def _animate_level(self):
        """Animate the level change"""
        # Smoothly transition to target level
        diff = self.target_level - self.level
        self.level += diff * 0.3
        
        # Redraw meter
        self._draw_meter()
        
        # Continue animation if needed
        if abs(diff) > 0.01:
            self.after(30, self._animate_level)
        else:
            self.is_animating = False


class AudioVisualizer(ctk.CTkFrame):
    """Audio waveform visualizer"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Create matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(5, 2), dpi=100)
        self.fig.patch.set_facecolor(COLORS["background"])
        self.ax.set_facecolor(COLORS["background"])
        
        # Remove spines and ticks
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        # Set up plot
        self.line, = self.ax.plot([], [], lw=2, color=COLORS["primary"])
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(-1, 1)
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Initialize data
        self.data = np.zeros(100)
    
    def update_data(self, new_data):
        """Update visualizer with new audio data"""
        # Normalize data
        if len(new_data) > 0:
            normalized = new_data / (np.max(np.abs(new_data)) + 1e-10)
            
            # Update data buffer (rolling window)
            self.data = np.roll(self.data, -len(normalized))
            self.data[-len(normalized):] = normalized
            
            # Update plot
            self.line.set_data(range(len(self.data)), self.data)
            self.canvas.draw_idle()


class CustomSlider(ctk.CTkSlider):
    """Enhanced slider with value display and animations"""
    
    def __init__(self, master, command=None, **kwargs):
        self.value_var = kwargs.pop("variable", None)
        self.show_value = kwargs.pop("show_value", True)
        self.format_string = kwargs.pop("format_string", "{:.2f}")
        self.label_width = kwargs.pop("label_width", 50)
        
        # Create a frame to hold slider and label
        self.frame = ctk.CTkFrame(master, fg_color="transparent")
        self.frame.pack(fill="x", pady=5)
        
        # Initialize the slider in the frame
        super().__init__(self.frame, variable=self.value_var, command=self._on_slider_change, **kwargs)
        self.pack(side="left", fill="x", expand=True)
        
        # Create value label if needed
        if self.show_value:
            self.value_label = ctk.CTkLabel(
                self.frame, 
                text=self.format_string.format(self.value_var.get() if self.value_var else 0),
                width=self.label_width
            )
            self.value_label.pack(side="right", padx=(10, 0))
        
        # Store original command
        self.user_command = command
    
    def _on_slider_change(self, value):
        """Handle slider value change"""
        # Update label
        if self.show_value:
            self.value_label.configure(text=self.format_string.format(value))
        
        # Call user command if provided
        if self.user_command:
            self.user_command(value)


class EffectButton(ctk.CTkButton):
    """Button for selecting voice effect presets"""
    
    def __init__(self, master, text, command=None, **kwargs):
        self.is_selected = False
        self.effect_name = text
        
        super().__init__(
            master, 
            text=text,
            fg_color=COLORS["card"],
            hover_color=COLORS["primary"],
            command=self._on_click,
            **kwargs
        )
        
        # Store user command
        self.user_command = command
    
    def _on_click(self):
        """Handle button click"""
        # Call user command if provided
        if self.user_command:
            self.user_command(self.effect_name)
    
    def select(self):
        """Mark button as selected"""
        self.is_selected = True
        self.configure(fg_color=COLORS["primary"])
    
    def deselect(self):
        """Mark button as not selected"""
        self.is_selected = False
        self.configure(fg_color=COLORS["card"])


class TabView(ctk.CTkTabview):
    """Enhanced tab view with animations"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Configure colors
        self.configure(
            fg_color=COLORS["background"],
            segmented_button_fg_color=COLORS["card"],
            segmented_button_selected_color=COLORS["primary"],
            segmented_button_selected_hover_color=COLORS["secondary"],
            segmented_button_unselected_hover_color=COLORS["card"]
        )


class VoiceChangerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VChanger")
        self.geometry("900x650")
        self.resizable(True, True)
        self.minsize(800, 600)
        
        # Configure appearance
        self.configure(fg_color=COLORS["background"])

        # App state
        self.pitch_shift = ctk.DoubleVar(value=1.0)
        self.volume = ctk.DoubleVar(value=1.0)
        self.monitor = ctk.BooleanVar(value=True)
        self.theme_var = ctk.StringVar(value="dark")
        self.running = False
        self.recording = False
        self.current_effect = "Normal"
        self.audio_data = np.zeros(1024)

        # Devices
        self.input_device = None
        self.output_device = None
        self.input_devices = []
        self.output_devices = []

        self.wav_file = None

        # Set up devices
        self.set_default_devices()
        
        # Build UI
        self.build_ui()
        
        # Start animation loop
        self.after(100, self.update_animations)

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
        # Create main layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.create_sidebar()
        
        # Main content area
        self.create_main_content()
        
        # Status bar
        self.create_status_bar()

    def create_sidebar(self):
        # Sidebar frame
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=COLORS["card"])
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # App title with shadow effect
        title_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_frame.pack(pady=(20, 5), padx=10, fill="x")
        
        title = ctk.CTkLabel(
            title_frame, 
            text="VChanger", 
            font=ctk.CTkFont(family="Arial", size=24, weight="bold"),
            text_color=COLORS["primary"]
        )
        title.pack(pady=5)
        
        subtitle = ctk.CTkLabel(
            title_frame, 
            text="Voice Changer", 
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=COLORS["text_secondary"]
        )
        subtitle.pack(pady=(0, 10))
        
        # Separator
        separator = ctk.CTkFrame(self.sidebar, height=2, fg_color=COLORS["background"])
        separator.pack(fill="x", padx=15, pady=10)
        
        # Control buttons
        self.start_button = AnimatedButton(
            self.sidebar, 
            text="Start Processing", 
            command=self.start_voice_changer,
            fg_color=COLORS["primary"],
            hover_color=COLORS["secondary"]
        )
        self.start_button.pack(pady=(20, 10), padx=20, fill="x")

        self.stop_button = AnimatedButton(
            self.sidebar, 
            text="Stop Processing", 
            command=self.stop_voice_changer, 
            state="disabled",
            fg_color=COLORS["card"],
            hover_color=COLORS["secondary"]
        )
        self.stop_button.pack(pady=10, padx=20, fill="x")
        
        # Separator
        separator2 = ctk.CTkFrame(self.sidebar, height=2, fg_color=COLORS["background"])
        separator2.pack(fill="x", padx=15, pady=10)
        
        # Recording controls
        record_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        record_frame.pack(pady=10, padx=20, fill="x")
        
        self.record_button = AnimatedButton(
            record_frame, 
            text="● Record", 
            command=self.start_recording,
            fg_color=COLORS["card"],
            hover_color=COLORS["recording"],
            text_color=COLORS["recording"],
            pulse=True,
            pulse_color=COLORS["recording"],
            pulse_speed=1.5
        )
        self.record_button.pack(pady=5, fill="x")

        self.stop_record_button = AnimatedButton(
            record_frame, 
            text="■ Stop Recording", 
            command=self.stop_recording, 
            state="disabled",
            fg_color=COLORS["card"],
            hover_color=COLORS["secondary"]
        )
        self.stop_record_button.pack(pady=5, fill="x")
        
        # Separator
        separator3 = ctk.CTkFrame(self.sidebar, height=2, fg_color=COLORS["background"])
        separator3.pack(fill="x", padx=15, pady=10)
        
        # Profile management
        profile_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        profile_frame.pack(pady=10, padx=20, fill="x")
        
        profile_label = ctk.CTkLabel(
            profile_frame, 
            text="Profiles", 
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            anchor="w"
        )
        profile_label.pack(pady=5, fill="x")
        
        self.save_profile_btn = AnimatedButton(
            profile_frame, 
            text="Save Profile", 
            command=self.save_profile,
            fg_color=COLORS["card"],
            hover_color=COLORS["primary"]
        )
        self.save_profile_btn.pack(pady=5, fill="x")

        self.load_profile_btn = AnimatedButton(
            profile_frame, 
            text="Load Profile", 
            command=self.load_profile,
            fg_color=COLORS["card"],
            hover_color=COLORS["primary"]
        )
        self.load_profile_btn.pack(pady=5, fill="x")
        
        # Theme toggle at bottom
        theme_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        theme_frame.pack(side="bottom", pady=20, padx=20, fill="x")
        
        self.theme_switch = ctk.CTkSwitch(
            theme_frame, 
            text="Dark Mode", 
            command=self.toggle_theme,
            variable=self.theme_var,
            onvalue="dark",
            offvalue="light",
            progress_color=COLORS["primary"],
            button_color=COLORS["secondary"],
            button_hover_color=COLORS["primary"]
        )
        self.theme_switch.pack(pady=5)
        
        # Status indicator
        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.pack(side="bottom", pady=10, padx=20, fill="x")
        
        self.status_indicator = ctk.CTkFrame(
            self.status_frame, 
            width=15, 
            height=15, 
            corner_radius=7,
            fg_color=COLORS["text_secondary"]
        )
        self.status_indicator.pack(side="left", padx=(0, 10))
        
        self.status_label = ctk.CTkLabel(
            self.status_frame, 
            text="Status: Idle", 
            font=ctk.CTkFont(family="Arial", size=12),
            anchor="w"
        )
        self.status_label.pack(side="left", fill="x")

    def create_main_content(self):
        # Main content frame
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=COLORS["background"])
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        # Create tab view
        self.tab_view = TabView(self.main_frame)
        self.tab_view.pack(fill="both", expand=True)
        
        # Add tabs
        self.main_tab = self.tab_view.add("Main")
        self.settings_tab = self.tab_view.add("Settings")
        self.about_tab = self.tab_view.add("About")
        
        # Configure tabs
        self.configure_main_tab()
        self.configure_settings_tab()
        self.configure_about_tab()

    def configure_main_tab(self):
        # Main tab content
        self.main_tab.grid_columnconfigure(0, weight=1)
        
        # Audio visualizer
        visualizer_frame = ctk.CTkFrame(self.main_tab, fg_color=COLORS["card"], corner_radius=10)
        visualizer_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        visualizer_label = ctk.CTkLabel(
            visualizer_frame, 
            text="Audio Visualization", 
            font=ctk.CTkFont(family="Arial", size=16, weight="bold")
        )
        visualizer_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        # Audio waveform
        self.visualizer = AudioVisualizer(visualizer_frame, fg_color="transparent", height=150)
        self.visualizer.pack(fill="x", padx=15, pady=10, expand=True)
        
        # VU Meter
        vu_frame = ctk.CTkFrame(visualizer_frame, fg_color="transparent")
        vu_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        vu_label = ctk.CTkLabel(vu_frame, text="Input Level:", anchor="w")
        vu_label.pack(side="left", padx=(0, 10))
        
        self.vu_meter = VUMeter(vu_frame, height=20)
        self.vu_meter.pack(side="left", fill="x", expand=True)
        
        # Controls section
        controls_frame = ctk.CTkFrame(self.main_tab, fg_color=COLORS["card"], corner_radius=10)
        controls_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        # Pitch control
        pitch_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        pitch_frame.pack(fill="x", padx=15, pady=15)
        
        pitch_label = ctk.CTkLabel(
            pitch_frame, 
            text="Pitch Shift", 
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            anchor="w"
        )
        pitch_label.pack(fill="x", pady=(0, 5))
        
        self.pitch_slider = CustomSlider(
            pitch_frame, 
            from_=0.5, 
            to=2.0, 
            variable=self.pitch_shift,
            format_string="{:.2f}x"
        )
        
        # Voice effect presets
        effects_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        effects_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        effects_label = ctk.CTkLabel(
            effects_frame, 
            text="Voice Effects", 
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            anchor="w"
        )
        effects_label.pack(anchor="w", pady=(10, 5))
        
        # Effect buttons grid
        effects_grid = ctk.CTkFrame(effects_frame, fg_color="transparent")
        effects_grid.pack(fill="x")
        
        # Create effect buttons
        self.effect_buttons = {}
        effects = [
            ("Normal", "Normal voice with no effects"),
            ("Alien", "High-pitched alien voice"),
            ("Robot", "Mechanical robot voice"),
            ("Deep", "Deep, low-pitched voice"),
            ("Chipmunk", "High-pitched chipmunk voice")
        ]
        
        for i, (effect, tooltip) in enumerate(effects):
            btn = EffectButton(
                effects_grid,
                text=effect,
                width=100,
                height=30,
                command=self.apply_preset
            )
            btn.grid(row=0, column=i, padx=5, pady=5)
            
            # Add tooltip functionality
            self.create_tooltip(btn, tooltip)
            
            self.effect_buttons[effect] = btn
        
        # Select default effect
        self.effect_buttons["Normal"].select()
        
        # Volume control
        volume_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        volume_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        volume_label = ctk.CTkLabel(
            volume_frame, 
            text="Volume", 
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            anchor="w"
        )
        volume_label.pack(fill="x", pady=(10, 5))
        
        self.volume_slider = CustomSlider(
            volume_frame, 
            from_=0.0, 
            to=2.0, 
            variable=self.volume,
            format_string="{:.2f}x"
        )

    def configure_settings_tab(self):
        # Settings tab content
        self.settings_tab.grid_columnconfigure(0, weight=1)
        
        # Devices section
        device_frame = ctk.CTkFrame(self.settings_tab, fg_color=COLORS["card"], corner_radius=10)
        device_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        device_label = ctk.CTkLabel(
            device_frame, 
            text="Audio Devices", 
            font=ctk.CTkFont(family="Arial", size=16, weight="bold")
        )
        device_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Input device
        input_frame = ctk.CTkFrame(device_frame, fg_color="transparent")
        input_frame.pack(fill="x", padx=15, pady=5)
        
        input_label = ctk.CTkLabel(input_frame, text="Input Device:", anchor="w", width=100)
        input_label.pack(side="left", padx=(0, 10))
        
        self.input_selector = ctk.CTkOptionMenu(
            input_frame, 
            values=self.input_devices,
            command=self.set_input_device,
            fg_color=COLORS["background"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["secondary"],
            dropdown_fg_color=COLORS["background"]
        )
        self.input_selector.set(self.input_device)
        self.input_selector.pack(side="left", fill="x", expand=True)
        
        # Output device
        output_frame = ctk.CTkFrame(device_frame, fg_color="transparent")
        output_frame.pack(fill="x", padx=15, pady=5)
        
        output_label = ctk.CTkLabel(output_frame, text="Output Device:", anchor="w", width=100)
        output_label.pack(side="left", padx=(0, 10))
        
        self.output_selector = ctk.CTkOptionMenu(
            output_frame, 
            values=self.output_devices,
            command=self.set_output_device,
            fg_color=COLORS["background"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["secondary"],
            dropdown_fg_color=COLORS["background"]
        )
        self.output_selector.set(self.output_device)
        self.output_selector.pack(side="left", fill="x", expand=True)
        
        # Monitor toggle
        monitor_frame = ctk.CTkFrame(device_frame, fg_color="transparent")
        monitor_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        self.monitor_toggle = ctk.CTkSwitch(
            monitor_frame, 
            text="Monitor Output", 
            variable=self.monitor,
            progress_color=COLORS["primary"],
            button_color=COLORS["secondary"],
            button_hover_color=COLORS["primary"]
        )
        self.monitor_toggle.pack(pady=10)
        
        # Advanced settings
        advanced_frame = ctk.CTkFrame(self.settings_tab, fg_color=COLORS["card"], corner_radius=10)
        advanced_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        advanced_label = ctk.CTkLabel(
            advanced_frame, 
            text="Advanced Settings", 
            font=ctk.CTkFont(family="Arial", size=16, weight="bold")
        )
        advanced_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Sample rate
        sample_frame = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        sample_frame.pack(fill="x", padx=15, pady=5)
        
        sample_label = ctk.CTkLabel(sample_frame, text="Sample Rate:", anchor="w", width=100)
        sample_label.pack(side="left", padx=(0, 10))
        
        self.sample_selector = ctk.CTkOptionMenu(
            sample_frame, 
            values=["44100 Hz", "48000 Hz", "96000 Hz"],
            fg_color=COLORS["background"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["secondary"],
            dropdown_fg_color=COLORS["background"]
        )
        self.sample_selector.set("44100 Hz")
        self.sample_selector.pack(side="left", fill="x", expand=True)
        
        # Buffer size
        buffer_frame = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        buffer_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        buffer_label = ctk.CTkLabel(buffer_frame, text="Buffer Size:", anchor="w", width=100)
        buffer_label.pack(side="left", padx=(0, 10))
        
        self.buffer_selector = ctk.CTkOptionMenu(
            buffer_frame, 
            values=["256", "512", "1024", "2048"],
            fg_color=COLORS["background"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["secondary"],
            dropdown_fg_color=COLORS["background"]
        )
        self.buffer_selector.set("1024")
        self.buffer_selector.pack(side="left", fill="x", expand=True)

    def configure_about_tab(self):
        # About tab content
        about_frame = ctk.CTkFrame(self.about_tab, fg_color=COLORS["card"], corner_radius=10)
        about_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # App info
        app_info_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        app_info_frame.pack(fill="x", padx=15, pady=15)
        
        app_title = ctk.CTkLabel(
            app_info_frame, 
            text="VChanger", 
            font=ctk.CTkFont(family="Arial", size=24, weight="bold"),
            text_color=COLORS["primary"]
        )
        app_title.pack(pady=5)
        
        app_subtitle = ctk.CTkLabel(
            app_info_frame, 
            text="Simple Real-Time Voice Changer", 
            font=ctk.CTkFont(family="Arial", size=14)
        )
        app_subtitle.pack(pady=5)
        
        app_description = ctk.CTkLabel(
            app_info_frame, 
            text="A free, real-time voice changer written 100% in Python",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=COLORS["text_secondary"]
        )
        app_description.pack(pady=5)
        
        # Features
        features_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        features_frame.pack(fill="x", padx=15, pady=15)
        
        features_title = ctk.CTkLabel(
            features_frame, 
            text="Features", 
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            anchor="w"
        )
        features_title.pack(anchor="w", pady=5)
        
        features = [
            "Real-time voice pitch shifting",
            "Audio visualization",
            "Recording capability",
            "Multiple voice effect presets",
            "Profile saving and loading",
            "Customizable settings"
        ]
        
        for feature in features:
            feature_label = ctk.CTkLabel(
                features_frame, 
                text=f"• {feature}", 
                anchor="w",
                font=ctk.CTkFont(family="Arial", size=12)
            )
            feature_label.pack(anchor="w", pady=2)
        
        # Credits
        credits_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        credits_frame.pack(fill="x", padx=15, pady=15)
        
        credits_title = ctk.CTkLabel(
            credits_frame, 
            text="Credits", 
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            anchor="w"
        )
        credits_title.pack(anchor="w", pady=5)
        
        credits_text = ctk.CTkLabel(
            credits_frame, 
            text="Created with customtkinter, numpy, and sounddevice",
            anchor="w",
            font=ctk.CTkFont(family="Arial", size=12)
        )
        credits_text.pack(anchor="w", pady=2)
        
        version_label = ctk.CTkLabel(
            credits_frame, 
            text="Version 2.0.0", 
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=COLORS["text_secondary"]
        )
        version_label.pack(anchor="w", pady=(10, 2))

    def create_status_bar(self):
        """Create the status bar at the bottom of the window"""
        self.status_bar = ctk.CTkFrame(self, height=25, fg_color=COLORS["card"])
        self.status_bar.grid(row=1, column=1, sticky="ew", padx=20, pady=(0, 20))
        
        # Status text
        self.status_bar_label = ctk.CTkLabel(
            self.status_bar, 
            text="Ready", 
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=COLORS["text_secondary"]
        )
        self.status_bar_label.pack(side="left", padx=10)
        
        # CPU usage (placeholder)
        self.cpu_label = ctk.CTkLabel(
            self.status_bar, 
            text="CPU: 0%", 
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=COLORS["text_secondary"]
        )
        self.cpu_label.pack(side="right", padx=10)

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        tooltip_window = None
        
        def enter(event):
            nonlocal tooltip_window
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create a toplevel window
            tooltip_window = ctk.CTkToplevel(widget)
            tooltip_window.wm_overrideredirect(True)
            tooltip_window.wm_geometry(f"+{x}+{y}")
            
            label = ctk.CTkLabel(
                tooltip_window, 
                text=text, 
                font=ctk.CTkFont(family="Arial", size=12),
                fg_color=COLORS["card"],
                corner_radius=5,
                padx=5,
                pady=2
            )
            label.pack()
            
        def leave(event):
            nonlocal tooltip_window
            if tooltip_window:
                tooltip_window.destroy()
                tooltip_window = None
        
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def toggle_theme(self):
        """Toggle between light and dark theme"""
        new_theme = self.theme_var.get()
        ctk.set_appearance_mode(new_theme)
        
        # Update colors based on theme
        if new_theme == "light":
            # Update status bar text
            self.status_bar_label.configure(text_color=COLORS["secondary"])
            self.cpu_label.configure(text_color=COLORS["secondary"])
        else:
            # Update status bar text
            self.status_bar_label.configure(text_color=COLORS["text_secondary"])
            self.cpu_label.configure(text_color=COLORS["text_secondary"])
        
        # Update status
        self.update_status(f"Theme changed to {new_theme}")

    def update_animations(self):
        """Update all animations and visual elements"""
        if self.running:
            # Update CPU usage (placeholder)
            self.cpu_label.configure(text=f"CPU: {np.random.randint(5, 15)}%")
            
            # Pulse record button if recording
            if self.recording:
                self.record_button.start_pulse()
            else:
                self.record_button.stop_pulse()
        
        # Schedule next update
        self.after(1000, self.update_animations)

    def update_status(self, message):
        """Update status bar message with animation"""
        self.status_bar_label.configure(text=message)

    def set_input_device(self, device_name):
        """Set the input audio device"""
        self.input_device = device_name
        self.update_status(f"Input device set to: {device_name}")

    def set_output_device(self, device_name):
        """Set the output audio device"""
        self.output_device = device_name
        self.update_status(f"Output device set to: {device_name}")

    def apply_preset(self, preset):
        """Apply a voice effect preset"""
        # Update current effect
        self.current_effect = preset
        
        # Update UI
        for effect, button in self.effect_buttons.items():
            if effect == preset:
                button.select()
            else:
                button.deselect()
        
        # Set pitch based on preset
        presets = {
            "Normal": 1.0,
            "Alien": 1.6,
            "Robot": 0.9,
            "Deep": 0.6,
            "Chipmunk": 1.8,
        }
        self.pitch_shift.set(presets.get(preset, 1.0))
        
        # Update status
        self.update_status(f"Applied {preset} voice effect")

    def start_voice_changer(self):
        """Start the voice changer processing"""
        if not self.running:
            self.running = True
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            
            # Update status indicator
            self.status_indicator.configure(fg_color=COLORS["success"])
            self.status_label.configure(text="Status: Running")
            self.update_status("Voice changer started")
            
            # Start audio processing thread
            threading.Thread(target=self.audio_loop, daemon=True).start()

    def stop_voice_changer(self):
        """Stop the voice changer processing"""
        self.running = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        
        # Update status indicator
        self.status_indicator.configure(fg_color=COLORS["text_secondary"])
        self.status_label.configure(text="Status: Stopped")
        self.update_status("Voice changer stopped")

    def start_recording(self):
        """Start recording the processed audio"""
        if not self.recording:
            self.recording = True
            self.wav_file = wave.open("recorded_voice.wav", 'wb')
            self.wav_file.setnchannels(1)
            self.wav_file.setsampwidth(2)
            self.wav_file.setframerate(44100)
            
            # Update UI
            self.record_button.configure(state="disabled")
            self.stop_record_button.configure(state="normal")
            
            # Update status
            self.status_indicator.configure(fg_color=COLORS["recording"])
            self.status_label.configure(text="Status: Recording")
            self.update_status("Recording started")

    def stop_recording(self):
        """Stop recording the processed audio"""
        if self.recording:
            self.recording = False
            self.wav_file.close()
            self.wav_file = None
            
            # Update UI
            self.record_button.configure(state="normal")
            self.stop_record_button.configure(state="disabled")
            
            # Update status
            if self.running:
                self.status_indicator.configure(fg_color=COLORS["success"])
                self.status_label.configure(text="Status: Running")
            else:
                self.status_indicator.configure(fg_color=COLORS["text_secondary"])
                self.status_label.configure(text="Status: Idle")
            
            self.update_status("Recording saved to recorded_voice.wav")

    def audio_loop(self):
        """Main audio processing loop"""
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
            self.update_status(f"Audio stream error: {e}")
            print("Audio stream error:", e)
            
            # Reset UI state
            self.running = False
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.status_indicator.configure(fg_color=COLORS["error"])

    def audio_callback(self, indata, outdata, frames, time, status):
        """Process audio data in real-time"""
        if not self.running:
            outdata[:] = np.zeros_like(indata)
            return

        try:
            pitch = self.pitch_shift.get()
            vol = self.volume.get()
            audio = indata[:, 0]
            
            # Store audio data for visualization
            self.audio_data = audio
            
            # Update VU meter (on main thread)
            level = np.sqrt(np.mean(audio**2)) * 2  # RMS level
            self.after(0, lambda: self.vu_meter.set_level(level))
            
            # Update visualizer (on main thread)
            self.after(0, lambda: self.visualizer.update_data(audio))
            
            # Process audio with pitch shifting
            indices = np.arange(0, len(audio), pitch)
            indices = indices[indices < len(audio)].astype(int)
            shifted_audio = audio[indices]

            if len(shifted_audio) < len(audio):
                shifted_audio = np.pad(shifted_audio, (0, len(audio) - len(shifted_audio)))
            elif len(shifted_audio) > len(audio):
                shifted_audio = shifted_audio[:len(audio)]

            # Apply volume
            output_audio = shifted_audio * vol

            # Output audio if monitoring is enabled
            if self.monitor.get():
                outdata[:, 0] = output_audio
            else:
                outdata[:, 0] = np.zeros_like(audio)

            # Record if active
            if self.recording and self.wav_file:
                data_to_write = (output_audio * 32767).astype(np.int16).tobytes()
                self.wav_file.writeframes(data_to_write)

        except Exception as e:
            print("Callback error:", e)
            outdata[:, 0] = np.zeros(frames)

    def get_device_index(self, name, is_input=True):
        """Get the index of an audio device by name"""
        for i, d in enumerate(sd.query_devices()):
            if d['name'] == name and ((is_input and d['max_input_channels'] > 0) or
                                      (not is_input and d['max_output_channels'] > 0)):
                return i
        return None

    def save_profile(self):
        """Save the current settings to a profile file"""
        profile_data = {
            "pitch": self.pitch_shift.get(),
            "volume": self.volume.get(),
            "effect": self.current_effect
        }
        
        path = filedialog.asksaveasfilename(
            defaultextension=".json", 
            filetypes=[("JSON", "*.json")],
            title="Save Voice Profile"
        )
        
        if path:
            with open(path, "w") as f:
                json.dump(profile_data, f, indent=2)
            
            # Get filename for status
            filename = os.path.basename(path)
            self.update_status(f"Profile saved as {filename}")

    def load_profile(self):
        """Load settings from a profile file"""
        path = filedialog.askopenfilename(
            defaultextension=".json", 
            filetypes=[("JSON", "*.json")],
            title="Load Voice Profile"
        )
        
        if path:
            try:
                with open(path, "r") as f:
                    profile_data = json.load(f)
                    
                    # Apply settings
                    self.pitch_shift.set(profile_data.get("pitch", 1.0))
                    self.volume.set(profile_data.get("volume", 1.0))
                    
                    # Apply effect if specified
                    effect = profile_data.get("effect", "Normal")
                    if effect in self.effect_buttons:
                        self.apply_preset(effect)
                
                # Get filename for status
                filename = os.path.basename(path)
                self.update_status(f"Profile loaded from {filename}")
                
            except Exception as e:
                self.update_status(f"Error loading profile: {e}")


if __name__ == "__main__":
    app = VoiceChangerApp()
    app.mainloop()
