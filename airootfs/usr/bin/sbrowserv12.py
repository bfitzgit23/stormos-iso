#!/usr/bin/env python3
import sys
import os

# =============================================
# MUST BE SET BEFORE ANY QT IMPORTS
# =============================================
os.environ["QT_VAAPI_ENABLED"] = "1"
os.environ["LIBVA_DRIVER_NAME"] = "iHD"  # Intel: 'iHD' | AMD: 'radeonsi' | Nvidia: 'nvidia'
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--enable-features=Widevine,PlatformEncryptedDolbyVision "
    "--disable-features=UseChromeOSDirectVideoDecoder "
    "--enable-ac3-eac3-audio "
    "--enable-mse-mp2t-streaming "
    "--no-sandbox "
    "--widevine-cdm-path=/usr/lib/chromium/WidevineCdm"
)
import os
import sys
import json
import time
import sqlite3
import platform
from datetime import datetime
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWebEngineCore import *  # Try this for all WebEngineCore components
import re
import json
import logging
import subprocess
import time
import re
import logging
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import shutil
import sqlite3
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import (
    QUrl, Qt, QTimer, pyqtSignal, QObject, QRect, QThread, QSize,
    QCoreApplication, QStandardPaths, QEvent # Added QStandardPaths for better default download folder
)
from PyQt5.QtGui import (
    QIcon, QFontMetrics, QPalette, QColor, QKeySequence, QPainter,
    QGuiApplication, QDesktopServices, QCursor
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QWidget, QLabel, QProgressBar,
    QToolBar, QAction, QDialog, QListWidget, QListWidgetItem,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QInputDialog, QMenu,
    QDialogButtonBox, QToolButton, QTabBar, QTextEdit, QSpacerItem,
    QStatusBar # Explicitly import QStatusBar for clarity
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile, QWebEngineDownloadItem, QWebEngineSettings
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtWidgets import QDockWidget
from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtWidgets import QMenu, QFileDialog
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import QTimer
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QProcess
from PyQt5.QtWidgets import QAction
from PyQt5.QtCore import QStandardPaths
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import (
    QGroupBox,  # Add this
    QVBoxLayout,  # Probably already there
    QRadioButton,  # Add this
    QDialog,  # Probably already there
    QFileDialog,  # Probably already there
    QMessageBox  # Probably already there
)
from PyQt5.QtWidgets import QLayout  # Add this import
from PyQt5.QtCore import QUrl, Qt, QTimer, pyqtSignal, QObject, QRect, QThread, QSize,QCoreApplication, QStandardPaths, QEvent, QDateTime, QPoint  # Added QDateTime here

# ====================== CONSTANTS ======================
DEFAULT_HOME_PAGE = "https://www.google.com"
DOWNLOAD_DIR = os.path.expanduser("~/Downloads")
CONFIG_DIR = os.path.expanduser("~/.config/storm_browser")
BOOKMARKS_FILE = os.path.join(CONFIG_DIR, "bookmarks.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.json")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
DRM_ENABLED = True  # Enable Widevine DRM support
HLS_ENABLED = True  # Enable HLS streaming support
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# ====================== UTILITIES ======================
def ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

def load_json_file(file_path, default=None):
    if default is None:
        default = {}
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json_file(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def format_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

def format_time(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds//60)}m {int(seconds%60)}s"
    else:
        return f"{int(seconds//3600)}h {int((seconds%3600)//60)}m"

# ====================== BOOKMARK IMPORT ======================
class BookmarkImporter:
    @staticmethod
    def get_browser_bookmarks(browser):
        paths = {
            "chrome": {
                "linux": "~/.config/google-chrome/Default/Bookmarks",
                "windows": os.path.expanduser("~/AppData/Local/Google/Chrome/User Data/Default/Bookmarks"),
                "darwin": "~/Library/Application Support/Google/Chrome/Default/Bookmarks"
            },
            "firefox": {
                "linux": "~/.mozilla/firefox/*.default-release/places.sqlite",
                "windows": os.path.expanduser("~/AppData/Roaming/Mozilla/Firefox/Profiles/*.default-release/places.sqlite"),
                "darwin": "~/Library/Application Support/Firefox/Profiles/*.default-release/places.sqlite"
            }
        }
        
        system = platform.system().lower()
        if browser == "chrome":
            path = os.path.expanduser(paths["chrome"].get(system, ""))
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return BookmarkImporter._parse_chrome_bookmarks(data)
        
        elif browser == "firefox":
            import glob
            path_pattern = os.path.expanduser(paths["firefox"].get(system, ""))
            matches = glob.glob(path_pattern)
            if matches:
                return BookmarkImporter._parse_firefox_bookmarks(matches[0])
        
        return []

    @staticmethod
    def _parse_chrome_bookmarks(data, folder="Imported Chrome"):
        bookmarks = []
        if "roots" in data:
            for root in data["roots"].values():
                if "children" in root:
                    for child in root["children"]:
                        if child["type"] == "url":
                            bookmarks.append({
                                "url": child["url"],
                                "title": child["name"],
                                "folder": folder,
                                "date": datetime.now().isoformat()
                            })
        return bookmarks

    @staticmethod
    def _parse_firefox_bookmarks(db_path):
        bookmarks = []
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT moz_bookmarks.title, moz_places.url 
                FROM moz_bookmarks 
                JOIN moz_places ON moz_bookmarks.fk = moz_places.id 
                WHERE moz_bookmarks.type = 1
            """)
            for title, url in cursor.fetchall():
                bookmarks.append({
                    "url": url,
                    "title": title or url,
                    "folder": "Imported Firefox",
                    "date": datetime.now().isoformat()
                })
            conn.close()
        except sqlite3.Error:
            pass
        return bookmarks

# ====================== DOWNLOAD MANAGER ======================
class DownloadManager(QObject):
    download_progress = pyqtSignal(str, int, int, str, str)  # filename, received, total, speed, eta
    download_finished = pyqtSignal(str, bool, str)  # path, success, filename
    download_started = pyqtSignal(str, str)  # filename, size

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_downloads = {}
        self.completed_downloads = []
        ensure_config_dir()

    def handle_download(self, download_item):
        filename = download_item.suggestedFileName() or f"download_{int(time.time())}"
        path = self._get_unique_path(filename)
        download_item.setPath(path)
        
        # Store download info
        download_id = int(time.time() * 1000)
        self.active_downloads[download_id] = {
            'item': download_item,
            'filename': filename,
            'path': path,
            'start_time': time.time(),
            'last_update': time.time(),
            'last_bytes': 0,
            'speed': 0
        }
        
        self.download_started.emit(filename, "0 B")
        
        download_item.accept()
        download_item.downloadProgress.connect(
            lambda recv, total: self._on_download_progress(download_id, recv, total)
        )
        download_item.finished.connect(
            lambda: self._on_download_finished(download_id)
        )

    def handle_forced_download_url(self, url, filename=None):
        if not filename:
            filename = os.path.basename(url.path()) or f"download_{int(time.time())}"
        path = self._get_unique_path(filename)
        
        # Store download info
        download_id = int(time.time() * 1000)
        self.active_downloads[download_id] = {
            'filename': filename,
            'path': path,
            'start_time': time.time(),
            'last_update': time.time(),
            'last_bytes': 0,
            'speed': 0,
            'received': 0,
            'total': 0
        }
        
        self.download_started.emit(filename, "0 B")
        
        manager = QNetworkAccessManager()
        request = QNetworkRequest(QUrl(url))
        reply = manager.get(request)

        def _on_reply_progress(recv, total):
            self._on_download_progress(download_id, recv, total)

        def _on_reply_finished():
            if reply.error() == QNetworkReply.NoError:
                with open(path, "wb") as f:
                    f.write(reply.readAll().data())
                self._on_download_finished(download_id, True)
            else:
                self._on_download_finished(download_id, False)
            reply.deleteLater()

        reply.downloadProgress.connect(_on_reply_progress)
        reply.finished.connect(_on_reply_finished)

    def _get_unique_path(self, filename):
        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)
        
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(DOWNLOAD_DIR, filename)):
            filename = f"{base}({counter}){ext}"
            counter += 1
            
        return os.path.join(DOWNLOAD_DIR, filename)

    def _on_download_progress(self, download_id, received, total):
        if download_id not in self.active_downloads:
            return
            
        download = self.active_downloads[download_id]
        now = time.time()
        time_elapsed = now - download['last_update']
        
        # Calculate download speed
        if time_elapsed > 0:
            bytes_diff = received - download['last_bytes']
            download['speed'] = bytes_diff / time_elapsed  # bytes per second
            
        # Update download info
        download['last_update'] = now
        download['last_bytes'] = received
        download['received'] = received
        download['total'] = total
        
        # Calculate ETA
        remaining_bytes = total - received
        if download['speed'] > 0:
            eta = remaining_bytes / download['speed']
        else:
            eta = 0
            
        # Emit progress signal
        self.download_progress.emit(
            download['filename'],
            received,
            total,
            f"{format_size(download['speed'])}/s",
            format_time(eta) if eta > 0 else "Calculating..."
        )

    def _on_download_finished(self, download_id, success=None):
        if download_id not in self.active_downloads:
            return
            
        download = self.active_downloads.pop(download_id)
        
        if success is None:
            if hasattr(download['item'], 'state'):
                success = download['item'].state() == QWebEngineDownloadItem.DownloadCompleted
            else:
                success = True
        
        self.completed_downloads.append(download)
        self.download_finished.emit(download['path'], success, download['filename'])

# ====================== BOOKMARK MANAGER ======================
class BookmarkManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        ensure_config_dir()
        self.bookmarks = load_json_file(BOOKMARKS_FILE, {"folders": {"Main": []}})

    def add_bookmark(self, url, title, folder="Main"):
        if folder not in self.bookmarks["folders"]:
            self.bookmarks["folders"][folder] = []
        self.bookmarks["folders"][folder].append({
            "url": url,
            "title": title,
            "date": datetime.now().isoformat()
        })
        save_json_file(BOOKMARKS_FILE, self.bookmarks)

    def remove_bookmark(self, url, folder="Main"):
        if folder in self.bookmarks["folders"]:
            self.bookmarks["folders"][folder] = [
                b for b in self.bookmarks["folders"][folder] 
                if b["url"] != url
            ]
            save_json_file(BOOKMARKS_FILE, self.bookmarks)

    def get_bookmarks(self, folder="Main"):
        return self.bookmarks["folders"].get(folder, [])

    def get_all_bookmarks(self):
        """Get all bookmarks across all folders."""
        all_bookmarks = []
        for folder, bookmarks in self.bookmarks["folders"].items():
            for bookmark in bookmarks:
                bookmark_copy = bookmark.copy()
                bookmark_copy["folder"] = folder
                all_bookmarks.append(bookmark_copy)
        return all_bookmarks

    def import_browser_bookmarks(self, browser):
        imported = BookmarkImporter.get_browser_bookmarks(browser)
        for bookmark in imported:
            self.add_bookmark(bookmark["url"], bookmark["title"], bookmark.get("folder", "Imported"))
        return len(imported)

# ====================== HISTORY MANAGER ======================
class HistoryManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        ensure_config_dir()
        self.history = load_json_file(HISTORY_FILE, {"entries": []})

    def add_history_entry(self, url, title):
        self.history["entries"].append({
            "url": url,
            "title": title,
            "date": datetime.now().isoformat(),
            "visit_count": 1
        })
        save_json_file(HISTORY_FILE, self.history)

    def clear_history(self):
        self.history["entries"] = []
        save_json_file(HISTORY_FILE, self.history)

    def get_history(self, limit=100, search_query=None):
        history = sorted(
            self.history["entries"], 
            key=lambda x: x["date"], 
            reverse=True
        )
        
        if search_query:
            search_query = search_query.lower()
            history = [
                entry for entry in history
                if (search_query in entry["title"].lower() or 
                    search_query in entry["url"].lower())
            ]
        
        return history[:limit]

# ====================== SETTINGS MANAGER ======================
class SettingsManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        ensure_config_dir()
        
        # Default settings with dark mode enabled
        self.default_settings = {
            "home_page": DEFAULT_HOME_PAGE,
            "search_engine": "https://www.google.com/search?q={}",
            "download_dir": DOWNLOAD_DIR,
            "dark_mode": True,
            "dark_theme": {
                "base_color": "#2d2d2d",
                "highlight_color": "#3daee9",
                "text_color": "#f0f0f0",
                "button_color": "#3a3a3a",
                "disabled_color": "#404040",
                "window_color": "#252525",
                "tooltip_color": "#353535"
            },
            "ad_blocker": True,
            "javascript_enabled": True,
            "auto_load_images": True,
            "drm_enabled": DRM_ENABLED,
            "hls_enabled": HLS_ENABLED,
            "user_agent": USER_AGENT,
            "shortcuts": {
                "new_tab": "Ctrl+T",
                "close_tab": "Ctrl+W",
                "next_tab": "Ctrl+Tab",
                "prev_tab": "Ctrl+Shift+Tab",
                "reload": "F5",
                "bookmarks": "Ctrl+B",
                "history": "Ctrl+H",
                "downloads": "Ctrl+J",
                "dev_tools": "F12",
                "bookmark_search": "Ctrl+K"
            }
        }
        
        # Load settings
        self.settings = load_json_file(SETTINGS_FILE, self.default_settings)
        
        # Validate and repair settings
        self.validate_settings()

    def validate_settings(self):
        """Ensure all settings exist and are valid."""
        needs_save = False
        
        # Check top-level settings
        for key, default_value in self.default_settings.items():
            if key not in self.settings:
                self.settings[key] = default_value
                needs_save = True
                
        # Check dark theme colors
        if "dark_theme" not in self.settings:
            self.settings["dark_theme"] = self.default_settings["dark_theme"]
            needs_save = True
        else:
            for color_key, default_value in self.default_settings["dark_theme"].items():
                if color_key not in self.settings["dark_theme"]:
                    self.settings["dark_theme"][color_key] = default_value
                    needs_save = True
        
        # Check shortcuts
        if "shortcuts" not in self.settings:
            self.settings["shortcuts"] = self.default_settings["shortcuts"]
            needs_save = True
        else:
            for shortcut, default_value in self.default_settings["shortcuts"].items():
                if shortcut not in self.settings["shortcuts"]:
                    self.settings["shortcuts"][shortcut] = default_value
                    needs_save = True
        
        if needs_save:
            self.save_settings()

    def save_settings(self):
        """Save current settings to file."""
        save_json_file(SETTINGS_FILE, self.settings)

    def get(self, key, default=None):
        """Get a setting value."""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Set a setting value and save to disk."""
        self.settings[key] = value
        self.save_settings()

    def get_shortcut(self, action):
        """Get keyboard shortcut for an action."""
        try:
            return self.settings["shortcuts"].get(action, self.default_settings["shortcuts"].get(action, ""))
        except KeyError:
            return self.default_settings["shortcuts"].get(action, "")


    def close_tab(self, index):
        """Close a tab and aggressively ensure media playback is stopped."""
        # Get the browser instance from the tab
        tab_widget = self.tab_widget.widget(index)
        if tab_widget:
            browser = tab_widget.findChild(QWebEngineView)
            if browser:
                # Stop any media playback using JavaScript
                browser.page().runJavaScript("""
                    var mediaElements = document.querySelectorAll('audio, video');
                    mediaElements.forEach(function(media) {
                        media.pause();
                    });
                """)

                # Stop the browser
                browser.stop()

                # Clear the page and delete it
                browser.setPage(QWebEnginePage())
                browser.page().deleteLater()

        # Proceed with closing the tab
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)
        else:
            self.close()

    def closeEvent(self, event):
        """Handle the event when the window is being closed."""
        # Iterate over all tabs and aggressively stop media playback
        for index in range(self.tab_widget.count()):
            tab_widget = self.tab_widget.widget(index)
            if tab_widget:
                browser = tab_widget.findChild(QWebEngineView)
                if browser:
                    browser.page().runJavaScript("""
                        var mediaElements = document.querySelectorAll('audio, video');
                        mediaElements.forEach(function(media) {
                            media.pause();
                        });
                    """)
                    browser.stop()
                    browser.setPage(QWebEnginePage())
                    browser.page().deleteLater()

        # Accept the close event
        event.accept()






    def apply_dark_mode(self, app):
        """Apply dark theme to the application."""
        if not self.settings.get("dark_mode", True):
            app.setPalette(QStyleFactory.create("Fusion").standardPalette())
            app.setStyleSheet("")
            return

        # Use Fusion style as base
        app.setStyle("Fusion")
        
        # Get theme colors
        theme = self.settings.get("dark_theme", self.default_settings["dark_theme"])
        
        # Create and set dark palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(theme["window_color"]))
        palette.setColor(QPalette.WindowText, QColor(theme["text_color"]))
        palette.setColor(QPalette.Base, QColor(theme["base_color"]))
        palette.setColor(QPalette.AlternateBase, QColor(theme["base_color"]))
        palette.setColor(QPalette.ToolTipBase, QColor(theme["tooltip_color"]))
        palette.setColor(QPalette.ToolTipText, QColor(theme["text_color"]))
        palette.setColor(QPalette.Text, QColor(theme["text_color"]))
        palette.setColor(QPalette.Button, QColor(theme["button_color"]))
        palette.setColor(QPalette.ButtonText, QColor(theme["text_color"]))
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(theme["highlight_color"]))
        palette.setColor(QPalette.Highlight, QColor(theme["highlight_color"]))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(theme["disabled_color"]))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(theme["disabled_color"]))
        
        app.setPalette(palette)
        
        # Apply stylesheet
        app.setStyleSheet(f"""
            QWidget {{
                background-color: {theme["base_color"]};
                color: {theme["text_color"]};
            }}
            QPushButton, QToolButton {{
                background-color: {theme["button_color"]};
                border: 1px solid #444;
                padding: 5px;
                border-radius: 3px;
            }}
            QPushButton:hover, QToolButton:hover {{
                background-color: #{self._adjust_lightness(theme["button_color"], 10)};
            }}
            QTabBar::tab {{
                background: {theme["button_color"]};
                color: {theme["text_color"]};
                padding: 8px;
                border: 1px solid #444;
            }}
            QLineEdit, QTextEdit {{
                background-color: {theme["window_color"]};
                border: 1px solid #444;
            }}
            QMenu {{
                background-color: {theme["window_color"]};
            }}
        """)

    def _adjust_lightness(self, hex_color, percent):
        """Adjust color lightness (helper for styles)."""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Convert to HSL
            r /= 255.0
            g /= 255.0
            b /= 255.0
            max_val = max(r, g, b)
            min_val = min(r, g, b)
            l = (max_val + min_val) / 2.0
            
            # Adjust lightness
            l = min(1.0, max(0.0, l + (percent / 100.0)))
            
            # Convert back to RGB
            if l <= 0:
                return "000000"
            if l >= 1:
                return "ffffff"
                
            if max_val == min_val:
                r = g = b = l
            else:
                def hue2rgb(p, q, t):
                    if t < 0: t += 1
                    if t > 1: t -= 1
                    if t < 1/6: return p + (q - p) * 6 * t
                    if t < 1/2: return q
                    if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                    return p
                
                if l < 0.5:
                    q = l * (1 + percent/100)
                else:
                    q = l + percent/100 - (l * percent/100)
                    
                p = 2 * l - q
                r = hue2rgb(p, q, r + 1/3)
                g = hue2rgb(p, q, g)
                b = hue2rgb(p, q, b - 1/3)
            
            # Convert to hex
            r = int(max(0, min(255, round(r * 255))))
            g = int(max(0, min(255, round(g * 255))))
            b = int(max(0, min(255, round(b * 255))))
            return f"{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color.lstrip('#')

