import sys
import os
from pynput import keyboard

class Input:
    def __init__(self, args):
        self.args = args
        self.gui = None #gui.CaptionerGUI()  # Initialize GUI as None
        # Set up global hotkeys (excluding Ctrl+W)
        self.listener = keyboard.GlobalHotKeys({
            '<ctrl>+<enter>': self.toggle_recording,
            '<ctrl>+<shift>+<backspace>': self.reload,
            '<ctrl>+<shift>+=': self.increase_font_size,
            '<ctrl>+<shift>+-': self.decrease_font_size,
            '<ctrl>+<alt>+x': self.clear_text,
#            '<ctrl>+<shift>+<left>': self.move_monitor,
#            '<ctrl>+<shift>+<down>': self.toggle_top,
            '<ctrl>+<page_up>': self.increase_transparency,
            '<ctrl>+<page_down>': self.decrease_transparency,
            # Add new shortcuts for window resize and settings
            '<ctrl>+<alt>+<up>': self.increase_window_height,
            '<ctrl>+<alt>+<down>': self.decrease_window_height,
            '<ctrl>+<alt>+<left>': self.decrease_window_width,
            '<ctrl>+<alt>+<right>': self.increase_window_width
 #           '<shift>+<ctrl>+<up>': self.prompt_settings,
#            '<shift>+<ctrl>+<down>': self.prompt_settings
        })
        self.listener.start()

    def toggle_recording(self):
        if self.gui and self.gui.speech:
            self.gui.speech.toggle_recording()

    def reload(self):
        """Reload the application."""
        os.execv(sys.executable, ['py'] + self.args)

    def quit(self):
        """Quit the application."""
        # This method is still available for other functions to call
        # but Ctrl+W will be handled separately as an app-only shortcut
        if self.gui:
            self.gui.end()
        else:
            sys.exit()  # Exit if no GUI is provided

    def increase_font_size(self):
        """Increase the font size."""
        if self.gui: self.gui.zoomInSignal.emit()
    def decrease_font_size(self):
        """Decrease the font size."""
        if self.gui: self.gui.zoomOutSignal.emit()

    def clear_text(self):
        """Clear the text."""
        if self.gui: self.gui.clearEmit()

    def move_monitor(self):
        if self.gui: self.gui.moveMonitorSignal.emit()

    def toggle_top(self):
        if self.gui: self.gui.toggleTopSignal.emit()

    def increase_transparency(self):
        """Increase transparency."""
        if self.gui: self.gui.transparencyAddSignal.emit()
    def decrease_transparency(self):
        """Decrease transparency."""
        if self.gui: self.gui.transparencySubSignal.emit()

    def increase_window_width(self):
        """Increase window width."""
        if self.gui: self.gui.resizeWidthSignal.emit(50)

    def decrease_window_width(self):
        """Decrease window width."""
        if self.gui: self.gui.resizeWidthSignal.emit(-50)

    def increase_window_height(self):
        """Increase window height."""
        if self.gui: self.gui.resizeHeightSignal.emit(50)

    def decrease_window_height(self):
        """Decrease window height."""
        if self.gui: self.gui.resizeHeightSignal.emit(-50)

    def prompt_settings(self):
        """Prompt for settings changes."""
        if self.gui: self.gui.changeSettingsSignal.emit()

# Example usage
if __name__ == "__main__":
    input_handler = Input(sys.argv)
