import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QWidget, QStyleOption, QStyle, QScrollArea, QDesktopWidget, QShortcut, QSizePolicy
from PyQt5.QtCore import Qt, QRect, QSize, QPoint, pyqtSignal, pyqtSlot, QEvent, QMetaObject, Q_ARG
from PyQt5.QtGui import QPainter, QColor, QCursor, QKeySequence, QTextDocument
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import textwrap

import string
import os
import re
class CaptionerGUI(QMainWindow):
    mousePressPos = None
    mouseMovePos = None

    clearSignal = pyqtSignal()
    newLineSignal = pyqtSignal(str)
    zoomInSignal = pyqtSignal()
    zoomOutSignal = pyqtSignal()
    moveMonitorSignal = pyqtSignal()
    toggleTopSignal = pyqtSignal()
    transparencyAddSignal = pyqtSignal()
    transparencySubSignal = pyqtSignal()
    resizeWidthSignal = pyqtSignal(int)
    resizeHeightSignal = pyqtSignal(int)
    changeSettingsSignal = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.newLineSignal.connect(self.addNewLine)
        self.zoomInSignal.connect(self.zoomIn)
        self.zoomOutSignal.connect(self.zoomOut)
        self.moveMonitorSignal.connect(self.move_monitor)
        self.toggleTopSignal.connect(self.toggleTop)
        self.transparencyAddSignal.connect(self.transparencyAdd)
        self.transparencySubSignal.connect(self.transparencySub)
        self.resizeWidthSignal.connect(self.resizeWidth)
        self.resizeHeightSignal.connect(self.resizeHeight)
        self.changeSettingsSignal.connect(self.changeSettings)
        self.lines = []
        self.fontSize = 55
        self.alpha = 128
        self.lineLimit = 0
        self.textLimit = 50
        self.zoomFactor = 2
        self.transparencyFactor = 3
        self.monitor = 2
        self.windowHeight = 300 if self.monitor == 1 else 210
        self.windowWidthOffset = 300
        self.lastGeometry = QRect(0, 0, 0, 0)
        self.top = False
        self.scrolling = False
        self.previous_value = -1
        self.max_value = -1
        self.language = 'en'
        self.speech = None
        self.log = None
        self.recording_enabled = True
        self.initUI()

        # Check if required library for Japanese text processing is available
        self.japanese_processing_available = False
        try:
            import fugashi  # Japanese morphological analyzer
            import jaconv   # Japanese converter
            self.japanese_processing_available = True
            self.tagger = fugashi.Tagger()  # Initialize Japanese morphological analyzer
        except ImportError:
            print("Note: Japanese text processing requires 'fugashi' and 'jaconv' libraries.")
            print("Install with: pip install fugashi jaconv")

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # Set margins to zero
        layout.setSpacing(0)  # Set spacing to zero
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.caption_label = QLabel("Caption goes here")
        self.caption_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.caption_label.setWordWrap(True)
        self.caption_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.caption_label.setCursor(Qt.IBeamCursor)
        self.caption_label.setTextFormat(Qt.RichText)  # Enable HTML formatting for ruby tags

        self.scroll_area.setWidget(self.caption_label)
        layout.addWidget(self.scroll_area)

        self.styling()
        self.setCentralWidget(central_widget)

        self.setWindowTitle("Captioner")
        
        self.setup_geometry()
        # Create shortcuts for the global hotkeys

        # Support + and = keys for zooming in (font size increase)
        # Standard shortcuts for increasing font size
        plus_shortcut = QShortcut(QKeySequence(Qt.Key_Plus), self)
        plus_shortcut.activated.connect(self.zoomIn)

        equal_shortcut = QShortcut(QKeySequence(Qt.Key_Equal), self)
        equal_shortcut.activated.connect(self.zoomIn)

        # Use different shortcuts for window resizing to avoid conflicts
        # Keep original Shift shortcuts for window resizing
        shift_equals_shortcut = QShortcut(QKeySequence("Shift+="), self)
        shift_equals_shortcut.activated.connect(lambda: self.resizeWidth(50))

        shift_underscore_shortcut = QShortcut(QKeySequence("Shift+_"), self)
        shift_underscore_shortcut.activated.connect(lambda: self.resizeWidth(-50))

        ctrl_up_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Up), self)
        ctrl_up_shortcut.activated.connect(lambda: self.resizeHeight(50))

        ctrl_down_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Down), self)
        ctrl_down_shortcut.activated.connect(lambda: self.resizeHeight(-50))

        # Support - key for zooming out (font size decrease)
        minus_shortcut = QShortcut(QKeySequence(Qt.Key_Minus), self)
        minus_shortcut.activated.connect(self.zoomOut)

        top_shortcut = QShortcut(QKeySequence(Qt.Key_Home), self)
        top_shortcut.activated.connect(self.toTop)

        bottom_shortcut = QShortcut(QKeySequence(Qt.Key_End), self)
        bottom_shortcut.activated.connect(self.toBottom)
        
        # 9 to increase transparency (make more see-through), 0 to decrease transparency (make less see-through/more opaque)
        transparency_9_shortcut = QShortcut(QKeySequence(Qt.Key_9), self)
        transparency_9_shortcut.activated.connect(self.transparencySub)  # 9 to make more transparent (decrease alpha)

        transparency_0_shortcut = QShortcut(QKeySequence(Qt.Key_0), self)
        transparency_0_shortcut.activated.connect(self.transparencyAdd)  # 0 to make less transparent (increase alpha)

        clear_shortcut = QShortcut(QKeySequence(Qt.Key_X), self)
        clear_shortcut.activated.connect(self.clearEmit)

        # Arrow keys to move window position
        left_arrow_shortcut = QShortcut(QKeySequence(Qt.ALT + Qt.Key_Left), self)
        left_arrow_shortcut.activated.connect(lambda: self.moveWindow(-10, 0))

        right_arrow_shortcut = QShortcut(QKeySequence(Qt.ALT + Qt.Key_Right), self)
        right_arrow_shortcut.activated.connect(lambda: self.moveWindow(10, 0))

        up_arrow_shortcut = QShortcut(QKeySequence(Qt.ALT + Qt.Key_Up), self)
        up_arrow_shortcut.activated.connect(lambda: self.moveWindow(0, -10))

        down_arrow_shortcut = QShortcut(QKeySequence(Qt.ALT + Qt.Key_Down), self)
        down_arrow_shortcut.activated.connect(lambda: self.moveWindow(0, 10))
        
        top_shortcut = QShortcut(QKeySequence(Qt.Key_B), self)
        top_shortcut.activated.connect(self.toggleTop)

        move_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        move_shortcut.activated.connect(self.move_monitor)

        # T key to change model, language, and minimum speech time
        t_shortcut = QShortcut(QKeySequence(Qt.Key_T), self)
        t_shortcut.activated.connect(self.changeSettings)
        
        
        # Setup fullscreen shortcut
        fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key_F), self)
        fullscreen_shortcut.activated.connect(self.fullscreen)

        # Ctrl+W to quit the application (app-only shortcut)
        quit_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_W), self)
        quit_shortcut.activated.connect(self.end)

        fullwidth_shortcut = QShortcut(QKeySequence(Qt.Key_W), self)
        fullwidth_shortcut.activated.connect(self.fullwidth)
        fullheight_shortcut = QShortcut(QKeySequence(Qt.Key_H), self)
        fullheight_shortcut.activated.connect(self.fullheight)
        
        self.scroll_area.verticalScrollBar().setVisible(False)
        self.previous_value = self.scroll_area.verticalScrollBar().value()
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.new_scroll)
        QApplication.instance().installEventFilter(self)

    def showEvent(self, event):
        super().showEvent(event)
        # Initialize the lastGeometry when the window is first shown
        if self.lastGeometry.width() <= 0:
            self.lastGeometry = self.geometry()

    def resizeEvent(self, event):
        # Handle resize events to maintain proper state
        if not self.isFullScreen():
            # Only save geometry if not in fullscreen mode
            self.lastGeometry = self.geometry()
        super().resizeEvent(event)

    def fullscreen(self):
        # Get the current screen geometry
        desktop = QDesktopWidget()
        screen_geometry = desktop.screenGeometry(self.monitor - 1)
        if not self.isFullScreen():
            # Save current window geometry before going fullscreen
            self.lastGeometry = self.geometry()
            # Set the window to cover the entire screen
            self.showFullScreen()
        else:
            # Restore to last geometry when exiting fullscreen
            if self.lastGeometry.width() > 0:
                # Make sure we're not showing fullscreen anymore
                self.showNormal()  # Exit fullscreen mode first
                self.setGeometry(self.lastGeometry)
                self.lastGeometry = QRect(0, 0, 0, 0)
            else:
                # Fallback to default geometry if no previous geometry was saved
                self.showNormal()  # Exit fullscreen mode first
                self.setup_geometry()
        self.write(f"Fullscreen toggle - Current state: {self.isFullScreen()}")
    def fullwidth(self):
        # Get the current screen geometry
        desktop = QDesktopWidget()
        screen_geometry = desktop.screenGeometry(self.monitor - 1)
        if self.lastGeometry.width() <= 0:
            self.lastGeometry = self.geometry()
            # Set the window to cover the entire screen
            self.setGeometry(screen_geometry.left(), self.y(), screen_geometry.width(), self.height())
        else:
            self.setGeometry(self.lastGeometry)
            self.lastGeometry = QRect(0, 0, 0, 0)
        
        # Set the window to full width and maintain its current height
        self.write(f"Set to full width: {screen_geometry.width()} at position {self.y()}")

    def fullheight(self):
        # Get the current screen geometry
        desktop = QDesktopWidget()
        screen_geometry = desktop.screenGeometry(self.monitor - 1)
        if self.lastGeometry.width() <= 0:
            self.lastGeometry = self.geometry()       
            # Set the window to full height and maintain its current width
            self.setGeometry(self.x(), screen_geometry.top(), self.width(), screen_geometry.height())
        else:
            self.setGeometry(self.lastGeometry)
            self.lastGeometry = QRect(0, 0, 0, 0)
        self.write(f"Set to full height: {screen_geometry.height()} at position {screen_geometry.top()}")
    def setup_geometry(self, fullscreen = False):
        desktop = QDesktopWidget()
        num_screens = desktop.screenCount()

        def get_screen_geometry(monitor_index, fullscreen = False):
            if monitor_index < num_screens:
                return desktop.screenGeometry(monitor_index)
            else:
                return desktop.screenGeometry(desktop.primaryScreen())

        screen_geometry = get_screen_geometry(self.monitor - 1)
        self.windowWidth = screen_geometry.width() - self.windowWidthOffset

        if fullscreen:
            windowHeight = screen_geometry.height()
            windowWidth = screen_geometry.width()
            self.setGeometry(screen_geometry.left(), screen_geometry.top(), windowWidth, windowHeight)
        else:
            if self.top:
                self.setGeometry(screen_geometry.left(), screen_geometry.top(), self.windowWidth, self.windowHeight)
            else:
                self.setGeometry(screen_geometry.left(), screen_geometry.bottom() - self.windowHeight, self.windowWidth, self.windowHeight)
    def move_monitor(self):
        pos = self.pos()
        if pos.x() < 0:
            self.monitor = 1
        else:
            self.monitor = 2
        self.setup_geometry()
        self.setup_geometry()
    def toggleTop(self):
        self.top = not self.top
        pos = self.pos()
        #print(pos.x(),'\n')
        if pos.x() < 0:
            self.monitor = 2
        else:
            self.monitor = 1
        self.setup_geometry()
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key_sequence = QKeySequence(event.modifiers() | event.key())
            if key_sequence == QKeySequence(Qt.CTRL | Qt.ALT | Qt.Key_Minus):
                self.zoomOut()
            elif key_sequence == QKeySequence(Qt.CTRL | Qt.ALT | Qt.Key_Equal):
                self.zoomIn()
            elif key_sequence == QKeySequence(Qt.CTRL | Qt.ALT | Qt.Key_X):
                self.clear()
            elif key_sequence == QKeySequence(Qt.CTRL | Qt.ALT | Qt.Key_Q):
                self.end()
        return super().eventFilter(obj, event)
    def zoom(self, factor):
        if not self or factor == 0 or self.fontSize + factor <= 0:
            return
        self.fontSize += factor
        self.styling()

    def moveWindow(self, dx, dy):
        """Move the window by dx, dy pixels"""
        current_pos = self.pos()
        new_x = current_pos.x() + dx
        new_y = current_pos.y() + dy
        self.move(new_x, new_y)
    def zoomIn(self):
        self.zoom(self.zoomFactor)
    def zoomOut(self):
        self.zoom(-self.zoomFactor)

    def changeSettings(self):
        """Prompt for model, language, and minimum speech time changes"""
        if not self.speech:
            return

        # Import dialog modules if not already available
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QDoubleSpinBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Change Settings")
        dialog.setModal(True)

        layout = QVBoxLayout()

        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        model_combo = QComboBox()
        model_combo.addItems([
            "tiny", "base", "small", "medium", "large", "large-v2", "large-v3",
            "tiny.en", "base.en", "small.en", "medium.en"
        ])
        # Set current model
        current_model_index = model_combo.findText(self.speech.args['model_name'])
        if current_model_index >= 0:
            model_combo.setCurrentIndex(current_model_index)
        model_layout.addWidget(model_combo)
        layout.addLayout(model_layout)

        # Language input
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        lang_input = QLineEdit()
        lang_input.setText(self.speech.args.get('lang', '') or '')
        lang_layout.addWidget(lang_input)
        layout.addLayout(lang_layout)

        # Minimum speech time
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Min Speech Time:"))
        time_spinbox = QDoubleSpinBox()
        time_spinbox.setRange(0.1, 30.0)
        time_spinbox.setSingleStep(0.1)
        time_spinbox.setValue(self.speech.recording_scale)  # Using recording_scale as the time factor
        time_layout.addWidget(time_spinbox)
        layout.addLayout(time_layout)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            # Update speech settings
            new_model = model_combo.currentText()
            new_lang = lang_input.text() or None
            new_time_scale = time_spinbox.value()

            # Update the speech object
            self.speech.args['model_name'] = new_model
            self.speech.args['lang'] = new_lang
            self.speech.recording_scale = new_time_scale

            # Restart the audio recorder with new settings
            self.restartAudioRecorder(new_model, new_lang, new_time_scale)

    def restartAudioRecorder(self, model_name, language, time_scale):
        """Restart the audio recorder with new settings"""
        if not self.speech:
            return

        try:
            # Stop the current recorder safely
            self.speech.stop = True
            if self.speech.recorder:
                try:
                    self.speech.recorder.stop()
                except:
                    pass  # Ignore errors during stop
                self.speech.recorder = None

            # Update the settings
            self.speech.args['model_name'] = model_name
            self.speech.args['lang'] = language
            self.speech.recording_scale = time_scale

            # Update the minimum length calculation
            self.speech.min_length = self.speech.get_min_length_of_recording()

            # Restart the transcription thread with new settings
            import threading
            self.speech.stop = False
            transcription_thread = threading.Thread(target=self.speech.main_program)
            transcription_thread.daemon = True
            transcription_thread.start()

        except Exception as e:
            print(f"Error restarting audio recorder: {e}")

    def resizeWidth(self, factor):
        """Change window width"""
        if factor == 0:
            return
        current_width = self.width()
        new_width = current_width + factor
        if new_width > 0:  # Make sure width is positive
            self.resize(new_width, self.height())

    def resizeHeight(self, factor):
        """Change window height"""
        if factor == 0:
            return
        current_height = self.height()
        new_height = current_height + factor
        if new_height > 0:  # Make sure height is positive
            self.resize(self.width(), new_height)
    def transparency(self, factor):
        if factor == 0 or self.alpha + factor <= 0 or self.alpha + factor > 255:
            return
        self.alpha += factor
        self.styling()
    def transparencyAdd(self):
        self.transparency(self.transparencyFactor)
    def transparencySub(self):
        self.transparency(-self.transparencyFactor)
    def toBottom(self):
        max_value = self.scroll_area.verticalScrollBar().maximum()
        current_value = self.scroll_area.verticalScrollBar().value()
        self.write('toBottom ', self.previous_value, current_value, max_value)
        self.scroll_area.verticalScrollBar().setValue(max_value)
        self.previous_value = max_value
    def toTop(self):
        """
        Scroll to the top of the text area.
        """
        self.write("toTop")
        self.scroll_area.verticalScrollBar().setValue(0)
    def end(self):
        #print(self.speech)
        self.write("End")
        if self.log:
            try:
                self.log.close_log_file()
            except:
                pass
        if self.speech:
            # Call the speech cleanup method to ensure proper cleanup
            try:
                self.speech.cleanup()
            except:
                pass
            # Also set the stop flag directly as backup
            self.speech.stop = True
        # Close and delete all UI elements to ensure cleanup
        try:
            self.close()  # Close the main window
            self.deleteLater()  # Schedule for deletion
        except:
            pass
        # Quit the application
        QApplication.quit()

        # Schedule a forceful termination if the application doesn't exit within 2 seconds
        import sys
        import os
        import signal
        import threading

        def force_quit():
            import time
            time.sleep(2)  # Wait 2 seconds
            # If we reach this point, the app didn't exit gracefully
            os.kill(os.getpid(), signal.SIGKILL)

        # Start the force quit in a separate daemon thread so it doesn't prevent exit
        force_thread = threading.Thread(target=force_quit, daemon=True)
        force_thread.start()

        # Exit the Python interpreter to allow graceful termination
        sys.exit(0)
        """if os.name == 'nt':
            os._exit(1)
        else:
            os.kill(os.getpid(), signal.SIGINT)"""
    @pyqtSlot()
    def clearEmit(self):
        self.clearSignal.emit()
    @pyqtSlot()
    def clear(self):
        if self:
            self.lines = []
            self.caption_label.setText("")
            self.log.write_log('-- Clear --')
            #self.clearCaption()
    # Show the scrollbar when the content is larger than the viewport
    def scrollbar_visibility(self):
        if self.scroll_area.verticalScrollBar().isVisible():
            self.scroll_area.verticalScrollBar().setVisible(True)
        else:
            self.scroll_area.verticalScrollBar().setVisible(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mousePressPos = event.globalPos() - self.pos()
            self.mouseMovePos = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        self.move(event.globalPos() - self.mouseMovePos)
        self.mouseMovePos = event.globalPos() - self.pos()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mousePressPos = None
            self.mouseMovePos = None
            event.accept()

    def wheelEvent(self, event):
        # Handle Ctrl+Scroll for font size
        if event.modifiers() == Qt.CTRL:
            # Get the angle delta (positive for up, negative for down)
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoomIn()
            else:
                self.zoomOut()
            event.accept()
        else:
            # Pass the event to the parent for normal scrolling
            super().wheelEvent(event)

    def styling(self):
        self.write("Style change ", self.fontSize, self.alpha)
        self.scroll_area.setStyleSheet(f"font-size: {self.fontSize}px; color: white; background-color: rgba(0, 0, 0, {self.alpha});")
        self.caption_label.setStyleSheet(f"background-color: rgba(0, 0, 0, {self.alpha});")

    @pyqtSlot(bool)
    def updateRecordingStatus(self, enabled):
        self.recording_enabled = enabled
        self.update()

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)

        if not self.recording_enabled:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor("red"))
            painter.setPen(Qt.NoPen)
            radius = 10
            margin = 5
            painter.drawEllipse(self.width() - radius * 2 - margin, margin, radius * 2, radius * 2)

    def editCaption(self, new_caption):
        self.caption_label.setText(new_caption)

    def clearCaption(self):
        self.caption_label.clear()

    @pyqtSlot()
    def call_adjust_size(self):
        self.caption_label.adjustSize()
        self.max_value = self.scroll_area.verticalScrollBar().maximum()
        self.scroll_area.verticalScrollBar().setValue(self.max_value)
    
    def normalize_text(self, text):
        # Normalize the text: lower case, strip spaces, and remove punctuation
        return text.lower().strip().translate(str.maketrans('', '', string.punctuation))

    def is_similar(self, new_text, existing_lines, threshold=0.8, recent_count=7):
        # Limit text length to prevent performance issues with large texts
        if len(new_text) > 100:  # Limit to first 100 characters for comparison
            new_text = new_text[:100]

        # Get the most recent lines
        recent_lines = existing_lines[-recent_count:]

        # Limit length of existing lines too
        limited_lines = []
        for line in recent_lines:
            if len(line) > 100:
                limited_lines.append(line[:100])
            else:
                limited_lines.append(line)

        # Only proceed if there are lines to compare
        if not limited_lines:
            return False

        try:
            vectorizer = TfidfVectorizer().fit_transform([new_text] + limited_lines)
            vectors = vectorizer.toarray()
            csim = cosine_similarity(vectors)
            return any(csim[0][i] > threshold for i in range(1, len(csim)))
        except:
            # If similarity checking fails, return False to allow text to be added
            return False
    
    @pyqtSlot(str)
    def addNewLine(self, text):
        if len(self.lines) > 0:
            # Normalize the incoming text
            normalized_text = self.normalize_text(text)
            # Create a list of normalized lines for similarity checking
            # Only check against a limited number of recent lines to avoid performance issues
            recent_lines = self.lines[-20:]  # Only check last 20 lines
            normalized_lines = [self.normalize_text(line) for line in recent_lines]

            # Check for similarity with existing lines
            if self.is_similar(normalized_text, normalized_lines):
                return

        # Process text for furigana if it's Japanese
        processed_text = self.process_text_with_furigana(text)

        # Handle text length limit and specific languages
        #if len(text) > self.textLimit and self.language not in ['zh-CN', 'zh-TW', 'ja', 'th', 'my', 'lo', 'km', 'bo', 'mn', 'mn-Mong', 'dz', 'aii']:
            # Split the text into multiple lines without splitting words
        #    lines = textwrap.wrap(text, width=self.textLimit, break_long_words=False)
        #    self.lines.extend(lines)
        #else:
        self.lines.append(processed_text)

        # Ensure the number of lines does not exceed the limit
        if self.lineLimit > 0:
            while len(self.lines) > self.lineLimit:
                del self.lines[0]

        # Use setTextFormat to support HTML content with ruby tags
        self.caption_label.setText('\n'.join(self.lines))
        # Write log in a separate thread to avoid blocking the UI
        if self.log:
            QMetaObject.invokeMethod(self, "_write_log", Qt.QueuedConnection,
                                    Q_ARG(str, text))
        self.update_scroll_position()

    def contains_japanese(self, text):
        """
        Checks if the text contains Japanese characters (Hiragana, Katakana, Kanji).
        """
        # Regular expression to match Japanese characters
        japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]')
        return bool(japanese_pattern.search(text))

    def add_furigana_ruby_html(self, text):
        """
        Adds furigana to Japanese text using HTML ruby tags or fallback format.
        """
        if not self.japanese_processing_available:
            return text

        try:
            # Use the tagger to analyze the text
            result = self.tagger.parse(text)
            processed_parts = []

            for line in result.split("\n"):
                if line.strip() == "EOS" or line.strip() == "":
                    continue

                parts = line.split("\t")
                if len(parts) < 2:
                    continue

                surface = parts[0]  # The surface form (what you see)
                feature_str = parts[1]  # The feature string

                # Parse the feature string
                features = feature_str.split(",")

                # Extract the reading (yomi) - typically in position 7 for UniDic
                # For different dictionaries, it might be different positions
                if len(features) > 7 and features[7] and features[7] != "*" and features[7] != surface:
                    # Get the reading
                    reading = features[7]

                    # Check if the surface form contains kanji
                    if self.contains_japanese(surface) and any('\u4e00' <= c <= '\u9fff' for c in surface):
                        # Qt's HTML support for ruby tags might be limited
                        # Using a more compatible format that shows furigana clearly
                        processed_parts.append(f'{surface}({reading})')
                        # Keep HTML ruby as comment for when better support is available
                        # processed_parts.append(f'<ruby>{surface}<rt>{reading}</rt></ruby>')
                    else:
                        processed_parts.append(surface)
                else:
                    # No reading available, just add the surface
                    processed_parts.append(surface)

            # Join the processed parts
            return "".join(processed_parts) if processed_parts else text
        except Exception as e:
            # If processing fails, return the original text
            print(f"Furigana processing error: {e}")
            return text

    def process_text_with_furigana(self, text):
        """
        Process text to add furigana if it contains Japanese characters.
        """
        if self.contains_japanese(text):
            return self.add_furigana_ruby_html(text)
        return text

    @pyqtSlot(str)
    def _write_log(self, text):
        """Thread-safe method to write log"""
        if self.log:
            self.log.write_log(f'{text}')
    def new_scroll(self) -> None:
        current_value = self.scroll_area.verticalScrollBar().value()
        max_value = self.scroll_area.verticalScrollBar().maximum()
        if current_value == max_value:
            self.previous_value = max_value
    def update_scroll_position(self):
        self.scrolling = True
        caption_height = self.caption_label.height()
        viewport_height = self.scroll_area.viewport().height()
        # Check if the caption label height exceeds the viewport height
        
        if caption_height > viewport_height:
            # Get the current scroll bar value and the maximum value
            current_value = self.scroll_area.verticalScrollBar().value()
            max_value = self.scroll_area.verticalScrollBar().maximum()
            # If the scroll bar is already at the bottom, update the value to the maximum
            if current_value == max_value:
                QMetaObject.invokeMethod(self, "call_adjust_size", Qt.QueuedConnection)
                self.previous_value = self.max_value
            else:
                # Check if the scroll position has changed
                if current_value == self.previous_value or self.previous_value < 0:
                    # Scroll to the bottom of the content
                    QMetaObject.invokeMethod(self, "call_adjust_size", Qt.QueuedConnection)
                    
                    self.previous_value = self.max_value
        self.scrolling = False
    def run(self):
        sys.exit(self.app.exec_())
    def write(self, *kwargs):
        #print(*kwargs)
        if self.log is not None and self.log.test is not None:
            self.log.write_log(' '.join(map(str, kwargs)), self.log.test)

def initialize():
    app = QApplication(sys.argv)
    gui = CaptionerGUI()
    gui.show()
    gui.clearSignal.connect(gui.clear)
    gui.app = app
    return gui