# ====================== NOTIFICATION MANAGER ======================
class NotificationManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notification_window = None

    def show_notification(self, title, message, duration=3000):
        if self.notification_window:
            self.notification_window.close()
            
        self.notification_window = QLabel(message)
        self.notification_window.setWindowTitle(title)
        self.notification_window.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint | 
            Qt.ToolTip
        )
        self.notification_window.setStyleSheet("""
            QLabel {
                background-color: #333;
                color: white;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #555;
            }
        """)
        self.notification_window.adjustSize()
        
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.notification_window.width() - 20
        y = screen.height() - self.notification_window.height() - 50
        self.notification_window.move(x, y)
        
        self.notification_window.show()
        QTimer.singleShot(duration, self.notification_window.close)

# ====================== BOOKMARK SEARCHER AND LAUNCHER ======================
class BookmarkSearcher(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Bookmark Search")
        self.setMinimumSize(600, 400)
        
        # Setup UI
        self.setup_ui()
        
        # Apply dark mode if enabled
        if self.parent.settings_manager.get("dark_mode"):
            self.apply_dark_mode()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search bookmarks...")
        self.search_bar.textChanged.connect(self.search_bookmarks)
        layout.addWidget(self.search_bar)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.launch_bookmark)
        layout.addWidget(self.results_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self.launch_selected_bookmark)
        btn_layout.addWidget(open_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        # Populate initial results
        self.search_bookmarks()
    
    def apply_dark_mode(self):
        """Apply dark theme to the dialog."""
        theme = self.parent.settings_manager.get("dark_theme")
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme["base_color"]};
                color: {theme["text_color"]};
            }}
            QLineEdit, QListWidget {{
                background-color: {theme["window_color"]};
                color: {theme["text_color"]};
                border: 1px solid #444;
            }}
            QPushButton {{
                background-color: {theme["button_color"]};
                color: {theme["text_color"]};
                border: 1px solid #444;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: #{self.parent.settings_manager._adjust_lightness(theme["button_color"], 10)};
            }}
        """)
    
class BookmarkSearcher(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Bookmark Search - Name Only")
        self.setMinimumSize(600, 400)
        self.setup_ui()
        
        # Apply dark mode if enabled
        if self.parent.settings_manager.get("dark_mode"):
            self.apply_dark_mode()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search bookmarks by name...")
        self.search_bar.textChanged.connect(self.search_bookmarks)
        layout.addWidget(self.search_bar)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.launch_bookmark)
        layout.addWidget(self.results_list)
        
        # Status label
        self.status_label = QLabel("Ready to search")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def search_bookmarks(self):
        """Enhanced bookmark search with multi-browser support"""
        query = self.search_bar.text().strip().lower()
        self.results_list.clear()

        try:
            # First collect all bookmarks from different sources
            bookmarks = []
            
            # Chrome bookmarks
            if shutil.which("google-chrome-stable"):
                chrome_path = os.path.expanduser("~/.config/google-chrome/Default/Bookmarks")
                if os.path.exists(chrome_path):
                    try:
                        result = subprocess.run(
                            ["jq", r'.. | objects | select(.type?=="url") | "\(.name)@@\(.url)"', chrome_path],
                            capture_output=True, text=True
                        )
                        if result.returncode == 0:
                            bookmarks.extend(
                                (name.strip(), url.strip(' "\''))
                                for line in result.stdout.strip().split('\n')
                                if "@@" in line and (name_url := line.split("@@", 1))
                                for name, url in [name_url]
                            )
                    except Exception as e:
                        print(f"Error parsing Chrome bookmarks: {e}")

            # Chromium bookmarks
            if shutil.which("chromium"):
                chromium_path = os.path.expanduser("~/.config/chromium/Default/Bookmarks")
                if os.path.exists(chromium_path):
                    try:
                        result = subprocess.run(
                            ["jq", r'.. | objects | select(.type?=="url") | "\(.name)@@\(.url)"', chromium_path],
                            capture_output=True, text=True
                        )
                        if result.returncode == 0:
                            bookmarks.extend(
                                (name.strip(), url.strip(' "\''))
                                for line in result.stdout.strip().split('\n')
                                if "@@" in line and (name_url := line.split("@@", 1))
                                for name, url in [name_url]
                            )
                    except Exception as e:
                        print(f"Error parsing Chromium bookmarks: {e}")

            # Firefox bookmarks
            if shutil.which("firefox"):
                try:
                    home = os.path.expanduser("~")
                    profile_path = os.path.join(home, ".mozilla/firefox/*.default-release/places.sqlite")
                    places_db = subprocess.run(
                        ["bash", "-c", f"ls {profile_path}"],
                        capture_output=True, text=True
                    ).stdout.strip()
                    
                    if places_db:
                        db_copy_path = os.path.join(home, "places_copy.sqlite")
                        shutil.copyfile(places_db, db_copy_path)
                        
                        with sqlite3.connect(db_copy_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT moz_bookmarks.title, moz_places.url 
                                FROM moz_bookmarks 
                                INNER JOIN moz_places ON moz_bookmarks.fk = moz_places.id
                            """)
                            bookmarks.extend(
                                (title, url.strip(' "\''))
                                for title, url in cursor.fetchall()
                                if title and url
                            )
                except Exception as e:
                    print(f"Error reading Firefox bookmarks: {e}")
                finally:
                    if 'db_copy_path' in locals() and os.path.exists(db_copy_path):
                        os.remove(db_copy_path)

            # Local bookmarks
            local_path = os.path.expanduser("~/.config/storm_browser/bookmarks.json")
            if os.path.exists(local_path):
                try:
                    with open(local_path, 'r') as f:
                        local_bookmarks = json.load(f)
                        if isinstance(local_bookmarks, list):
                            bookmarks.extend(
                                (bm.get('name', ''), bm.get('url', ''))
                                for bm in local_bookmarks
                            )
                except Exception as e:
                    print(f"Error reading local bookmarks: {e}")

            # Now filter and display results
            max_results = 200
            name_max_len = 50
            url_max_len = 100
            
            matches = [
                (name, url)
                for name, url in bookmarks
                if query in (name or "").lower() or query in (url or "").lower()
            ][:max_results]

            if matches:
                for name, url in matches:
                    display_name = (name or "Untitled")[:name_max_len] + ('...' if len(name or "") > name_max_len else '')
                    display_url = url[:url_max_len] + ('...' if len(url) > url_max_len else '')
                    item = QListWidgetItem(f"{display_name} - {display_url}")
                    item.setData(Qt.UserRole, url)
                    self.results_list.addItem(item)
            else:
                self.results_list.addItem(QListWidgetItem(f"No matches found for '{query}'"))
                
        except Exception as e:
            self.results_list.addItem(QListWidgetItem(f"Search error: {str(e)}"))
    
    def launch_bookmark(self, item):
        """Open selected bookmark in browser"""
        url = item.data(Qt.UserRole)
        if url and self.parent.current_browser():
            self.parent.current_browser().setUrl(QUrl(url))
            self.close()
    
    def apply_dark_mode(self):
        """Apply dark theme if enabled"""
        theme = self.parent.settings_manager.get("dark_theme")
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme["base_color"]};
                color: {theme["text_color"]};
            }}
            QLineEdit, QListWidget {{
                background-color: {theme["window_color"]};
                color: {theme["text_color"]};
                border: 1px solid #444;
            }}
            QListWidget::item:hover {{
                background-color: {theme["highlight_color"]};
            }}
        """)

# ====================== MAIN BROWSER WINDOW ======================
class BrowserMainWindow(QMainWindow):
    def __init__(self):
        # ======================================================================
        # CRITICAL ENVIRONMENT CONFIGURATION (MUST BE FIRST)
        # ======================================================================
        os.environ["QT_VAAPI_ENABLED"] = "1"  # Enable hardware acceleration
        os.environ["LIBVA_DRIVER_NAME"] = "iHD"  # Intel: 'iHD' | AMD: 'radeonsi' | Nvidia: 'nvidia'
        
        # Configure Chromium engine flags for maximum compatibility
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            "--enable-features="
            "Widevine,"                    # DRM support
            "PlatformEncryptedDolbyVision," # Media decoding
            "MediaSessionService,"          # Media controls
            "EmbeddedMediaExperience "      # Modern media APIs
            
            "--disable-features="
            "UseChromeOSDirectVideoDecoder " # Better Linux compatibility
            
            "--enable-mse-mp2t-streaming "  # HLS/DASH streaming support
            "--no-sandbox "                # Bypass security restrictions for verification
            "--widevine-cdm-path=/usr/lib/chromium/WidevineCdm"
        )

        # ======================================================================
        # WINDOW INITIALIZATION
        # ======================================================================
        super().__init__()
        self.setWindowTitle("Storm Browser v12 - Ultimate Edition")
        self.setMinimumSize(800, 600)
        self.showMaximized()  # Start in full-screen mode
        
        # ======================================================================
        # STATE MANAGEMENT
        # ======================================================================
        self.closed_tabs = []          # For tab restoration (Ctrl+Shift+T)
        self.window_state = None       # For session management
        self.media_players = []        # Track active media elements

        # ======================================================================
        # CORE COMPONENT INITIALIZATION
        # ======================================================================
        self.settings_manager = SettingsManager(self)
        self.download_manager = DownloadManager(self)
        self.bookmark_manager = BookmarkManager(self) 
        self.history_manager = HistoryManager(self)
        self.notification_manager = NotificationManager(self)
        
        # ======================================================================
        # UI SETUP
        # ======================================================================
        self.setup_ui()                # Initialize all UI components
        self.setup_connections()       # Connect signals/slots
        self.setup_shortcuts()         # Configure keyboard shortcuts
        
        # ======================================================================
        # RUNTIME CONFIGURATION
        # ======================================================================
        # Apply theme before any pages load
        if self.settings_manager.get("dark_mode", True):
            self.settings_manager.apply_dark_mode(QApplication.instance())
            
        # Configure engine features (DRM, HLS, etc.)
        self.configure_webengine()
        
        # ======================================================================
        # INITIAL CONTENT LOAD
        # ======================================================================
        home_url = self.settings_manager.get("home_page", DEFAULT_HOME_PAGE)
        self.add_new_tab(QUrl(home_url))

    def configure_webengine(self):
        """Enhanced WebEngine configuration for modern web compatibility."""
        # Enable HLS if configured
        if self.settings_manager.get("hls_enabled", HLS_ENABLED):
            QWebEngineSettings.globalSettings().setAttribute(
                QWebEngineSettings.PlaybackRequiresUserGesture, False
            )
            QWebEngineSettings.globalSettings().setAttribute(
                QWebEngineSettings.AutoLoadIconsForPage, True
            )
        
        # Configure DRM and media capabilities
        if self.settings_manager.get("drm_enabled", DRM_ENABLED):
            profile = QWebEngineProfile.defaultProfile()
            
            # Set modern user agent
            profile.setHttpUserAgent(
                self.settings_manager.get("user_agent", USER_AGENT)
            )
            
            # Enable media features
            profile.setProperty("httpAccept", 
                "application/x-mpegURL,application/dash+xml,application/vnd.apple.mpegurl")
            profile.setProperty("enableMediaSource", True)
            profile.setProperty("enableMedia", True)
            profile.setProperty("enableWebAudio", True)
            
            # Additional DRM configuration
            profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
            profile.setCachePath(os.path.join(CONFIG_DIR, "webcache"))
            
            # Apply performance tweaks
            QWebEngineSettings.globalSettings().setAttribute(
                QWebEngineSettings.Accelerated2dCanvasEnabled, True
            )

        # Universal settings
        settings = QWebEngineSettings.globalSettings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)

    def setup_ui(self):
        """Setup the main browser UI with consistent styling."""
        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab bar with corner widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # Add new tab button in corner
        new_tab_btn = QToolButton()
        new_tab_btn.setText("+")
        new_tab_btn.setCursor(Qt.PointingHandCursor)
        new_tab_btn.clicked.connect(lambda: self.add_new_tab())
        self.tab_widget.setCornerWidget(new_tab_btn)
        
        layout.addWidget(self.tab_widget)

        # Navigation bar
        nav_bar = QToolBar("Navigation")
        nav_bar.setMovable(False)
        nav_bar.setIconSize(QSize(24, 24))
        self.addToolBar(nav_bar)

        # Unified button style
        button_style = """
        QToolButton {
            border: none;
            padding: 4px;
            margin: 1px;
            background: transparent;
            border-radius: 3px;
        }
        QToolButton:hover {
            background: rgba(128, 128, 128, 0.2);
        }
        QToolButton:pressed {
            background: rgba(128, 128, 128, 0.3);
        }
        QToolButton[popupMode="1"] {  /* MenuButtonPopup */
            padding-right: 10px;  /* space for arrow */
        }
        """
        
        # Apply style to the toolbar
        nav_bar.setStyleSheet(button_style)

        # Navigation buttons
        nav_buttons = [
            ("back", "go-previous", "Back"),
            ("forward", "go-next", "Forward"),
            ("refresh", "view-refresh", "Refresh"),
            ("home", "go-home", "Home")
        ]
        
        for var_name, icon_name, tooltip in nav_buttons:
            btn = QAction(QIcon.fromTheme(icon_name), tooltip, self)
            setattr(self, f"{var_name}_btn", btn)
            nav_bar.addAction(btn)

        # URL bar container
        url_container = QWidget()
        url_layout = QHBoxLayout(url_container)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.setSpacing(3)

        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search or enter URL")
        url_layout.addWidget(self.url_bar)

        # Right-side action buttons
        action_buttons = [
            ("print", "document-print", "Print page (Ctrl+P)", self.print_current_page),
            ("pdf", "document-export", "Save as PDF (Ctrl+Shift+P)", self.print_to_pdf),
            ("screenshot", "camera-photo", "Take screenshot (Ctrl+Shift+S)", 
             lambda: self.take_screenshot("ask"))
        ]
        
        for var_name, icon_name, tooltip, handler in action_buttons:
            btn = QToolButton()
            btn.setIcon(QIcon.fromTheme(icon_name))
            btn.setToolTip(tooltip)
            btn.clicked.connect(handler)
            setattr(self, f"{var_name}_btn", btn)
            url_layout.addWidget(btn)
            
            # Special setup for screenshot button
            if var_name == "screenshot":
                btn.setPopupMode(QToolButton.MenuButtonPopup)
                menu = QMenu()
                actions = [
                    ("edit-copy", "Copy to Clipboard", "clipboard"),
                    ("document-save", "Save to File", "file"),
                    ("select-rectangular", "Capture Region", "region")
                ]
                for icon, text, mode in actions:
                    action = QAction(QIcon.fromTheme(icon), text, self)
                    action.triggered.connect(lambda _, m=mode: self.take_screenshot(m))
                    menu.addAction(action)
                btn.setMenu(menu)

        # Add URL container to toolbar
        nav_bar.addWidget(url_container)

        # Right-side navigation buttons
        nav_buttons_right = [
            ("search", "system-search", "Search"),
            ("bookmarks", "bookmarks", "Bookmarks"),
            ("downloads", "folder-download", "Downloads"),
            ("history", "view-history", "History"),
            ("settings", "preferences-system", "Settings")
        ]
        
        for var_name, icon_name, tooltip in nav_buttons_right:
            btn = QAction(QIcon.fromTheme(icon_name), tooltip, self)
            setattr(self, f"{var_name}_btn", btn)
            nav_bar.addAction(btn)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Download progress bar
        self.download_progress_bar = QProgressBar()
        self.download_progress_bar.setTextVisible(False)
        self.download_progress_bar.setFixedHeight(3)
        self.download_progress_bar.hide()
        self.status_bar.addPermanentWidget(self.download_progress_bar)

    def setup_connections(self):
        """Connect signals to slots."""
        # Navigation buttons
        self.back_btn.triggered.connect(lambda: self.current_browser().back())
        self.forward_btn.triggered.connect(lambda: self.current_browser().forward())
        self.refresh_btn.triggered.connect(lambda: self.current_browser().reload())
        self.home_btn.triggered.connect(self.go_home)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.search_btn.triggered.connect(self.perform_search)
        self.bookmarks_btn.triggered.connect(self.show_bookmarks)
        self.downloads_btn.triggered.connect(self.show_downloads)
        self.history_btn.triggered.connect(self.show_history)
        self.settings_btn.triggered.connect(self.show_settings)
        
        # Download manager signals
        self.download_manager.download_started.connect(self.on_download_started)
        self.download_manager.download_progress.connect(self.on_download_progress)
        self.download_manager.download_finished.connect(self.on_download_finished)


    def print_current_page(self):
        """Print current page with option for PDF output."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Print Options")
        
        layout = QVBoxLayout()
        
        # Regular print button
        print_btn = QPushButton("Print to Printer")
        print_btn.clicked.connect(lambda: [
            self._print_to_printer(),
            dialog.close()
        ])
        
        # PDF print button
        pdf_btn = QPushButton("Save as PDF")
        pdf_btn.clicked.connect(lambda: [
            self.print_to_pdf(),
            dialog.close()
        ])
        
        layout.addWidget(print_btn)
        layout.addWidget(pdf_btn)
        dialog.setLayout(layout)
        dialog.exec_()

    def _print_to_printer(self):
        """Handle actual printer output"""
        if browser := self.current_browser():
            printer = QPrinter(QPrinter.HighResolution)
            print_dialog = QPrintDialog(printer, self)
            
            if print_dialog.exec_() == QPrintDialog.Accepted:
                browser.page().print(printer, lambda success: 
                    self.status_bar.showMessage(
                        "Printing completed" if success else "Printing failed",
                        3000
                    )
                )
    def print_to_pdf(self):
        """Print current page to PDF file."""
        if browser := self.current_browser():
            # Set up default PDF filename with timestamp
            default_name = f"page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            default_path = os.path.join(DOWNLOAD_DIR, default_name)
            
            # Get save path from user
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save as PDF",
                default_path,
                "PDF Files (*.pdf);;All Files (*)"
            )
            
            if filename:
                # Ensure .pdf extension
                if not filename.lower().endswith('.pdf'):
                    filename += '.pdf'
                
                # Show saving message
                self.status_bar.showMessage("Saving PDF...", 3000)
                
                # Print to PDF
                browser.page().printToPdf(filename)
                
                # Show completion message
                self.status_bar.showMessage(f"PDF saved to {filename}", 5000)
                
                # Optional: Open the PDF after saving
                QTimer.singleShot(1000, lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(filename)))


    def take_screenshot(self, mode="ask"):
        """
        Handle screenshot capture with multiple output options
        Modes: "ask" (show dialog), "clipboard", "file"
        """
        if browser := self.current_browser():
            try:
                # Show busy cursor during capture
                QApplication.setOverrideCursor(Qt.WaitCursor)
                
                # Capture the viewport
                pixmap = browser.grab()
                
                # Restore cursor
                QApplication.restoreOverrideCursor()
                
                if mode == "clipboard":
                    self._save_screenshot_to_clipboard(pixmap)
                elif mode == "file":
                    self._save_screenshot_to_file(pixmap)
                else:  # ask
                    self._show_screenshot_options(pixmap)
                    
            except Exception as e:
                self.status_bar.showMessage(f"Screenshot error: {str(e)}", 3000)
                QApplication.restoreOverrideCursor()
                logging.error(f"Screenshot failed: {str(e)}", exc_info=True)

    def _save_screenshot_to_clipboard(self, pixmap):
        """Save screenshot to clipboard with visual feedback"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            
            # Show brief notification
            self.notification_manager.show_notification(
                "Screenshot Copied",
                "The screenshot was copied to clipboard",
                2000
            )
            
            # Also show in status bar
            self.status_bar.showMessage("Screenshot copied to clipboard", 3000)
            
        except Exception as e:
            self.status_bar.showMessage(f"Clipboard error: {str(e)}", 3000)
            logging.error(f"Clipboard save failed: {str(e)}", exc_info=True)

    def _save_screenshot_to_file(self, pixmap, suggested_path=None):
        """Save screenshot to file with intelligent defaults"""
        try:
            # Set default save location
            screenshot_dir = os.path.join(
                os.path.expanduser("~"), 
                "Pictures",
                "Screenshots"
            )
            os.makedirs(screenshot_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            default_filename = f"StormBrowser_{timestamp}.png"
            
            # Use suggested path if provided (from drag/drop or other operations)
            if suggested_path and os.path.isdir(os.path.dirname(suggested_path)):
                default_path = suggested_path
            else:
                default_path = os.path.join(screenshot_dir, default_filename)
            
            # Show save dialog
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Screenshot",
                default_path,
                "PNG Images (*.png);;JPEG Images (*.jpg *.jpeg);;BMP Images (*.bmp);;All Files (*)"
            )
            
            if filename:
                # Ensure proper file extension
                if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    filename += '.png'
                
                # Save with quality settings
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    quality = 95  # High quality JPEG
                    pixmap.save(filename, quality=quality)
                else:
                    pixmap.save(filename)
                
                # Show notification with click-to-open functionality
                notification = self.notification_manager.show_notification(
                    "Screenshot Saved",
                    f"Saved to {os.path.basename(filename)}",
                    3000
                )
                
                # Add click handler to open the file
                if notification:
                    notification.mousePressEvent = lambda e: QDesktopServices.openUrl(
                        QUrl.fromLocalFile(filename)
                    )
                
                self.status_bar.showMessage(f"Screenshot saved to {filename}", 5000)
                
        except Exception as e:
            self.status_bar.showMessage(f"Save error: {str(e)}", 3000)
            logging.error(f"Screenshot save failed: {str(e)}", exc_info=True)

    def _show_screenshot_options(self, pixmap):
        """Show dialog with screenshot options"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Screenshot Options")
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        # Preview thumbnail
        preview_label = QLabel()
        preview_pixmap = pixmap.scaled(
            400, 300, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        preview_label.setPixmap(preview_pixmap)
        preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(preview_label)
        
        # Button options
        btn_layout = QVBoxLayout()
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(lambda: [
            self._save_screenshot_to_clipboard(pixmap),
            dialog.close()
        ])
        btn_layout.addWidget(copy_btn)
        
        save_btn = QPushButton("Save to File...")
        save_btn.clicked.connect(lambda: [
            self._save_screenshot_to_file(pixmap),
            dialog.close()
        ])
        btn_layout.addWidget(save_btn)
        
        # Advanced options expandable section
        advanced_group = QGroupBox("Advanced Options")
        advanced_group.setCheckable(True)
        advanced_group.setChecked(False)
        advanced_layout = QVBoxLayout()
        
        # Delay capture option
        delay_layout = QHBoxLayout()
        delay_label = QLabel("Delay (seconds):")
        delay_spin = QSpinBox()
        delay_spin.setRange(0, 10)
        delay_spin.setValue(0)
        delay_layout.addWidget(delay_label)
        delay_layout.addWidget(delay_spin)
        advanced_layout.addLayout(delay_layout)
        
        # Region capture option
        region_capture_btn = QPushButton("Capture Specific Region")
        region_capture_btn.clicked.connect(lambda: [
            self._capture_region(),
            dialog.close()
        ])
        advanced_layout.addWidget(region_capture_btn)
        
        advanced_group.setLayout(advanced_layout)
        btn_layout.addWidget(advanced_group)
        
        layout.addLayout(btn_layout)
        
        # Close button
        close_btn = QPushButton("Cancel")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def _capture_region(self):
        """Capture a custom region of the screen"""
        # Hide main window temporarily
        self.hide()
        QApplication.processEvents()
        
        # Create transparent overlay for region selection
        overlay = QLabel()
        overlay.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        overlay.setAttribute(Qt.WA_TranslucentBackground)
        overlay.setStyleSheet("background-color: rgba(0,0,0,0.5);")
        overlay.setGeometry(QApplication.desktop().screenGeometry())
        overlay.show()
        
        # Create selection rubber band
        rubber_band = QRubberBand(QRubberBand.Rectangle, overlay)
        
        start_pos = None
        
        def mouse_press(event):
            nonlocal start_pos
            start_pos = event.pos()
            rubber_band.setGeometry(QRect(start_pos, QSize()))
            rubber_band.show()
        
        def mouse_move(event):
            if start_pos:
                rubber_band.setGeometry(QRect(start_pos, event.pos()).normalized())
        
        def mouse_release(event):
            nonlocal start_pos
            if start_pos:
                rect = rubber_band.geometry()
                if rect.width() > 10 and rect.height() > 10:  # Minimum size
                    # Capture the selected region
                    screenshot = QApplication.primaryScreen().grabWindow(
                        0,
                        rect.x(),
                        rect.y(),
                        rect.width(),
                        rect.height()
                    )
                    self._show_screenshot_options(screenshot)
                
                rubber_band.hide()
                overlay.hide()
                self.show()
                start_pos = None
        
        overlay.mousePressEvent = mouse_press
        overlay.mouseMoveEvent = mouse_move
        overlay.mouseReleaseEvent = mouse_release



    def setup_shortcuts(self):
        """Setup keyboard shortcuts with proper error handling and logging."""
        try:
            # Create shortcuts dictionary with fallback defaults
            shortcuts = {
                # Navigation
                "back": ("Alt+Left", lambda: self.current_browser().back()),
                "forward": ("Alt+Right", lambda: self.current_browser().forward()),
                "reload": ("F5", self.reload_current_tab),
                "reload_ignore_cache": ("Shift+F5", lambda: self.current_browser().reload()),
                "stop": ("Esc", lambda: self.current_browser().stop()),
                "home": ("Alt+Home", self.go_home),
                
                # Tab management
                "new_tab": ("Ctrl+T", self.add_new_tab),
                "close_tab": ("Ctrl+W", lambda: self.close_tab(self.tab_widget.currentIndex())),
                "next_tab": ("Ctrl+Tab", self.focus_next_tab),
                "prev_tab": ("Ctrl+Shift+Tab", self.focus_prev_tab),
                "restore_tab": ("Ctrl+Shift+T", self.restore_closed_tab),
                
                # UI focus
                "focus_url": ("Ctrl+L", self.focus_url_bar),
                "focus_search": ("Ctrl+K", self.focus_search_bar),
                
                # Tools
                "bookmark_search": ("Ctrl+B", self.show_bookmark_search),
                "bookmark_page": ("Ctrl+D", self.add_current_to_bookmarks),
                "downloads": ("Ctrl+J", self.show_downloads),
                "history": ("Ctrl+H", self.show_history),
                "settings": ("Ctrl+,", self.show_settings),
                "print": ("Ctrl+P", self.print_current_page),
                "print_pdf": ("Ctrl+Shift+P", self.print_to_pdf),
                "screenshot": ("Ctrl+Shift+S", lambda: self.take_screenshot("ask")),
                "full_screenshot": ("Ctrl+Alt+Shift+S", lambda: self.take_screenshot("full")),
                "region_screenshot": ("Ctrl+Shift+R", lambda: self.take_screenshot("region")),
                
                # Developer tools
                "dev_tools": ("F12", self.toggle_dev_tools),
                "view_source": ("Ctrl+U", lambda: self.current_browser().page().action(QWebEnginePage.ViewSource).trigger()),
                
                # Search/URL
                "autocomplete_url": ("Ctrl+Return", self.autocomplete_url),
                "search_selected": ("Ctrl+E", self.search_selected_text),
            }

            # Create and connect shortcuts
            self.shortcut_objects = {}  # Store shortcut objects to prevent garbage collection
            for name, (keyseq, callback) in shortcuts.items():
                try:
                    shortcut = QShortcut(QKeySequence(keyseq), self)
                    shortcut.activated.connect(callback)
                    self.shortcut_objects[name] = shortcut  # Keep reference
                    
                    # Set context to avoid conflicts
                    shortcut.setContext(Qt.ApplicationShortcut)
                    
                    logging.debug(f"Shortcut configured: {name} -> {keyseq}")
                except Exception as e:
                    logging.error(f"Failed to set shortcut {name}: {str(e)}")

            # Additional special cases
            QShortcut(QKeySequence("Ctrl++"), self).activated.connect(self.zoom_in)
            QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(self.zoom_out)
            QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(self.zoom_reset)

        except Exception as e:
            logging.error(f"Error setting up shortcuts: {str(e)}")
            # Fallback to essential shortcuts if setup fails
            QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(self.add_new_tab)
            QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(
                lambda: self.close_tab(self.tab_widget.currentIndex()))
            QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(
                lambda: self.take_screenshot("ask"))

    def focus_next_tab(self):
        """Focus the next tab."""
        current = self.tab_widget.currentIndex()
        next_index = (current + 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(next_index)

    def focus_prev_tab(self):
        """Focus the previous tab."""
        current = self.tab_widget.currentIndex()
        prev_index = (current - 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(prev_index)

    def reload_current_tab(self):
        """Reload current tab."""
        if browser := self.current_browser():
            browser.reload()

    def focus_url_bar(self):
        """Focus the URL bar and select all text."""
        self.url_bar.setFocus()
        self.url_bar.selectAll()


    def autocomplete_url(self):
        """Autocomplete the URL in the address bar with www. and .com."""
        current_text = self.url_bar.text().strip()

        # Skip if empty
        if not current_text:
            return

        # If already a complete URL, just load it
        if current_text.startswith(("http://", "https://")):
            self.navigate_to_url()
            return

        # Autocomplete the URL
        autocomplete_url = f"www.{current_text}.com"
        self.url_bar.setText(autocomplete_url)

        # Load the completed URL
        self.navigate_to_url()

    def navigate_to_url(self):
        """Navigate to the URL in the address bar."""
        url_text = self.url_bar.text().strip()
        if not url_text:
            return

        if not url_text.startswith(("http://", "https://")):
            url_text = "https://" + url_text

        self.current_browser().setUrl(QUrl(url_text))


    def current_browser(self):
        """Get the current QWebEngineView."""
        current_widget = self.tab_widget.currentWidget()
        if current_widget:
            return current_widget.findChild(QWebEngineView)
        return None

    def add_new_tab(self, url=None, title="New Tab"):
        """Add a new browser tab."""
        if url is None:
            url = QUrl(self.settings_manager.get("home_page"))
        
        # Create container widget
        container = QWidget()
        layout = QVBoxLayout()
        container.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create web view
        browser = QWebEngineView()
        browser.setUrl(url)
        
        # Configure browser settings
        settings = browser.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, 
                            self.settings_manager.get("javascript_enabled", True))
        settings.setAttribute(QWebEngineSettings.AutoLoadImages, 
                            self.settings_manager.get("auto_load_images", True))
        
        # Create progress bar
        progress_bar = QProgressBar()
        progress_bar.setMaximumHeight(3)
        progress_bar.setTextVisible(False)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 0px;
                background: transparent;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
            }
        """)
        
        # Connect signals
        browser.urlChanged.connect(self.update_urlbar)
        browser.titleChanged.connect(lambda t: self.update_tab_title(browser, t))
        browser.loadProgress.connect(progress_bar.setValue)
        browser.page().profile().downloadRequested.connect(self.download_manager.handle_download)
        
        # Add widgets to layout
        layout.addWidget(browser)
        layout.addWidget(progress_bar)

        # Add tab
        tab_index = self.tab_widget.addTab(container, title)
        self.tab_widget.setCurrentIndex(tab_index)
        
        return browser

    def close_tab(self, index):
        """Close a tab and remember it for possible restoration."""
        if self.tab_widget.count() > 1:
            browser = self.tab_widget.widget(index).findChild(QWebEngineView)
            if browser:
                # Remember URL and title before closing
                self.closed_tabs.append((browser.url().toString(), 
                                       self.tab_widget.tabText(index)))
            self.tab_widget.removeTab(index)
        else:
            self.close()

    def update_urlbar(self, url):
        """Update the URL bar when navigation occurs."""
        self.url_bar.setText(url.toString())
        self.url_bar.setCursorPosition(0)
        
        # Add to history
        browser = self.current_browser()
        if browser:
            title = self.tab_widget.tabText(self.tab_widget.currentIndex())
            self.history_manager.add_history_entry(url.toString(), title)

    def update_tab_title(self, browser, title):
        """Update tab title when page title changes."""
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i).findChild(QWebEngineView) == browser:
                # Truncate long titles
                display_title = title[:20] + "..." if len(title) > 20 else title
                self.tab_widget.setTabText(i, display_title)
                self.tab_widget.setTabToolTip(i, title)
                break

    def navigate_to_url(self):
        """Navigate to the URL in the address bar."""
        url_text = self.url_bar.text().strip()
        if not url_text:
            return

        if "." in url_text and " " not in url_text:
            if not url_text.startswith(("http://", "https://")):
                url_text = "https://" + url_text
            self.current_browser().setUrl(QUrl(url_text))
        else:
            self.perform_search()

    def perform_search(self):
        """Perform a web search."""
        query = self.url_bar.text().strip()
        if not query:
            return

        search_url = self.settings_manager.get("search_engine").format(query)
        self.current_browser().setUrl(QUrl(search_url))

    def go_home(self):
        """Navigate to the home page."""
        self.current_browser().setUrl(QUrl(self.settings_manager.get("home_page")))

    def toggle_dev_tools(self):
        """Toggle developer tools for current page."""
        browser = self.current_browser()
        if browser:
            browser.page().triggerAction(QWebEnginePage.InspectElement)

    def show_bookmark_search(self):
        """Show the bookmark search dialog."""
        searcher = BookmarkSearcher(self)
        searcher.exec_()



    def browse_download_dir(self):
        """Open a directory dialog to choose download location."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Download Directory",
            self.download_dir_edit.text() or DOWNLOAD_DIR
        )
        if dir_path:
            self.download_dir_edit.setText(dir_path)

    def configure_webengine(self):
        """Configure WebEngine settings for HLS and DRM support."""
        # Enable HLS if configured
        if self.settings_manager.get("hls_enabled", HLS_ENABLED):
            QWebEngineSettings.globalSettings().setAttribute(
                QWebEngineSettings.PlaybackRequiresUserGesture, False
            )
        
        # Enable DRM if configured
        if self.settings_manager.get("drm_enabled", DRM_ENABLED):
            profile = QWebEngineProfile.defaultProfile()
            profile.setHttpUserAgent(self.settings_manager.get("user_agent", USER_AGENT))
            
            # Enable Widevine
            profile.setProperty("httpAccept", "application/x-mpegURL,application/dash+xml,application/vnd.apple.mpegurl")
            profile.setProperty("enableMediaSource", True)
            profile.setProperty("enableMedia", True)
            profile.setProperty("enableWebAudio", True)
            
            # Set common DRM flags
            os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
                "--enable-media-stream "
                "--enable-features=WidevineCdm "
                "--disable-features=UseChromeOSDirectVideoDecoder"
            )

    def reset_shortcuts_to_defaults(self):
        """Reset all shortcuts to their default values."""
        default_shortcuts = {
            "back": "Alt+Left",
            "forward": "Alt+Right",
            "reload": "F5",
            "reload_ignore_cache": "Shift+F5",
            "stop": "Esc",
            "home": "Alt+Home",
            "new_tab": "Ctrl+T",
            "close_tab": "Ctrl+W",
            "next_tab": "Ctrl+Tab",
            "prev_tab": "Ctrl+Shift+Tab",
            "restore_tab": "Ctrl+Shift+T",
            "bookmark_search": "Ctrl+B",
            "bookmark_page": "Ctrl+D",
            "downloads": "Ctrl+J",
            "history": "Ctrl+H",
            "settings": "Ctrl+,",
            "print": "Ctrl+P",
            "screenshot": "Ctrl+Shift+S",
            "full_screenshot": "Ctrl+Alt+Shift+S",
            "region_screenshot": "Ctrl+Shift+R",
            "dev_tools": "F12",
            "view_source": "Ctrl+U",
            "zoom_in": "Ctrl++",
            "zoom_out": "Ctrl+-",
            "zoom_reset": "Ctrl+0"
        }
        
        for name, editor in self.shortcut_editors.items():
            if name in default_shortcuts:
                editor.setKeySequence(QKeySequence(default_shortcuts[name]))

    def restore_closed_tab(self):
        """Restore the most recently closed tab."""
        if hasattr(self, 'closed_tabs') and self.closed_tabs:
            url, title = self.closed_tabs.pop()
            self.add_new_tab(QUrl(url), title)
        else:
            self.status_bar.showMessage("No tabs to restore", 2000)

    def zoom_in(self):
        """Increase zoom level by 10%."""
        if browser := self.current_browser():
            current_zoom = browser.zoomFactor()
            browser.setZoomFactor(min(current_zoom + 0.1, 3.0))  # Max zoom 300%
            self.status_bar.showMessage(f"Zoom: {int(browser.zoomFactor() * 100)}%", 1500)

    def zoom_out(self):
        """Decrease zoom level by 10%."""
        if browser := self.current_browser():
            current_zoom = browser.zoomFactor()
            browser.setZoomFactor(max(current_zoom - 0.1, 0.3))  # Min zoom 30%
            self.status_bar.showMessage(f"Zoom: {int(browser.zoomFactor() * 100)}%", 1500)

    def zoom_reset(self):
        """Reset zoom level to 100%."""
        if browser := self.current_browser():
            browser.setZoomFactor(1.0)
            self.status_bar.showMessage("Zoom reset to 100%", 1500)

    def search_selected_text(self):
        """Search for currently selected text."""
        if browser := self.current_browser():
            browser.page().toPlainText(lambda text: self._perform_search_for_selection(text))

    def _perform_search_for_selection(self, page_text):
        """Helper method to handle selected text search."""
        cursor = self.current_browser().page().cursor()
        selected_text = page_text[cursor.selectionStart():cursor.selectionEnd()].strip()
        
        if selected_text:
            search_url = self.settings_manager.get("search_engine").format(selected_text)
            self.add_new_tab(QUrl(search_url))
        else:
            self.status_bar.showMessage("No text selected", 2000)

    def focus_search_bar(self):
        """Focus the search/URL bar and select all text."""
        self.url_bar.setFocus()
        self.url_bar.selectAll()

    # ====================== BOOKMARKS ======================
    def show_bookmarks(self):
        """Show bookmarks dialog with import options."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Bookmarks")
        dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout()
        
        # Import buttons
        import_layout = QHBoxLayout()
        chrome_btn = QPushButton("Import from Chrome")
        firefox_btn = QPushButton("Import from Firefox")
        import_layout.addWidget(chrome_btn)
        import_layout.addWidget(firefox_btn)
        layout.addLayout(import_layout)

        # Bookmarks tree
        self.bookmarks_tree = QTreeWidget()
        self.bookmarks_tree.setHeaderLabels(["Name", "URL"])
        self.bookmarks_tree.setColumnWidth(0, 200)
        self.bookmarks_tree.setColumnWidth(1, 350)
        self.bookmarks_tree.itemDoubleClicked.connect(self.open_bookmark)
        self.refresh_bookmarks_tree()
        layout.addWidget(self.bookmarks_tree)

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Current Page")
        remove_btn = QPushButton("Remove Selected")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)

        # Connect signals
        chrome_btn.clicked.connect(lambda: self.import_bookmarks("chrome"))
        firefox_btn.clicked.connect(lambda: self.import_bookmarks("firefox"))
        add_btn.clicked.connect(self.add_current_to_bookmarks)
        remove_btn.clicked.connect(self.remove_selected_bookmark)

        dialog.setLayout(layout)
        dialog.exec_()

    def refresh_bookmarks_tree(self):
        """Refresh the bookmarks tree view."""
        self.bookmarks_tree.clear()
        
        for folder, bookmarks in self.bookmark_manager.bookmarks["folders"].items():
            folder_item = QTreeWidgetItem(self.bookmarks_tree, [folder])
            for bookmark in bookmarks:
                item = QTreeWidgetItem(folder_item, [bookmark["title"], bookmark["url"]])
                item.setData(0, Qt.UserRole, bookmark)
            folder_item.setExpanded(True)

    def import_bookmarks(self, browser):
        """Import bookmarks from another browser."""
        count = self.bookmark_manager.import_browser_bookmarks(browser)
        self.refresh_bookmarks_tree()
        self.notification_manager.show_notification(
            "Bookmarks Imported", 
            f"Successfully imported {count} bookmarks from {browser.capitalize()}"
        )

    def add_current_to_bookmarks(self):
        """Add current page to bookmarks."""
        browser = self.current_browser()
        if browser:
            url = browser.url().toString()
            title = self.tab_widget.tabText(self.tab_widget.currentIndex())
            self.bookmark_manager.add_bookmark(url, title)
            self.refresh_bookmarks_tree()
            self.notification_manager.show_notification(
                "Bookmark Added", 
                f"Added '{title}' to bookmarks"
            )

    def remove_selected_bookmark(self):
        """Remove selected bookmark."""
        selected = self.bookmarks_tree.currentItem()
        if selected and selected.childCount() == 0:  # Not a folder
            bookmark = selected.data(0, Qt.UserRole)
            if bookmark:
                self.bookmark_manager.remove_bookmark(bookmark["url"])
                self.refresh_bookmarks_tree()

    def open_bookmark(self, item, column):
        """Open bookmark in current tab."""
        if item.childCount() == 0:  # Not a folder
            bookmark = item.data(0, Qt.UserRole)
            if bookmark:
                self.current_browser().setUrl(QUrl(bookmark["url"]))

    # ====================== DOWNLOADS ======================
    def on_download_started(self, filename, size):
        """Handle when a download starts."""
        self.download_progress_bar.show()
        self.download_progress_bar.setValue(0)
        self.status_bar.showMessage(f"Downloading: {filename}")

    def on_download_progress(self, filename, received, total, speed, eta):
        """Update download progress."""
        percent = int((received / total) * 100) if total > 0 else 0
        self.download_progress_bar.setMaximum(total)
        self.download_progress_bar.setValue(received)
        
        message = (
            f"Downloading {filename}: {format_size(received)} of {format_size(total)} "
            f"({percent}%) - {speed} - ETA: {eta}"
        )
        self.status_bar.showMessage(message)

    def on_download_finished(self, path, success, filename):
        """Handle download completion."""
        self.download_progress_bar.hide()
        self.status_bar.clearMessage()
        
        if success:
            self.notification_manager.show_notification(
                "Download Complete",
                f"'{filename}' saved to {os.path.dirname(path)}",
                5000
            )
        else:
            self.notification_manager.show_notification(
                "Download Failed",
                f"Failed to download '{filename}'",
                5000
            )

    def show_downloads(self):
        """Show downloads manager dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Downloads")
        dialog.setMinimumSize(700, 500)

        layout = QVBoxLayout()
        
        # Tabs for active/completed downloads
        tab_widget = QTabWidget()
        
        # Active downloads tab
        active_tab = QWidget()
        active_layout = QVBoxLayout()
        self.active_downloads_list = QListWidget()
        active_layout.addWidget(self.active_downloads_list)
        active_tab.setLayout(active_layout)
        
        # Completed downloads tab
        completed_tab = QWidget()
        completed_layout = QVBoxLayout()
        self.completed_downloads_list = QListWidget()
        completed_layout.addWidget(self.completed_downloads_list)
        completed_tab.setLayout(completed_layout)
        
        tab_widget.addTab(active_tab, "Active Downloads")
        tab_widget.addTab(completed_tab, "Completed Downloads")
        layout.addWidget(tab_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        open_btn = QPushButton("Open File")
        open_folder_btn = QPushButton("Open Folder")
        cancel_btn = QPushButton("Cancel Download")
        clear_btn = QPushButton("Clear Completed")
        btn_layout.addWidget(open_btn)
        btn_layout.addWidget(open_folder_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)
        
        # Connect signals
        open_btn.clicked.connect(self.open_selected_download)
        open_folder_btn.clicked.connect(self.open_download_folder)
        cancel_btn.clicked.connect(self.cancel_selected_download)
        clear_btn.clicked.connect(self.clear_completed_downloads)
        
        # Populate lists
        self.update_downloads_lists()
        
        dialog.setLayout(layout)
        dialog.exec_()

    def update_downloads_lists(self):
        """Update active and completed downloads lists."""
        self.active_downloads_list.clear()
        self.completed_downloads_list.clear()
        
        # Active downloads
        for download_id, download in self.download_manager.active_downloads.items():
            if 'item' in download:
                received = download['received']
                total = download['total']
                percent = (received / total * 100) if total > 0 else 0
                
                item = QListWidgetItem(
                    f"{download['filename']} - {percent:.1f}% "
                    f"({format_size(received)} of {format_size(total)})"
                )
                item.setData(Qt.UserRole, download_id)
                self.active_downloads_list.addItem(item)
        
        # Completed downloads
        for download in self.download_manager.completed_downloads:
            status = "✓" if download.get('success', True) else "✗"
            item = QListWidgetItem(
                f"{status} {download['filename']} - {format_size(download.get('received', 0))}"
            )
            item.setData(Qt.UserRole, download['path'])
            self.completed_downloads_list.addItem(item)

    def open_selected_download(self):
        """Open selected downloaded file."""
        if self.completed_downloads_list.currentItem():
            path = self.completed_downloads_list.currentItem().data(Qt.UserRole)
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_download_folder(self):
        """Open downloads folder."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(DOWNLOAD_DIR))

    def cancel_selected_download(self):
        """Cancel selected active download."""
        if self.active_downloads_list.currentItem():
            download_id = self.active_downloads_list.currentItem().data(Qt.UserRole)
            if download_id in self.download_manager.active_downloads:
                download = self.download_manager.active_downloads[download_id]
                if 'item' in download:
                    download['item'].cancel()
                if download_id in self.download_manager.active_downloads:
                    del self.download_manager.active_downloads[download_id]
                self.update_downloads_lists()


    def clear_completed_downloads(self):
        """Clear completed downloads list."""
        self.download_manager.completed_downloads = []
        self.update_downloads_lists()

    # ====================== HISTORY ======================
    def show_history(self):
        """Show history dialog with search."""
        dialog = QDialog(self)
        dialog.setWindowTitle("History")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Search history...")
        search_btn = QPushButton("Search")
        clear_btn = QPushButton("Clear History")
        search_layout.addWidget(self.history_search)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(clear_btn)
        layout.addLayout(search_layout)
        
        # History list
        self.history_list = QTreeWidget()
        self.history_list.setHeaderLabels(["Title", "URL", "Last Visited"])
        self.history_list.setColumnWidth(0, 250)
        self.history_list.setColumnWidth(1, 350)
        self.history_list.itemDoubleClicked.connect(self.open_history_item)
        self.refresh_history_list()
        layout.addWidget(self.history_list)
        
        # Connect signals
        search_btn.clicked.connect(self.refresh_history_list)
        clear_btn.clicked.connect(self.clear_history)
        self.history_search.returnPressed.connect(self.refresh_history_list)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def refresh_history_list(self):
        """Refresh history list with optional search."""
        search_query = self.history_search.text()
        history = self.history_manager.get_history(search_query=search_query)
        
        self.history_list.clear()
        
        # Group by date
        date_groups = {}
        for entry in history:
            visit_date = datetime.fromisoformat(entry["date"]).strftime("%Y-%m-%d")
            if visit_date not in date_groups:
                date_groups[visit_date] = []
            date_groups[visit_date].append(entry)
        
        # Add to tree
        for date, entries in sorted(date_groups.items(), reverse=True):
            date_item = QTreeWidgetItem(self.history_list, [date, "", ""])
            for entry in entries:
                QTreeWidgetItem(date_item, [
                    entry["title"],
                    entry["url"],
                    datetime.fromisoformat(entry["date"]).strftime("%H:%M:%S")
                ])
            date_item.setExpanded(True)

    def clear_history(self):
        """Clear browsing history."""
        reply = QMessageBox.question(
            self, "Clear History",
            "Are you sure you want to clear all browsing history?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.history_manager.clear_history()
            self.refresh_history_list()

    def open_history_item(self, item, column):
        """Open history item in current tab."""
        if item.childCount() == 0:  # Not a date group
            url = item.text(1)
            self.current_browser().setUrl(QUrl(url))

    # ====================== SETTINGS ======================
    def show_settings(self):
        """Display comprehensive settings dialog with organized configuration options."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Browser Settings")
        dialog.setMinimumSize(900, 700)
        
        # Main tab widget
        tab_widget = QTabWidget()
        
        # General Settings Tab
        general_tab = QWidget()
        general_layout = QFormLayout()
        general_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        # Home page setting
        self.home_page_edit = QLineEdit(self.settings_manager.get("home_page"))
        general_layout.addRow(QLabel("Home Page:"), self.home_page_edit)
        
        # Search engine setting
        self.search_engine_edit = QLineEdit(self.settings_manager.get("search_engine"))
        general_layout.addRow(QLabel("Search Engine:"), self.search_engine_edit)
        
        # Download directory
        download_layout = QHBoxLayout()
        self.download_dir_edit = QLineEdit(self.settings_manager.get("download_dir"))
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_download_dir)
        download_layout.addWidget(self.download_dir_edit)
        download_layout.addWidget(browse_btn)
        general_layout.addRow(QLabel("Download Directory:"), download_layout)
        
        # Appearance settings
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout()
        
        self.dark_mode_check = QCheckBox("Enable dark mode")
        self.dark_mode_check.setChecked(self.settings_manager.get("dark_mode"))
        appearance_layout.addWidget(self.dark_mode_check)
        
        appearance_group.setLayout(appearance_layout)
        general_layout.addRow(appearance_group)
        
        # Media settings
        media_group = QGroupBox("Media Playback")
        media_layout = QVBoxLayout()
        
        self.hls_check = QCheckBox("Enable HLS streaming support")
        self.hls_check.setChecked(self.settings_manager.get("hls_enabled", HLS_ENABLED))
        media_layout.addWidget(self.hls_check)
        
        self.drm_check = QCheckBox("Enable DRM content (Widevine)")
        self.drm_check.setChecked(self.settings_manager.get("drm_enabled", DRM_ENABLED))
        media_layout.addWidget(self.drm_check)
        
        media_group.setLayout(media_layout)
        general_layout.addRow(media_group)
        
        general_tab.setLayout(general_layout)
        
        # Privacy Settings Tab
        privacy_tab = QWidget()
        privacy_layout = QFormLayout()
        
        # Content settings
        content_group = QGroupBox("Content Settings")
        content_layout = QVBoxLayout()
        
        self.ad_blocker_check = QCheckBox("Enable ad blocker")
        self.ad_blocker_check.setChecked(self.settings_manager.get("ad_blocker"))
        content_layout.addWidget(self.ad_blocker_check)
        
        self.js_check = QCheckBox("Enable JavaScript")
        self.js_check.setChecked(self.settings_manager.get("javascript_enabled"))
        content_layout.addWidget(self.js_check)
        
        self.images_check = QCheckBox("Load images automatically")
        self.images_check.setChecked(self.settings_manager.get("auto_load_images"))
        content_layout.addWidget(self.images_check)
        
        content_group.setLayout(content_layout)
        privacy_layout.addRow(content_group)
        
        # User agent settings
        ua_group = QGroupBox("User Agent")
        ua_layout = QVBoxLayout()
        
        self.user_agent_edit = QLineEdit(self.settings_manager.get("user_agent", USER_AGENT))
        ua_layout.addWidget(self.user_agent_edit)
        
        preset_ua_layout = QHBoxLayout()
        desktop_ua_btn = QPushButton("Desktop")
        mobile_ua_btn = QPushButton("Mobile")
        custom_ua_btn = QPushButton("Custom")
        
        desktop_ua_btn.clicked.connect(lambda: self.user_agent_edit.setText(USER_AGENT))
        mobile_ua_btn.clicked.connect(lambda: self.user_agent_edit.setText(
            "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
        ))
        
        preset_ua_layout.addWidget(desktop_ua_btn)
        preset_ua_layout.addWidget(mobile_ua_btn)
        preset_ua_layout.addWidget(custom_ua_btn)
        ua_layout.addLayout(preset_ua_layout)
        
        ua_group.setLayout(ua_layout)
        privacy_layout.addRow(ua_group)
        
        privacy_tab.setLayout(privacy_layout)
        
        # Shortcuts Tab
        shortcuts_tab = QWidget()
        shortcuts_layout = QVBoxLayout(shortcuts_tab)
        
        # Create scroll area for shortcuts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Organized shortcut categories
        categories = [
            ("Navigation", [
                ("Back", "back", "Alt+Left"),
                ("Forward", "forward", "Alt+Right"),
                ("Reload", "reload", "F5"),
                ("Hard Reload", "reload_ignore_cache", "Shift+F5"),
                ("Stop Loading", "stop", "Esc"),
                ("Home", "home", "Alt+Home")
            ]),
            ("Tab Management", [
                ("New Tab", "new_tab", "Ctrl+T"),
                ("Close Tab", "close_tab", "Ctrl+W"),
                ("Next Tab", "next_tab", "Ctrl+Tab"),
                ("Previous Tab", "prev_tab", "Ctrl+Shift+Tab"),
                ("Restore Closed Tab", "restore_tab", "Ctrl+Shift+T")
            ]),
            ("Focus & Search", [
                ("Focus Address Bar", "focus_url", "Ctrl+L"),
                ("Focus Search", "focus_search", "Ctrl+K"),
                ("Search Selected Text", "search_selected", "Ctrl+E"),
                ("Autocomplete URL", "autocomplete_url", "Ctrl+Return")
            ]),
            ("Bookmarks", [
                ("Bookmark Search", "bookmark_search", "Ctrl+B"),
                ("Bookmark Current Page", "bookmark_page", "Ctrl+D")
            ]),
            ("Tools", [
                ("Downloads", "downloads", "Ctrl+J"),
                ("History", "history", "Ctrl+H"),
                ("Settings", "settings", "Ctrl+,"),
                ("Print", "print", "Ctrl+P"),
                ("Save as PDF", "print_pdf", "Ctrl+Shift+P")
            ]),
            ("Screenshots", [
                ("Capture Screenshot", "screenshot", "Ctrl+Shift+S"),
                ("Capture Full Page", "full_screenshot", "Ctrl+Alt+Shift+S"),
                ("Capture Region", "region_screenshot", "Ctrl+Shift+R")
            ]),
            ("Developer Tools", [
                ("Toggle DevTools", "dev_tools", "F12"),
                ("View Page Source", "view_source", "Ctrl+U")
            ]),
            ("Zoom", [
                ("Zoom In", "zoom_in", "Ctrl++"),
                ("Zoom Out", "zoom_out", "Ctrl+-"),
                ("Reset Zoom", "zoom_reset", "Ctrl+0")
            ])
        ]
        
        # Initialize shortcut editors dictionary
        self.shortcut_editors = {}
        
        # Create category groups
        for category_name, items in categories:
            group = QGroupBox(category_name)
            group_layout = QFormLayout()
            
            for label, name, default in items:
                current = self.settings_manager.get_shortcut(name) or default
                editor = QKeySequenceEdit(QKeySequence(current))
                self.shortcut_editors[name] = editor
                group_layout.addRow(f"{label}:", editor)
            
            group.setLayout(group_layout)
            scroll_layout.addWidget(group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        shortcuts_layout.addWidget(scroll)
        
        # Add reset button
        reset_btn = QPushButton("Reset All Shortcuts to Defaults")
        reset_btn.clicked.connect(self.reset_shortcuts_to_defaults)
        shortcuts_layout.addWidget(reset_btn, alignment=Qt.AlignRight)
        
        # Add all tabs
        tab_widget.addTab(general_tab, "General")
        tab_widget.addTab(privacy_tab, "Privacy")
        tab_widget.addTab(shortcuts_tab, "Shortcuts")
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, dialog
        )
        button_box.accepted.connect(lambda: self.save_settings(dialog))
        button_box.rejected.connect(dialog.reject)
        
        # Main layout
        main_layout = QVBoxLayout(dialog)
        main_layout.addWidget(tab_widget)
        main_layout.addWidget(button_box)
        
        # Apply dark mode if enabled
        if self.settings_manager.get("dark_mode"):
            self._apply_dark_mode_to_dialog(dialog)
        
        dialog.exec_()

    def reset_shortcuts_to_defaults(self):
        """Reset all keyboard shortcuts to their default values."""
        default_shortcuts = {
            "back": "Alt+Left",
            "forward": "Alt+Right",
            "reload": "F5",
            "reload_ignore_cache": "Shift+F5",
            "stop": "Esc",
            "home": "Alt+Home",
            "new_tab": "Ctrl+T",
            "close_tab": "Ctrl+W",
            "next_tab": "Ctrl+Tab",
            "prev_tab": "Ctrl+Shift+Tab",
            "restore_tab": "Ctrl+Shift+T",
            "focus_url": "Ctrl+L",
            "focus_search": "Ctrl+K",
            "bookmark_search": "Ctrl+B",
            "bookmark_page": "Ctrl+D",
            "downloads": "Ctrl+J",
            "history": "Ctrl+H",
            "settings": "Ctrl+,",
            "print": "Ctrl+P",
            "print_pdf": "Ctrl+Shift+P",
            "screenshot": "Ctrl+Shift+S",
            "full_screenshot": "Ctrl+Alt+Shift+S",
            "region_screenshot": "Ctrl+Shift+R",
            "search_selected": "Ctrl+E",
            "autocomplete_url": "Ctrl+Return",
            "dev_tools": "F12",
            "view_source": "Ctrl+U",
            "zoom_in": "Ctrl++",
            "zoom_out": "Ctrl+-",
            "zoom_reset": "Ctrl+0"
        }
        
        for name, editor in self.shortcut_editors.items():
            if name in default_shortcuts:
                editor.setKeySequence(QKeySequence(default_shortcuts[name]))

    def save_settings(self, dialog):
        """Save all settings to configuration file."""
        try:
            # General settings
            self.settings_manager.set("home_page", self.home_page_edit.text())
            self.settings_manager.set("search_engine", self.search_engine_edit.text())
            self.settings_manager.set("download_dir", self.download_dir_edit.text())
            
            # Appearance
            dark_mode = self.dark_mode_check.isChecked()
            self.settings_manager.set("dark_mode", dark_mode)
            if dark_mode:
                self.settings_manager.apply_dark_mode(QApplication.instance())
            
            # Media
            self.settings_manager.set("hls_enabled", self.hls_check.isChecked())
            self.settings_manager.set("drm_enabled", self.drm_check.isChecked())
            
            # Privacy
            self.settings_manager.set("ad_blocker", self.ad_blocker_check.isChecked())
            self.settings_manager.set("javascript_enabled", self.js_check.isChecked())
            self.settings_manager.set("auto_load_images", self.images_check.isChecked())
            self.settings_manager.set("user_agent", self.user_agent_edit.text())
            
            # Save shortcuts
            shortcuts = {
                name: editor.keySequence().toString()
                for name, editor in self.shortcut_editors.items()
            }
            self.settings_manager.set("shortcuts", shortcuts)
            
            # Reconfigure browser with new settings
            self.configure_webengine()
            self.setup_shortcuts()  # Reapply shortcuts
            
            dialog.accept()
            self.notification_manager.show_notification(
                "Settings Saved", 
                "Your preferences have been updated",
                3000
            )
            
        except Exception as e:
            logging.error(f"Error saving settings: {str(e)}")
            QMessageBox.warning(
                self,
                "Save Error",
                f"Failed to save settings: {str(e)}"
            )

    def _apply_dark_mode_to_dialog(self, dialog):
        """Apply consistent dark theme styling to settings dialog."""
        theme = self.settings_manager.get("dark_theme")
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {theme["base_color"]};
                color: {theme["text_color"]};
                font-size: 12px;
            }}
            QGroupBox {{
                border: 1px solid {theme["button_color"]};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                color: {theme["highlight_color"]};
                padding: 0 3px;
            }}
            QLineEdit, QComboBox, QKeySequenceEdit {{
                background-color: {theme["window_color"]};
                color: {theme["text_color"]};
                border: 1px solid {theme["button_color"]};
                padding: 5px;
                min-height: 24px;
            }}
            QPushButton {{
                background-color: {theme["button_color"]};
                color: {theme["text_color"]};
                border: 1px solid {theme["highlight_color"]};
                padding: 5px 10px;
                min-width: 80px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {theme["highlight_color"]};
            }}
            QCheckBox {{
                spacing: 5px;
            }}
            QTabWidget::pane {{
                border: 1px solid {theme["button_color"]};
            }}
            QTabBar::tab {{
                padding: 5px 10px;
            }}
        """)
            
# ====================== MAIN APPLICATION ======================
def main():
    # Enable High DPI scaling if available
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Storm Browser")
    app.setApplicationVersion("12.0")
    
    window = BrowserMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()