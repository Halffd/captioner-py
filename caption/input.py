import sys
import os
from pynput import keyboard

class Input:
    def __init__(self, args):
        self.args = args
        self.gui = None #gui.CaptionerGUI()  # Initialize GUI as None
        # Set up hotkeys
        self.listener = keyboard.GlobalHotKeys({
            '<alt>+<backspace>': self.quit,
            '<ctrl>+<shift>+<backspace>': self.reload,
            '<ctrl>+<up>': self.increase_font_size,
            '<ctrl>+<down>': self.decrease_font_size,
            '<ctrl>+<alt>+x': self.clear_text,
            '<ctrl>+<shift>+<left>': self.move_monitor,
            '<ctrl>+<shift>+<down>': self.toggle_top,
            '<ctrl>+<page_up>': self.increase_transparency,
            '<ctrl>+<page_down>': self.decrease_transparency
        })
        self.listener.start()

    def reload(self):
        """Reload the application."""
        os.execv(sys.executable, ['py'] + self.args)

    def quit(self):
        """Quit the application."""
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
# Example usage
if __name__ == "__main__":
    input_handler = Input(sys.argv)