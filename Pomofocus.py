import tkinter as tk
import os
import ctypes
import pygame
import random
import sys
import time


class PomodoroWidget:
    def __init__(self, root):
        # Initialize pygame mixer for audio with specific parameters for macOS
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        pygame.init()

        self.root = root
        self.root.title("Pomodoro Widget")

        # Make it an overlay window
        self.root.overrideredirect(True)  # Remove title bar
        self.root.wm_attributes("-topmost", 1)  # Always on top

        # Set transparency for macOS
        self.root.attributes("-alpha", 0.55)

        # Compact size for widget
        self.root.geometry("240x120+50+50")

        # Add ability to drag the window
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<ButtonRelease-1>", self.stop_move)
        self.root.bind("<B1-Motion>", self.do_move)

        # Variables
        self.time_var = tk.StringVar()
        self.time_var.set("25:00")
        self.running = False
        self.paused = False
        self.remaining_time = 25 * 60  # 25 minutes
        self.muted = False  # Track mute state
        self.warning_played = False  # Track if warning sound has been played
        self.song_was_playing = False  # Track if a song was playing before warning
        self.song_position = 0  # Track position in song for resuming after warning

        # Store the current playlist
        self.current_playlist = []
        self.current_song_index = 0

        # Default music library path - use a more standard macOS path
        self.default_music_path = os.path.expanduser("/Users/kelvadas/Sounds")

        # Create a frame with transparent background
        self.main_frame = tk.Frame(root, bg="#333333")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create a label for the timer
        self.label = tk.Label(self.main_frame, textvariable=self.time_var,
                              font=("Helvetica", 36), bg="#333333", fg="white")
        self.label.pack(pady=5)

        # Current song display
        self.song_var = tk.StringVar()
        self.song_var.set("Ready to focus")
        self.song_label = tk.Label(self.main_frame, textvariable=self.song_var,
                                   width=25, bg="#333333", fg="#AAAAAA")
        self.song_label.pack(pady=5)

        # Button frame
        self.button_frame = tk.Frame(self.main_frame, bg="#333333")
        self.button_frame.pack(pady=5)

        # Control buttons
        self.start_button = tk.Button(self.button_frame, text="▶", command=self.toggle_timer,
                                      width=1, bg="#555555", fg="#bf2626")
        self.start_button.pack(side=tk.LEFT, padx=3)

        self.reset_button = tk.Button(self.button_frame, text="⟳", command=self.reset_timer,
                                      width=1, bg="#555555", fg="#bf2626")
        self.reset_button.pack(side=tk.LEFT, padx=3)

        self.shuffle_button = tk.Button(self.button_frame, text="♫", command=self.shuffle_music,
                                        width=1, bg="#555555", fg="#bf2626")
        self.shuffle_button.pack(side=tk.LEFT, padx=3)

        self.mute_button = tk.Button(self.button_frame, text="🔊", command=self.toggle_mute,
                                     width=1, bg="#555555", fg="#bf2626")
        self.mute_button.pack(side=tk.LEFT, padx=3)

        # Close button in corner
        self.close_button = tk.Button(self.main_frame, text="×", command=root.destroy,
                                      width=1, bg="#555555", fg="black", bd=0)
        self.close_button.place(x=200, y=0)

        # Add a resize handle in the bottom-left corner
        self.resize_handle = tk.Label(self.main_frame, text="↘", bg="#555555", fg="white",
                                      cursor="sizing")
        self.resize_handle.place(x=0, y=0)  # Position at bottom-left

        # Bind events for resizing
        self.resize_handle.bind("<Button-1>", self.start_resize)
        self.resize_handle.bind("<ButtonRelease-1>", self.stop_resize)
        self.resize_handle.bind("<B1-Motion>", self.do_resize)

        # Track resize state
        self.resizing = False
        self.resize_x = 0
        self.resize_y = 0

        # Pre-load the playlist at startup if the default path exists
        if os.path.exists(self.default_music_path):
            self.current_playlist = self.load_playlist(self.default_music_path)
            if self.current_playlist:
                self.song_var.set(f"Found {len(self.current_playlist)} songs")
            else:
                self.song_var.set("No music files found")

        # Load a warning sound (can be in the same directory as the script)
        self.warning_sound_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "warning.wav")

        # Set up event for song end detection and auto-play next song
        pygame.mixer.music.set_endevent(pygame.USEREVENT)

        # Start an event checking loop for music end events
        self.check_music_events()

    def check_music_events(self):
        """Check for music-related events like song end"""
        for event in pygame.event.get():
            if event.type == pygame.USEREVENT:  # Song has ended
                if self.running and self.current_playlist:
                    # Auto-play next song
                    self.play_next_song()

        # Schedule this check to run again
        self.root.after(100, self.check_music_events)

    def play_next_song(self):
        """Play the next song in the playlist"""
        if not self.current_playlist:
            return

        # Move to next song in playlist
        self.current_song_index = (
            self.current_song_index + 1) % len(self.current_playlist)
        self.play_song(self.current_playlist[self.current_song_index])
        print(f"Auto-playing next song (index {self.current_song_index})")

    def toggle_mute(self):
        """Toggle mute state and update button text"""
        self.muted = not self.muted

        if self.muted:
            # Set volume to 0 (mute)
            pygame.mixer.music.set_volume(0.0)
            self.mute_button.config(text="🔇")
        else:
            # Restore normal volume
            pygame.mixer.music.set_volume(0.7)
            self.mute_button.config(text="🔊")

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def start_resize(self, event):
        """Start the resize operation when clicking on the resize handle"""
        self.resizing = True
        self.resize_x = event.x_root
        self.resize_y = event.y_root

    def stop_resize(self, event):
        """Stop the resize operation"""
        self.resizing = False

    def do_resize(self, event):
        """Perform the resize operation while dragging"""
        if self.resizing:
            # Calculate the change in position
            delta_x = event.x_root - self.resize_x
            delta_y = event.y_root - self.resize_y

            # Get current window size
            width = self.root.winfo_width()
            height = self.root.winfo_height()

            # Calculate new size (minimum size constraints)
            new_width = max(200, width + delta_x)
            new_height = max(150, height + delta_y)

            # Set the new size
            self.root.geometry(f"{new_width}x{new_height}")

            # Update the resize handle position
            self.resize_handle.place(x=0, y=new_height-20)

            # Update reference points
            self.resize_x = event.x_root
            self.resize_y = event.y_root

    def load_playlist(self, playlist_folder):
        # Find all audio files in the specified folder
        # Prioritize OGG files which work better on macOS
        playlist = []
        try:
            for filename in os.listdir(playlist_folder):
                # Prioritize OGG format which works better on macOS
                if filename.lower().endswith(('.mp3', '.ogg', '.wav', '.flac')):
                    full_path = os.path.join(playlist_folder, filename)
                    playlist.append(full_path)
            print(f"Loaded {len(playlist)} songs from {playlist_folder}")
            return playlist
        except Exception as e:
            print(f"Error loading playlist: {e}")
            return []

    def play_song(self, song_path):
        # Stop any currently playing music
        pygame.mixer.music.stop()

        # Temporarily disable end event detection when manually changing songs
        pygame.mixer.music.set_endevent()  # Clear the event

        try:
            # For macOS, ensure we properly handle file paths
            abs_path = os.path.abspath(song_path)
            pygame.mixer.music.load(abs_path)
            pygame.mixer.music.play()

            # Set volume based on mute state
            if self.muted:
                pygame.mixer.music.set_volume(0.0)
            else:
                pygame.mixer.music.set_volume(0.7)

            # Update display with song name
            song_name = os.path.basename(song_path)
            self.song_var.set(f"♫ {song_name[:20]}")
            print(f"Now playing: {song_name}")

            # Re-enable end event detection after a short delay
            self.root.after(
                500, lambda: pygame.mixer.music.set_endevent(pygame.USEREVENT))
        except Exception as e:
            print(f"Error playing music: {e}")
            self.song_var.set("Error playing music")

            # Try to convert to OGG if possible
            if not song_path.lower().endswith('.ogg'):
                self.song_var.set("Try converting to OGG format")

    def play_warning(self):
        """Play the warning sound isolated from the current song"""
        try:
            # Check if music is playing
            self.song_was_playing = pygame.mixer.music.get_busy()

            if self.song_was_playing:
                # Get the current position in the song to resume later
                self.song_position = pygame.mixer.music.get_pos() / 1000.0  # Convert to seconds
                # Pause the current song
                pygame.mixer.music.pause()
                print(f"Music paused at position: {self.song_position}s")

            # Show warning message
            original_text = self.song_var.get()
            self.song_var.set("⚠️ 5 MINUTES REMAINING ⚠️")

            if os.path.exists(self.warning_sound_path):
                # Create a separate channel for the warning sound
                warning_channel = pygame.mixer.Channel(1)
                warning_sound = pygame.mixer.Sound(self.warning_sound_path)
                # Play at a suitable volume
                warning_sound.set_volume(0.7 if not self.muted else 0.0)
                warning_channel.play(warning_sound)

                # Schedule resuming the music after 5 seconds
                self.root.after(
                    3000, lambda: self.resume_after_warning(original_text))

                print("Warning sound played - 5 minutes remaining")
            else:
                print("Warning sound file not found")
                # If no sound file, still resume after 2 seconds
                self.root.after(
                    2000, lambda: self.resume_after_warning(original_text))
        except Exception as e:
            print(f"Error playing warning sound: {e}")

    def resume_after_warning(self, original_text):
        """Resume music after warning sound is done"""
        # Restore the original song text
        self.song_var.set(original_text)

        # Resume music if it was playing before
        if self.song_was_playing and pygame.mixer.get_init():
            try:
                current_song = self.current_playlist[self.current_song_index]
                # Need to reload the song and skip to previous position
                pygame.mixer.music.load(current_song)
                # Start playing and try to seek to the position where we paused
                pygame.mixer.music.play()
                # On some platforms/files seeking might not work perfectly
                try:
                    pygame.mixer.music.set_pos(self.song_position)
                except:
                    print("Could not seek to exact position in song")

                # Set volume based on mute state
                if self.muted:
                    pygame.mixer.music.set_volume(0.0)
                else:
                    pygame.mixer.music.set_volume(0.7)

                print("Music resumed after warning")
            except Exception as e:
                print(f"Error resuming music: {e}")

    def shuffle_music(self):
        if not self.current_playlist:
            print("No playlist loaded.")
            return

        # Stop checking for end-of-song events temporarily
        pygame.mixer.music.set_endevent()  # Clear the event

        # Pick a random song from the playlist, different from the current one
        if len(self.current_playlist) > 1:
            current_index = self.current_song_index
            while self.current_song_index == current_index:
                self.current_song_index = random.randint(
                    0, len(self.current_playlist) - 1)
        else:
            self.current_song_index = 0

        # Play the selected song
        self.play_song(self.current_playlist[self.current_song_index])

        # Reset the end event after a short delay to avoid immediate triggering
        self.root.after(
            500, lambda: pygame.mixer.music.set_endevent(pygame.USEREVENT))

    def center_on_screen(self):
        """Center the widget on the screen"""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Get widget dimensions
        widget_width = self.root.winfo_width()
        widget_height = self.root.winfo_height()

        # Calculate center position
        x = (screen_width - widget_width) // 2
        y = (screen_height - widget_height) // 2

        # Set the new position
        self.root.geometry(f"+{x}+{y}")
        print(f"Widget centered at position: {x}, {y}")

    def update_time(self):
        if self.running:
            minutes, seconds = divmod(self.remaining_time, 60)
            self.time_var.set(f"{minutes:02}:{seconds:02}")

            # Check for 5-minute warning (300 seconds)
            if self.remaining_time == 300 and not self.warning_played:
                self.warning_played = True
                # Change timer color to orange for the final 5 minutes
                self.label.config(fg="#FF9500")  # Orange for warning period
                # Play the warning sound isolated from the music
                self.play_warning()

            if self.remaining_time > 0:
                self.remaining_time -= 1
                self.root.after(1000, self.update_time)
            else:
                self.running = False
                pygame.mixer.music.stop()
                self.song_var.set("Time's up!")
                self.label.config(fg="white")  # Reset color
                self.center_on_screen()  # Center the widget on screen when timer ends

    def toggle_timer(self):
        if not self.running:
            self.start_timer()
        else:
            self.pause_timer()

    def start_timer(self):
        if not self.running:
            # Only start new music if we're not paused
            if not self.paused:
                if self.current_playlist:
                    self.current_song_index = random.randint(
                        0, len(self.current_playlist) - 1)
                    self.play_song(self.current_playlist[self.current_song_index])
                else:
                    self.song_var.set("No music files found!")
            else:
                # Resume paused music
                pygame.mixer.music.unpause()

            self.running = True
            self.paused = False
            self.warning_played = False  # Reset warning state
            self.label.config(fg="white")  # Reset color
            self.start_button.config(text="⏸")  # Change to pause icon
            self.update_time()

    def pause_timer(self):
        if self.running:
            # If timer is running, pause it
            self.running = False
            self.paused = True

            # Pause the music
            pygame.mixer.music.pause()

            self.start_button.config(text="▶")  # Change to play icon

        elif self.paused:
            # If timer is paused, resume it
            self.running = True
            self.paused = False

            # Resume music
            pygame.mixer.music.unpause()

            # Disable event detection temporarily to avoid false triggers
            current_event = pygame.mixer.music.get_endevent()
            pygame.mixer.music.set_endevent()

            # Schedule the re-enabling of event detection after a delay
            self.root.after(
                1000, lambda: pygame.mixer.music.set_endevent(current_event))

            # Continue the timer
            self.update_time()

    def reset_timer(self):
        self.running = False
        self.paused = False
        self.remaining_time = 25 * 60
        self.time_var.set("25:00")
        self.warning_played = False  # Reset warning state
        self.label.config(fg="white")  # Reset color
        pygame.mixer.music.stop()
        self.song_var.set("Timer reset")
        self.start_button.config(text="▶")  # Reset to play icon

    def __del__(self):
        # Ensure pygame mixer is properly closed
        pygame.mixer.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = PomodoroWidget(root)
    root.mainloop()
