# ♪ Rainy Lofi Terminal Player 🎧🌧️

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Escape into a world of chill beats and calming ambiances directly from your terminal! This Python-based TUI (Text User Interface) player brings you:

*   🎶 **Lofi Hip Hop Radio:** Stream the iconic Lofi Girl YouTube stream.
*   ☔ **Ambient Sounds:** Mix in soothing rain and immersive storm sounds to create your perfect atmosphere.
*   ✨ **Visual Ambiance:** Enjoy a dynamic terminal animation with falling rain, floating music notes, and occasional lightning flashes.
*   🎛️ **Full Control:** Adjust volumes, toggle play/pause for each sound source, and use presets for quick mood changes.
*   ⌨️ **Keyboard Driven:** Intuitive keyboard shortcuts for a seamless experience.

<p align="center">
  <img src="https://github.com/user-attachments/assets/12416a52-19a8-4d40-8dac-07ddf7c5b95d" alt="A placeholder image of a cute kitten in a terminal-like setting - Replace with an actual screenshot/gif!" width="600"/>
  <br/>
</p>


---

## 🚀 Features

*   **Triple Threat Audio:** Lofi stream, rain sounds, and storm sounds.
*   **Independent Controls:** Play/pause and volume control for each audio source.
*   **Sound Presets:**
    *   `1`: Chill Focus (Lofi + gentle rain)
    *   `2`: Study Storm (Lofi + louder rain & storm)
    *   `3`: Quiet Lofi (Just the beats)
    *   `0`: Silence All
*   **Dynamic Animations:**
    *   🌧️ Raindrops falling (density based on rain volume).
    *   🎵 Music notes floating upwards when lofi is playing.
    *   ⚡ Lightning flashes during storms.
*   **Informative UI:**
    *   Displays current playing status and volume for each track.
    *   Volume bars for a visual representation.
    *   Feedback messages for actions.
    *   Help screen with keybinds.
*   **Responsive Design:** Adapts to smaller terminal sizes with a minimal UI.
*   **Error Handling:** Detects missing audio files, `mpv` installation, and internet connectivity issues for the lofi stream.

---

## 🛠️ How It Works

This program leverages the power of `mpv` (a versatile command-line media player) for audio playback.

1.  **MPV Instances:** For each sound source (lofi, rain, storm), a separate `mpv` process is started in the background.
    *   Lofi music is streamed directly from the YouTube URL (requires `yt-dlp` or `youtube-dl` to be installed for `mpv` to resolve it).
    *   Rain and storm sounds are played from local `.ogg` files.
2.  **IPC Control:** The script communicates with each `mpv` instance via its IPC (Inter-Process Communication) socket. JSON commands are sent to control properties like volume and pause state.
3.  **Curses TUI:** The `curses` library is used to create the text-based user interface, manage screen drawing, and handle keyboard input.
4.  **State Management:** Python dictionaries keep track of the desired and actual state of each sound (playing, volume, running status, errors).
5.  **Animation Loop:** A main loop refreshes the UI at regular intervals, updating animations based on the current sound states and random events.
6.  **Internet Check:** Before attempting to play the lofi stream, and if the stream unexpectedly stops, a simple socket connection to a public DNS server is made to check for general internet connectivity.

---

## ⚙️ Dependencies & Setup

Make sure you have the following installed:

1.  **Python 3.7+**
2.  **`mpv` Media Player:**
    *   **Linux:** `sudo apt install mpv` or `sudo pacman -S mpv` (or your distro's equivalent).
    *   **macOS:** `brew install mpv`.
    *   **Windows:** Download from [mpv.io](https://mpv.io/installation/) and ensure `mpv.exe` is in your system's PATH.
3.  **`yt-dlp` (Recommended) or `youtube-dl`:**
    *   Needed by `mpv` to play YouTube streams.
    *   Install via pip: `pip install yt-dlp`
    *   Or download from [yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp#installation).
4.  **Python `curses` library:**
    *   **Linux/macOS:** Usually included with Python.
    *   **Windows:** `pip install windows-curses`

**Optional Audio Files:**

*   Place `rain.ogg` and `storm.ogg` files in the same directory as the script for local ambient sounds. If not found, the script will attempt to create empty files (which won't produce sound). You can find free `.ogg` sound effects online!

---

## 🎮 How to Run

1.  Clone this repository (or just save the Python script).
2.  Ensure all dependencies are installed.
3.  Navigate to the script's directory in your terminal.
4.  Run the script:
    ```bash
    python your_script_name.py
    ```
    (Replace `your_script_name.py` with the actual filename).

---

## ⌨️ Keybinds

*   **Lofi Controls:**
    *   `L`: Play/Pause Lofi
    *   `O`: Lofi Volume Up
    *   `K`: Lofi Volume Down
*   **Rain Controls:**
    *   `R`: Play/Pause Rain
    *   `E`: Rain Volume Up
    *   `D`: Rain Volume Down
*   **Storm Controls:**
    *   `S`: Play/Pause Storm
    *   `T`: Storm Volume Up
    *   `G`: Storm Volume Down
*   **Presets:**
    *   `1`: Chill Focus
    *   `2`: Study Storm
    *   `3`: Quiet Lofi
    *   `0`: Silence All
*   **General:**
    *   `H`: Toggle Help Screen
    *   `Q`: Quit Player

---

## 📝 To-Do / Future Ideas

*   [ ] Allow custom YouTube stream URLs.
*   [ ] More animation variety or themes.
*   [ ] Configuration file for custom keybinds/colors.
*   [ ] Better error messages/logging.
*   [ ] Add more ambient sound options.



---

<p align="center">
  Crafted with 💜 by Your Friendly AI Assistant Gimini 2.5 Pro
</p>
