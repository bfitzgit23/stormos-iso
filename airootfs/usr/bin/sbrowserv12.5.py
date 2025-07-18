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
from PyQt5.QtCore import QSysInfo
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
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
import json
import logging
import subprocess
import time
import re
from PyQt5.QtCore import QSettings, QByteArray
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QMessageBox
import hashlib
import base64
import traceback
from datetime import datetime
import logging
from PyQt5.QtWidgets import (QCalendarWidget, QListWidget, QInputDialog)
from PyQt5.QtCore import QDate, QDateTime
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

from PyQt5.QtCore import QUrl, QStandardPaths, QDir
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
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






class PasswordManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("StormBrowser", "PasswordManager")
        self._init_encryption()
        
    def _init_encryption(self):
        """Initialize encryption using system-specific key with fallback"""
        key = self.settings.value("encryption_key")
        if not key:
            # Fallback method for older Qt versions
            try:
                # Try the modern way first (Qt 5.11+)
                machine_id = QSysInfo.machineUniqueId().toHex().data().decode('utf-8')
            except AttributeError:
                # Fallback for older Qt versions
                import uuid
                machine_id = str(uuid.getnode())
            
            system_data = (
                QGuiApplication.applicationName() + 
                QGuiApplication.organizationName() +
                str(QGuiApplication.applicationPid()) +
                machine_id
            ).encode('utf-8')
            
            key = base64.urlsafe_b64encode(hashlib.sha256(system_data).digest()[:32])
            self.settings.setValue("encryption_key", key.decode('utf-8'))
        
        # Ensure encryption_key is always bytes
        if isinstance(key, str):
            self.encryption_key = key.encode('utf-8')
        else:
            self.encryption_key = key
        
    def _xor_encrypt(self, text):
        """Simple XOR encryption using our key"""
        if isinstance(text, str):
            text = text.encode('utf-8')
        return base64.urlsafe_b64encode(
            bytes([text[i] ^ self.encryption_key[i % len(self.encryption_key)] 
                  for i in range(len(text))])
        ).decode('utf-8')
        
    def _xor_decrypt(self, encrypted_text):
        """XOR decryption using our key"""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
        decrypted = bytes([encrypted_bytes[i] ^ self.encryption_key[i % len(self.encryption_key)] 
                         for i in range(len(encrypted_bytes))])
        return decrypted.decode('utf-8')
        
    def save_password(self, url, username, password):
        """Store encrypted credentials"""
        passwords = self._get_passwords()
        domain = QUrl(url).host()
        passwords[domain] = {
            'url': url,
            'username': self._xor_encrypt(username),
            'password': self._xor_encrypt(password),
            'timestamp': datetime.now().isoformat()
        }
        self.settings.setValue("passwords", passwords)
        
    def get_password(self, url):
        """Retrieve decrypted credentials"""
        passwords = self._get_passwords()
        domain = QUrl(url).host()
        if domain in passwords:
            return {
                'username': self._xor_decrypt(passwords[domain]['username']),
                'password': self._xor_decrypt(passwords[domain]['password'])
            }
        return None
        
    def _get_passwords(self):
        """Get all stored passwords"""
        return self.settings.value("passwords", {})


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
# Define global paths
import os
import json
import time
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWebEngineWidgets import QWebEngineDownloadItem

DOWNLOAD_DIR = os.path.expanduser("~/Downloads")
COMPLETED_DOWNLOADS_FILE = os.path.join(DOWNLOAD_DIR, "completed_downloads.json")


def ensure_config_dir():
    """Ensure the download directory exists."""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)


def format_size(bytes_received):
    """Format bytes into human-readable size (e.g., 1.2 MB)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_received < 1024:
            return f"{bytes_received:.1f} {unit}"
        bytes_received /= 1024
    return f"{bytes_received:.1f} TB"


class DownloadManager(QObject):
    # Signals to notify UI about changes
    download_progress = pyqtSignal(str, int, int, str, str)  # filename, received, total, speed, eta
    download_finished = pyqtSignal(str, bool, str)          # path, success, filename
    download_started = pyqtSignal(str, str)                 # filename, size
    download_list_updated = pyqtSignal()                    # Signal for list refresh

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_downloads = {}  # {download_id: {filename, path, item, start_time, last_update, ...}}
        self.completed_downloads = []  # List of completed download dicts
        ensure_config_dir()
        self.load_completed_downloads()

    def handle_download(self, download_item):
        """
        Handle a new download request from QWebEngineView.
        Assigns a unique ID and tracks the download.
        """
        filename = download_item.suggestedFileName() or f"download_{int(time.time())}"
        path = self._get_unique_path(filename)
        download_item.setPath(path)

        download_id = int(time.time() * 1000)

        # Prevent duplicate IDs
        if download_id in self.active_downloads:
            print(f"[WARNING] Duplicate download ID: {download_id}")
            return

        self.active_downloads[download_id] = {
            "item": download_item,
            "filename": filename,
            "path": path,
            "start_time": time.time(),
            "last_update": time.time(),
            "last_bytes": 0,
            "speed": 0,
            "received": 0,
            "total": 0
        }

        self.download_started.emit(filename, "0 B")
        download_item.accept()

        # Connect signals only once per download item
        download_item.downloadProgress.connect(lambda r, t: self._on_download_progress(download_id, r, t))
        download_item.finished.connect(lambda: self._on_download_finished(download_id))

    def _get_unique_path(self, filename):
        """Generate a unique path to avoid overwriting existing files."""
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(DOWNLOAD_DIR, filename)):
            filename = f"{base}({counter}){ext}"
            counter += 1
        return os.path.join(DOWNLOAD_DIR, filename)

    def _on_download_progress(self, download_id, received, total):
        """Handle download progress updates."""
        if download_id not in self.active_downloads:
            return

        download = self.active_downloads[download_id]
        now = time.time()
        time_elapsed = now - download["last_update"]

        if time_elapsed > 0:
            bytes_diff = received - download["last_bytes"]
            download["speed"] = bytes_diff / time_elapsed  # bytes per second

        download["last_update"] = now
        download["last_bytes"] = received
        download["received"] = received
        download["total"] = total

        percent = (received / total * 100) if total > 0 else 0
        speed_str = f"{format_size(download['speed'])}/s"
        eta_seconds = max(0, int((total - received) / download["speed"])) if download["speed"] > 0 else 0
        eta_str = format_size(eta_seconds) if eta_seconds > 0 else "Calculating..."

        self.download_progress.emit(
            download["filename"], received, total, speed_str, eta_str
        )

    def _on_download_finished(self, download_id):
        if download_id not in self.active_downloads:
            return

        download = self.active_downloads.pop(download_id)
        
        # Determine if the download was successful
        if hasattr(download["item"], "state"):
            success = download["item"].state() == QWebEngineDownloadItem.DownloadCompleted
        else:
            success = True  # Assume success if state is not available

        # Add to completed downloads list
        self.completed_downloads.append({
            "filename": download["filename"],
            "path": download["path"],
            "timestamp": download["start_time"],
            "received": download.get("received", 0),
            "total": download.get("total", 0),
            "success": success
        })

        # Emit signal for UI update
        self.download_finished.emit(download["path"], success, download["filename"])

        # Save completed downloads to disk
        self.save_completed_downloads()

        # Notify UI that the list has changed
        self.download_list_updated.emit()

    def save_completed_downloads(self):
        """
        Save completed downloads to a JSON file.
        If no downloads exist, the file will be written as an empty list.
        """
        try:
            with open(COMPLETED_DOWNLOADS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.completed_downloads, f, indent=4)
            print(f"[DEBUG] Saved {len(self.completed_downloads)} completed downloads.")
        except Exception as e:
            print(f"[ERROR] Failed to save completed downloads: {e}")

    def load_completed_downloads(self):
        """Load completed downloads from disk."""
        if os.path.exists(COMPLETED_DOWNLOADS_FILE):
            try:
                with open(COMPLETED_DOWNLOADS_FILE, "r", encoding="utf-8") as f:
                    self.completed_downloads = json.load(f)
            except Exception as e:
                print(f"[ERROR] Failed to load completed downloads: {e}")

    def get_active_downloads(self):
        """Return active download items for UI display."""
        return self.active_downloads.values()

    def get_completed_downloads(self):
        """Return completed download items for UI display."""
        return self.completed_downloads

    def clear_all_downloads(self):
        """Clear all active and completed downloads from memory."""
        self.active_downloads.clear()
        self.completed_downloads.clear()
        self.save_completed_downloads()
        self.download_list_updated.emit()

    def clear_completed_downloads(self):
        """Clear completed downloads list and delete the file from disk."""
        # Clear in-memory list
        self.completed_downloads = []
        
        # Delete the file if it exists
        if os.path.exists(COMPLETED_DOWNLOADS_FILE):
            try:
                os.remove(COMPLETED_DOWNLOADS_FILE)
                print(f"[DEBUG] Deleted {COMPLETED_DOWNLOADS_FILE}")
            except Exception as e:
                print(f"[ERROR] Could not delete download history file: {e}")
        
        # Notify UI that the list has changed
        self.download_list_updated.emit()

    def cancel_download(self, download_id):
        """Cancel a specific active download by ID."""
        if download_id in self.active_downloads:
            download = self.active_downloads[download_id]
            if 'item' in download:
                download['item'].cancel()
            del self.active_downloads[download_id]
            self.download_list_updated.emit()

    def remove_completed_download(self, index):
        """Remove a specific completed download by index."""
        if 0 <= index < len(self.completed_downloads):
            del self.completed_downloads[index]
            self.save_completed_downloads()
            self.download_list_updated.emit()
            
# ====================== BOOKMARK MANAGER ======================
class BookmarkManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        ensure_config_dir()
        self.bookmarks = load_json_file(BOOKMARKS_FILE, {"folders": {"Main": []}})

    def add_bookmark(self, url, title, folder="Main", description=""):
        """
        Add a new bookmark to the specified folder.
        
        Args:
            url (str): URL of the bookmark.
            title (str): Title or name of the bookmark.
            folder (str): Folder name to categorize the bookmark (default: "Main").
            description (str): Optional description for the bookmark.
        """
        # Create the folder if it doesn't exist
        if folder not in self.bookmarks["folders"]:
            self.bookmarks["folders"][folder] = []

        # Append the new bookmark with a timestamp and optional description
        self.bookmarks["folders"][folder].append({
            "url": url,
            "title": title,
            "description": description,
            "date": datetime.now().isoformat()
        })

        # Save bookmarks to file
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




    def closeEvent(self, event):
        """Handle the event when the window is being closed."""
        # Iterate over all tabs and aggressively stop media playback
        for index in range(self.tab_widget.count()):
            tab_widget = self.tab_widget.widget(index)
            if tab_widget:
                browser = tab_widget.findChild(QWebEngineView)
                if browser:
                    browser.page().runJavaScript("""s
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

class BlobUrlInterceptor(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        if info.requestUrl().scheme() == 'blob':
            info.setAllowed(True)


# =================================================================
class BrowserCalendar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BrowserCalendarWidget")
        self.notes = {}  # Dictionary to store notes by date
        self.setup_ui()
        self.setup_timers()
        self.load_events()
        self.load_notes_from_file()  # Load saved notes on startup
        self.show_events_for_date(QDate.currentDate())
        self.show_notes_for_date(QDate.currentDate())

    def setup_ui(self):
        """Initialize all UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Calendar Widget
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        layout.addWidget(self.calendar)

        # 🔴 Connect calendar click to show notes
        self.calendar.clicked.connect(self.show_notes_for_date)

        # Events List
        self.event_list = QListWidget()
        self.event_list.setAlternatingRowColors(True)
        self.event_list.itemDoubleClicked.connect(self.on_event_clicked)
        layout.addWidget(self.event_list)

        # Tab Widget for Notes
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Notes Tab
        notes_tab = QWidget()
        notes_layout = QVBoxLayout(notes_tab)

        self.notes_text = QTextEdit()
        notes_layout.addWidget(self.notes_text)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Notes")
        delete_btn = QPushButton("Delete Notes")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(delete_btn)
        notes_layout.addLayout(btn_layout)

        self.tab_widget.addTab(notes_tab, "Notes")

        # Connect Notes Buttons
        save_btn.clicked.connect(self.save_notes)
        delete_btn.clicked.connect(self.delete_notes)

        # Button Row
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Event")
        self.edit_btn = QPushButton("Edit Event")
        self.delete_btn = QPushButton("Delete Event")  # NEW BUTTON
        self.show_all_btn = QPushButton("Show All")

        self.add_btn.clicked.connect(self.show_add_event_dialog)
        self.edit_btn.clicked.connect(self.show_edit_event_dialog)
        self.delete_btn.clicked.connect(self.delete_selected_event)  # NEW CONNECTION
        self.show_all_btn.clicked.connect(self.show_all_events)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)  # ADD TO LAYOUT
        btn_layout.addWidget(self.show_all_btn)
        layout.addLayout(btn_layout)

        # Status Label
        self.status_label = QLabel()
        self.update_date_time_label()
        layout.addWidget(self.status_label)

    def setup_timers(self):
        """Initialize all timers"""
        # Reminder check timer
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(60000)  # 1 minute

        # Clock update timer
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_date_time_label)
        self.clock_timer.start(1000)  # 1 second

    def show_notes_for_date(self, qdate):
        """Display notes for the selected date."""
        date_str = qdate.toString("yyyy-MM-dd")
        self.notes_text.setPlainText(self.notes.get(date_str, ""))

    def save_notes(self):
        """Save notes for the currently selected date."""
        date_str = self.calendar.selectedDate().toString("yyyy-MM-dd")
        text = self.notes_text.toPlainText()
        if text.strip():
            self.notes[date_str] = text
        else:
            self.notes.pop(date_str, None)  # Remove empty notes

        # Save to file for persistence
        self.save_notes_to_file()

        # Show status message
        main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'status_bar'):
            main_window.status_bar.showMessage(f"Notes saved for {date_str}", 2000)


    def delete_selected_event(self):
        """Delete the selected event from the calendar."""
        date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        selected_items = self.event_list.selectedItems()
        
        if not selected_items or date not in self.events:
            QMessageBox.information(self, "No Selection", "Please select an event to delete")
            return

        selected_text = selected_items[0].text()
        
        if ": " in selected_text:
            time_part = selected_text.split(": ")[0]
            if "⏰" in time_part:
                time_str = time_part.replace("⏰", "").strip()

                for i, event in enumerate(self.events[date]):
                    if event["time"] == time_str:
                        reply = QMessageBox.question(
                            self, "Confirm Delete",
                            f"Delete event '{event['name']}' at {event['time']}?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        if reply == QMessageBox.Yes:
                            del self.events[date][i]
                            if not self.events[date]:
                                del self.events[date]
                            self.save_events()
                            self.show_events_for_date(self.calendar.selectedDate())
                        break
                else:
                    QMessageBox.warning(self, "Error", "Could not find selected event")
            else:
                QMessageBox.warning(self, "Error", "Invalid event format")
        else:
            QMessageBox.warning(self, "Error", "Could not parse event time")

    def delete_notes(self):
        """Delete notes for the selected date."""
        date_str = self.calendar.selectedDate().toString("yyyy-MM-dd")
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Delete notes for {date_str}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.notes.pop(date_str, None)
            self.notes_text.clear()
            self.save_notes_to_file()

            main_window = self.get_main_window()
            if main_window and hasattr(main_window, 'status_bar'):
                main_window.status_bar.showMessage(f"Notes deleted for {date_str}", 2000)

    def get_main_window(self):
        """Helper to safely get the QMainWindow (main browser window)"""
        parent = self.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        return parent

    def save_notes_to_file(self, filename="calendar_notes.json"):
        """Save notes dictionary to JSON file"""
        try:
            with open(filename, "w") as f:
                json.dump(self.notes, f)
        except Exception as e:
            print(f"Error saving notes: {e}")

    def load_notes_from_file(self, filename="calendar_notes.json"):
        """Load notes dictionary from JSON file"""
        try:
            with open(filename, "r") as f:
                self.notes = json.load(f)
        except FileNotFoundError:
            self.notes = {}
        except Exception as e:
            print(f"Error loading notes: {e}")
            self.notes = {}


    def load_events(self):
        """Load events from JSON file"""
        self.events = {}
        event_file = os.path.expanduser("~/Documents/browser_events.json")
        try:
            if os.path.exists(event_file):
                with open(event_file, 'r') as f:
                    self.events = json.load(f)
        except Exception as e:
            print(f"Error loading events: {e}")

    def save_events(self):
        """Save events to JSON file"""
        event_file = os.path.expanduser("~/Documents/browser_events.json")
        try:
            os.makedirs(os.path.dirname(event_file), exist_ok=True)
            with open(event_file, 'w') as f:
                json.dump(self.events, f, indent=2)
        except Exception as e:
            print(f"Error saving events: {e}")

    def update_date_time_label(self):
        """Update the time display"""
        current = QDateTime.currentDateTime()
        self.status_label.setText(current.toString("dddd, MMMM d, yyyy - hh:mm:ss AP"))

    def show_events_for_date(self, date):
        """Display events for selected date"""
        date_str = date.toString("yyyy-MM-dd")
        self.event_list.clear()
        
        if date_str in self.events:
            self.event_list.addItem(f"Events for {date.toString('MMMM d, yyyy')}:")
            for event in sorted(self.events[date_str], key=lambda x: x['time']):
                reminder = " 🔔" if event.get("reminder") else ""
                self.event_list.addItem(f"⏰ {event['time']}: {event['name']}{reminder}")
        else:
            self.event_list.addItem("No events scheduled")

    def show_all_events(self):
        """Show all events sorted chronologically"""
        self.event_list.clear()
        self.event_list.addItem("All Events:")
        
        for date in sorted(self.events.keys()):
            for event in sorted(self.events[date], key=lambda x: x['time']):
                reminder = " 🔔" if event.get("reminder") else ""
                self.event_list.addItem(
                    f"{QDate.fromString(date, 'yyyy-MM-dd').toString('MMM d')}: "
                    f"{event['time']} - {event['name']}{reminder}"
                )

    def on_event_clicked(self, item):
        """Handle event item clicks"""
        text = item.text()
        if ":" in text and "-" in text:  # All events format
            date_part = text.split(":")[0].strip()
            date = QDate.fromString(date_part, "MMM d")
            self.calendar.setSelectedDate(date)

    def show_add_event_dialog(self):
        """Show dialog to add new event"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Event")
        layout = QVBoxLayout(dialog)
        
        # Event Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.event_name_edit = QLineEdit()
        name_layout.addWidget(self.event_name_edit)
        layout.addLayout(name_layout)
        
        # Date/Time
        date_time_layout = QHBoxLayout()
        
        date_group = QGroupBox("Date")
        date_layout = QVBoxLayout()
        self.date_edit = QCalendarWidget()
        self.date_edit.setSelectedDate(self.calendar.selectedDate())
        date_layout.addWidget(self.date_edit)
        date_group.setLayout(date_layout)
        
        time_group = QGroupBox("Time")
        time_layout = QVBoxLayout()
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime.currentTime())
        time_layout.addWidget(self.time_edit)
        time_group.setLayout(time_layout)
        
        date_time_layout.addWidget(date_group)
        date_time_layout.addWidget(time_group)
        layout.addLayout(date_time_layout)
        
        # Reminder
        self.reminder_check = QCheckBox("Set Reminder")
        layout.addWidget(self.reminder_check)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self.add_event(dialog))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.exec_()

    def add_event(self, dialog):
        """Add new event from dialog"""
        name = self.event_name_edit.text().strip()
        date = self.date_edit.selectedDate().toString("yyyy-MM-dd")
        time = self.time_edit.time().toString("HH:mm")
        
        if name:
            event = {
                "name": name,
                "time": time,
                "reminder": self.reminder_check.isChecked()
            }
            
            if date not in self.events:
                self.events[date] = []
                
            self.events[date].append(event)
            self.save_events()
            self.show_events_for_date(self.date_edit.selectedDate())
            dialog.accept()

    def show_edit_event_dialog(self):
        """Show dialog to edit existing event"""
        date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        if date not in self.events or not self.events[date]:
            QMessageBox.information(self, "No Events", "No events to edit on selected date")
            return
            
        # Select event
        event_names = [e["name"] for e in self.events[date]]
        event_name, ok = QInputDialog.getItem(
            self, "Edit Event", "Select event:", event_names, 0, False)
        
        if ok and event_name:
            event_idx = next(i for i, e in enumerate(self.events[date]) 
                          if e["name"] == event_name)
            event = self.events[date][event_idx]
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Event")
            layout = QVBoxLayout(dialog)
            
            # Event Name
            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("Name:"))
            self.edit_name_edit = QLineEdit()
            self.edit_name_edit.setText(event["name"])
            name_layout.addWidget(self.edit_name_edit)
            layout.addLayout(name_layout)
            
            # Date/Time
            date_time_layout = QHBoxLayout()
            
            date_group = QGroupBox("Date")
            date_layout = QVBoxLayout()
            self.edit_date_edit = QCalendarWidget()
            self.edit_date_edit.setSelectedDate(QDate.fromString(date, "yyyy-MM-dd"))
            date_layout.addWidget(self.edit_date_edit)
            date_group.setLayout(date_layout)
            
            time_group = QGroupBox("Time")
            time_layout = QVBoxLayout()
            self.edit_time_edit = QTimeEdit()
            self.edit_time_edit.setTime(QTime.fromString(event["time"], "HH:mm"))
            time_layout.addWidget(self.edit_time_edit)
            time_group.setLayout(time_layout)
            
            date_time_layout.addWidget(date_group)
            date_time_layout.addWidget(time_group)
            layout.addLayout(date_time_layout)
            
            # Reminder
            self.edit_reminder_check = QCheckBox("Set Reminder")
            self.edit_reminder_check.setChecked(event.get("reminder", False))
            layout.addWidget(self.edit_reminder_check)
            
            # Buttons
            buttons = QDialogButtonBox(
                QDialogButtonBox.Save | QDialogButtonBox.Cancel)
            buttons.accepted.connect(
                lambda: self.save_edited_event(date, event_idx, dialog))
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            dialog.exec_()

    def save_edited_event(self, old_date, event_idx, dialog):
        """Save edited event"""
        new_name = self.edit_name_edit.text().strip()
        new_date = self.edit_date_edit.selectedDate().toString("yyyy-MM-dd")
        new_time = self.edit_time_edit.time().toString("HH:mm")
        
        if new_name:
            updated_event = {
                "name": new_name,
                "time": new_time,
                "reminder": self.edit_reminder_check.isChecked()
            }
            
            # Remove from old position
            event = self.events[old_date].pop(event_idx)
            
            # Add to new date
            if new_date not in self.events:
                self.events[new_date] = []
            self.events[new_date].append(updated_event)
            
            # Clean up empty dates
            if not self.events[old_date]:
                del self.events[old_date]
                
            self.save_events()
            self.show_events_for_date(self.edit_date_edit.selectedDate())
            dialog.accept()

    def check_reminders(self):
        """Check for events needing reminders"""
        current_date = QDate.currentDate().toString("yyyy-MM-dd")
        current_time = QTime.currentTime().toString("HH:mm")
        
        if current_date in self.events:
            for event in self.events[current_date]:
                if event.get("reminder") and event["time"] == current_time:
                    self.show_reminder_notification(event)
                    event["reminder"] = False  # Disable after showing
                    self.save_events()

    def show_reminder_notification(self, event):
        """Show reminder popup"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Event Reminder")
        msg.setText(f"⏰ Reminder: {event['name']} at {event['time']}")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()



class FaviconManager(QObject):
    favicon_ready = pyqtSignal(str, QIcon)  # Signal emitted when favicon is loaded
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.network_manager = QNetworkAccessManager(self)
        self.favicon_cache = {}
        self.cache_dir = os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.CacheLocation), 
            "favicons"
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        self._setup_cache_cleanup()
        
        # Connect signals
        self.network_manager.finished.connect(self._on_favicon_downloaded)
        
    def _setup_cache_cleanup(self):
        """Setup periodic cache cleanup"""
        self.cache_cleanup_timer = QTimer(self)
        self.cache_cleanup_timer.timeout.connect(self._cleanup_cache)
        self.cache_cleanup_timer.start(24 * 60 * 60 * 1000)  # Daily cleanup

    def _cleanup_cache(self, max_age_days=30, max_size_mb=50):
        """Clean up old or oversized cache"""
        total_size = 0
        now = time.time()
        
        for filename in os.listdir(self.cache_dir):
            filepath = os.path.join(self.cache_dir, filename)
            try:
                stat = os.stat(filepath)
                file_age = (now - stat.st_mtime) / (24 * 3600)  # in days
                
                # Delete if too old
                if file_age > max_age_days:
                    os.unlink(filepath)
                    continue
                    
                # Count size for active files
                total_size += stat.st_size
                
            except Exception as e:
                print(f"Cache cleanup error for {filepath}: {str(e)}")
        
        # Convert to MB
        total_size_mb = total_size / (1024 * 1024)
        
        # If cache is too big, delete oldest files
        if total_size_mb > max_size_mb:
            files = []
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    stat = os.stat(filepath)
                    files.append((stat.st_mtime, filepath))
                except:
                    continue
            
            # Sort by oldest first
            files.sort()
            
            # Delete until we're under the limit
            for mtime, filepath in files:
                if total_size_mb <= max_size_mb * 0.8:  # Stop at 80% of limit
                    break
                try:
                    size = os.path.getsize(filepath)
                    os.unlink(filepath)
                    total_size_mb -= size / (1024 * 1024)
                except:
                    continue

    def get_favicon(self, url):
        """Get favicon for given URL with improved handling"""
        if not url:
            return QIcon()
            
        parsed = QUrl(url)
        if not parsed.isValid():
            return QIcon()
            
        domain = parsed.host()
        if not domain:
            return QIcon()
            
        # Normalize domain (remove www. if present)
        domain = domain.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # Check memory cache first
        if domain in self.favicon_cache:
            return self.favicon_cache[domain]
            
        # Check disk cache
        favicon_path = os.path.join(self.cache_dir, f"{domain}.ico")
        if os.path.exists(favicon_path):
            try:
                # Validate the cached file
                if os.path.getsize(favicon_path) > 0:
                    icon = QIcon(favicon_path)
                    if not icon.isNull():
                        self.favicon_cache[domain] = icon
                        return icon
                # If invalid, delete it
                os.unlink(favicon_path)
            except Exception as e:
                print(f"Error loading cached favicon: {str(e)}")
                
        # Try multiple favicon locations
        favicon_urls = [
            f"https://{domain}/favicon.ico",
            f"http://{domain}/favicon.ico",
            f"https://www.{domain}/favicon.ico",
            f"http://www.{domain}/favicon.ico",
            parsed.toString() + "/favicon.ico"
        ]
        
        # Try each URL until we find one that works
        for favicon_url in favicon_urls:
            qurl = QUrl(favicon_url)
            if qurl.isValid():
                self._download_favicon(qurl, domain)
                break
                
        return QIcon()  # Return empty icon while loading

    def _download_favicon(self, url, domain):
        """Download favicon with proper timeout and redirect handling"""
        request = QNetworkRequest(url)
        request.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
        request.setRawHeader(b"User-Agent", b"Mozilla/5.0")
        
        reply = self.network_manager.get(request)
        
        # Set timeout (10 seconds)
        timer = QTimer(reply)
        timer.setSingleShot(True)
        timer.timeout.connect(reply.abort)
        timer.start(10000)
        
        # Store domain with reply for later identification
        reply.domain = domain

    def _on_favicon_downloaded(self, reply):
        """Handle completed favicon download"""
        domain = getattr(reply, 'domain', '')
        
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll().data()
            if data:  # Only proceed if we got data
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    icon = QIcon(pixmap)
                    if not icon.isNull():
                        self.favicon_cache[domain] = icon
                        
                        # Save to cache
                        favicon_path = os.path.join(self.cache_dir, f"{domain}.ico")
                        try:
                            with open(favicon_path, 'wb') as f:
                                f.write(data)
                        except Exception as e:
                            print(f"Error saving favicon: {str(e)}")
                        
                        # Emit signal that favicon is ready
                        self.favicon_ready.emit(domain, icon)
        else:
            error = reply.errorString()
            if reply.error() != QNetworkReply.OperationCanceledError:
                print(f"Favicon download failed for {domain}: {error}")
                
        reply.deleteLater()

    def clear_cache(self):
        """Clear both memory and disk cache"""
        self.favicon_cache.clear()
        if os.path.exists(self.cache_dir):
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error deleting {file_path}: {str(e)}")

# ====================== MAIN BROWSER WINDOW ======================
class BrowserMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Set Adwaita as the icon theme
        from PyQt5.QtGui import QIcon
        QIcon.setThemeName("Adwaita")
        self.shortcuts = []

        self.setWindowTitle("Storm Browser v12 - Ultimate Edition")
        self.setMinimumSize(800, 600)
        self.showMaximized()

        # Initialize managers first
        self.settings_manager = SettingsManager(self)
        self.password_manager = PasswordManager(self)
        self.download_manager = DownloadManager(self)
        self.bookmark_manager = BookmarkManager(self)
        self.history_manager = HistoryManager(self)
        self.notification_manager = NotificationManager(self)
        
        # Initialize favicon manager
        self.favicon_manager = FaviconManager(self)
        self.favicon_manager.favicon_ready.connect(self.update_tab_favicon)
        
        # Initialize the URL interceptor
        self.url_interceptor = BlobUrlInterceptor()
        QWebEngineProfile.defaultProfile().setUrlRequestInterceptor(self.url_interceptor)

        # Setup UI components (this creates url_bar)
        self.setup_ui()
        

        # ⬇️ Add this block here
        try:
            self.tab_widget.tabCloseRequested.disconnect()
        except TypeError:
            pass  # No existing connection

        self.tab_widget.tabCloseRequested.connect(lambda idx: self.close_tab(idx))
        
        # Initialize autocomplete system AFTER url_bar exists
        self._init_autocomplete_system()
        
        # Rest of initialization
        self.setup_calendar()
        self.setup_connections()
        self.setup_shortcuts()
        self._setup_password_handling()

        # Apply dark mode if enabled
        if self.settings_manager.get("dark_mode"):
            self.settings_manager.apply_dark_mode(QApplication.instance())
        
        # Configure WebEngine settings
        self.configure_webengine()
        
        # Load initial page
        self.add_new_tab(QUrl(self.settings_manager.get("home_page")))


        self.closed_tabs = []  # Store recently closed tabs
        self.MAX_CLOSED_TABS = 10  # Limit how many to remember


    def _init_autocomplete_system(self):
        """Initialize the optimized autocomplete system"""
        # Cache setup
        self._autocomplete_cache = []
        self._last_cache_update = 0
        self.CACHE_TIMEOUT = 30  # seconds
        self.MIN_SEARCH_LENGTH = 2  # characters
        
        # Create completer
        self.url_completer = QCompleter()
        self.url_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.url_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.url_completer.setFilterMode(Qt.MatchContains)
        
        # Use standard item model for icons/tooltips
        self.url_completer_model = QStandardItemModel()
        self.url_completer.setModel(self.url_completer_model)
        self.url_bar.setCompleter(self.url_completer)
        
        # Setup debouncing timer
        self._autocomplete_timer = QTimer()
        self._autocomplete_timer.setSingleShot(True)
        self._autocomplete_timer.timeout.connect(self._perform_autocomplete_search)
        self.url_bar.textChanged.connect(self._schedule_autocomplete_update)

    def _schedule_autocomplete_update(self, text):
        """Debounce autocomplete updates"""
        self._autocomplete_timer.stop()
        if len(text) >= self.MIN_SEARCH_LENGTH:
            self._autocomplete_timer.start(150)  # 150ms delay after typing stops

    def _update_autocomplete_cache(self):
        """Refresh the suggestion cache"""
        current_time = time.time()
        if (current_time - self._last_cache_update) > self.CACHE_TIMEOUT:
            self._autocomplete_cache = []
            
            # Get bookmarks (faster access)
            bookmarks = self.bookmark_manager.get_all_bookmarks()
            for bookmark in bookmarks:
                self._autocomplete_cache.append((
                    bookmark['url'].lower(), 
                    bookmark['url'], 
                    'bookmark', 
                    bookmark['title']
                ))
                self._autocomplete_cache.append((
                    bookmark['title'].lower(), 
                    bookmark['title'], 
                    'bookmark', 
                    bookmark['url']
                ))
            
            # Get recent history (limited to 50 items)
            history = self.history_manager.get_history(limit=50)
            for entry in history:
                self._autocomplete_cache.append((
                    entry['url'].lower(),
                    entry['url'],
                    'history',
                    entry['title']
                ))
                self._autocomplete_cache.append((
                    entry['title'].lower(),
                    entry['title'],
                    'history',
                    entry['url']
                ))
            
            self._last_cache_update = current_time

    def _perform_autocomplete_search(self):
        """Perform the actual search with cached data"""
        search_text = self.url_bar.text().lower()
        if len(search_text) < self.MIN_SEARCH_LENGTH:
            self.url_completer_model.clear()
            return
            
        self._update_autocomplete_cache()
        self.url_completer_model.clear()
        
        # Simple substring matching (faster than regex for most cases)
        for cached_item in self._autocomplete_cache:
            if search_text in cached_item[0]:  # Search in pre-lowered text
                self._add_suggestion_to_model(
                    display_text=cached_item[1],
                    item_type=cached_item[2],
                    tooltip=cached_item[3]
                )

    def _add_suggestion_to_model(self, display_text, item_type, tooltip):
        """Efficiently add a suggestion to the model"""
        item = QStandardItem(display_text)
        item.setIcon(QIcon.fromTheme('bookmarks' if item_type == 'bookmark' else 'view-history'))
        item.setToolTip(f"{item_type.title()}: {tooltip}")
        self.url_completer_model.appendRow(item)

    def setup_ui(self):
        """Setup the main browser UI without any menu bar"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
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
        new_tab_btn.clicked.connect(self.add_new_tab)
        self.tab_widget.setCornerWidget(new_tab_btn, Qt.TopLeftCorner)
        
        layout.addWidget(self.tab_widget)

        # Navigation bar (now contains all essential controls)
        self.nav_bar = QToolBar("Navigation")
        self.nav_bar.setMovable(False)
        self.nav_bar.setIconSize(QSize(24, 24))
        self.addToolBar(self.nav_bar)

        # Navigation buttons
        self.back_btn = QAction("←", self)
        self.back_btn.setToolTip("Back")
        self.nav_bar.addAction(self.back_btn)

        self.forward_btn = QAction("→", self)
        self.forward_btn.setToolTip("Forward")
        self.nav_bar.addAction(self.forward_btn)

        self.refresh_btn = QAction("↻", self)
        self.refresh_btn.setToolTip("Refresh")
        self.nav_bar.addAction(self.refresh_btn)

        self.home_btn = QAction("⌂", self)
        self.home_btn.setToolTip("Home")
        self.nav_bar.addAction(self.home_btn)

        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search or enter URL")
        self.nav_bar.addWidget(self.url_bar)

        # Add calendar button to toolbar
        self.calendar_btn = QAction("📅", self)
        self.calendar_btn.setToolTip("Calendar")
        self.nav_bar.addAction(self.calendar_btn)

        # Add settings button to toolbar
        self.settings_btn = QAction("⚙", self)
        self.settings_btn.setToolTip("Settings")
        self.nav_bar.addAction(self.settings_btn)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Download progress bar
        self.download_progress_bar = QProgressBar()
        self.download_progress_bar.setTextVisible(False)
        self.download_progress_bar.setFixedHeight(3)
        self.download_progress_bar.hide()
        self.status_bar.addPermanentWidget(self.download_progress_bar)

    def setup_calendar(self):
        """Setup calendar with a Notes tab."""
        self.calendar_widget = BrowserCalendar(self)
        self.calendar_dock = QDockWidget("Calendar", self)
        self.calendar_dock.setWidget(self.calendar_widget)
        self.calendar_dock.setFeatures(QDockWidget.DockWidgetMovable |
                                        QDockWidget.DockWidgetClosable |
                                        QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.calendar_dock)
        self.calendar_dock.hide()
        
        # Connect calendar button
        self.calendar_btn.triggered.connect(self.toggle_calendar)

    def toggle_calendar(self):
        """Toggle calendar visibility"""
        self.calendar_dock.setVisible(not self.calendar_dock.isVisible())
    def show_calendar(self):
        """Handle calendar button click - toggle visibility"""
        if hasattr(self, 'calendar_dock'):
            self.calendar_dock.setVisible(not self.calendar_dock.isVisible())
        else:
            # Fallback if dock wasn't created
            if not hasattr(self, '_calendar_window') or not self._calendar_window:
                self._calendar_window = BrowserCalendar(self)
            self._calendar_window.show()

    def configure_webengine(self):
        """Configure WebEngine settings for HLS and DRM support."""
        settings = QWebEngineSettings.globalSettings()
        
        # Enable HLS if configured
        if self.settings_manager.get("hls_enabled", HLS_ENABLED):
            settings.setAttribute(
                QWebEngineSettings.PlaybackRequiresUserGesture, False
            )
        
        # Allow all URL schemes if configured
        if self.settings_manager.get("allow_unknown_url_schemes", False):
            settings.setAttribute(
                QWebEngineSettings.AllowAllUnknownUrlSchemes, True
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






# Then define the dark theme variant AFTER BrowserMainWindow is defined
class StormBrowserDark(BrowserMainWindow):
    def __init__(self):
        super().__init__()  # This will initialize closed_tabs from parent
        self.setWindowTitle("Sandoval Browser - Dark")
        self.apply_firefox_dark_theme()
        
    def apply_firefox_dark_theme(self):
        """Apply Firefox-inspired dark theme styling"""
        # Firefox Proton dark theme colors
        self.theme_colors = {
            "toolbar": "#23222b",
            "address_bar": "#42414d",
            "text": "#fbfbfe",
            "button_hover": "#52525e",
            "button_active": "#5b5b66",
            "tab_selected": "#15141a",
            "tab_unselected": "#23222b",
            "tab_hover": "#2f2f3a",
            "accent": "#45a1ff",
            "divider": "#1c1b22"
        }
        
        # Base stylesheet
        stylesheet = f"""
        /* Main window */
        QMainWindow {{
            background-color: {self.theme_colors["toolbar"]};
            color: {self.theme_colors["text"]};
        }}
        
        /* Tab bar */
        QTabBar {{
            background-color: {self.theme_colors["toolbar"]};
            spacing: 4px;
        }}
        
        QTabBar::tab {{
            background-color: {self.theme_colors["tab_unselected"]};
            color: {self.theme_colors["text"]};
            border: 0;
            border-radius: 4px 4px 0 0;
            padding: 6px 12px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {self.theme_colors["tab_selected"]};
            border-bottom: 2px solid {self.theme_colors["accent"]};
        }}
        
        QTabBar::tab:hover {{
            background-color: {self.theme_colors["tab_hover"]};
        }}
        
        /* Address bar */
        QLineEdit {{
            background-color: {self.theme_colors["address_bar"]};
            color: {self.theme_colors["text"]};
            border: 1px solid {self.theme_colors["divider"]};
            border-radius: 4px;
            padding: 5px 8px;
            selection-background-color: {self.theme_colors["accent"]};
        }}
        
        /* Toolbar buttons */
        QToolButton {{
            background-color: transparent;
            border: none;
            padding: 5px;
            border-radius: 4px;
        }}
        
        QToolButton:hover {{
            background-color: {self.theme_colors["button_hover"]};
        }}
        
        QToolButton:pressed {{
            background-color: {self.theme_colors["button_active"]};
        }}
        """
        
        self.setStyleSheet(stylesheet)
        
        # Configure tab bar
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setElideMode(Qt.ElideRight)
        
        # Update new tab button style
        if hasattr(self.tab_widget, 'cornerWidget'):
            new_tab_btn = self.tab_widget.cornerWidget()
            if new_tab_btn:
                new_tab_btn.setStyleSheet(f"""
                    QToolButton {{
                        background-color: {self.theme_colors["button_hover"]};
                        color: {self.theme_colors["text"]};
                        border-radius: 4px;
                        font-weight: bold;
                        min-width: 24px;
                        max-width: 24px;
                    }}
                    QToolButton:hover {{
                        background-color: {self.theme_colors["accent"]};
                    }}
                """)



    def setup_ui(self):
        """Setup the main browser UI with consistent styling."""
        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
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
        new_tab_btn.clicked.connect(self.add_new_tab)
        self.tab_widget.setCornerWidget(new_tab_btn, Qt.TopLeftCorner)
        
        layout.addWidget(self.tab_widget)

        # Navigation bar
        nav_bar = QToolBar("Navigation")
        nav_bar.setMovable(False)
        nav_bar.setIconSize(QSize(24, 24))
        
        # Set appropriate font size for text fallbacks
        font = self.font()
        font.setPointSize(12)
        nav_bar.setFont(font)
        
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
        QToolButton[popupMode="1"] {
            padding-right: 10px;
        }
        """
        
        nav_bar.setStyleSheet(button_style)

        # Navigation buttons with fallback text
        nav_buttons = [
            ("back", "go-previous", "Back", "←"),
            ("forward", "go-next", "Forward", "→"),
            ("refresh", "view-refresh", "Refresh", "↻"),
            ("home", "go-home", "Home", "⌂")
        ]

        for var_name, icon_name, tooltip, fallback_text in nav_buttons:
            btn = QAction(fallback_text, self)
            icon = QIcon.fromTheme(icon_name)
            if not icon.isNull():
                btn.setIcon(icon)
            btn.setToolTip(tooltip)
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

        # Right-side action buttons with fallback
        action_buttons = [
            ("print", "document-print", "Print page (Ctrl+P)", "🖨️", self.print_current_page),
            ("pdf", "document-export", "Save as PDF (Ctrl+Shift+P)", "📄", self.print_to_pdf),
            ("screenshot", "camera-photo", "Take screenshot (Ctrl+Shift+S)", "📷",
             lambda: self.take_screenshot("ask")),
            ("calendar", "view-calendar", "Calendar (Ctrl+Shift+C)", "📅", self.show_calendar),
            
        ]
        
        for var_name, icon_name, tooltip, fallback_text, handler in action_buttons:
            btn = QToolButton()
            icon = QIcon.fromTheme(icon_name)
            if icon.isNull():
                btn.setText(fallback_text)
            else:
                btn.setIcon(icon)
            
            btn.setToolTip(tooltip)
            btn.clicked.connect(handler)
            setattr(self, f"{var_name}_btn", btn)
            url_layout.addWidget(btn)
            
            # Special setup for screenshot button
            if var_name == "screenshot":
                btn.setPopupMode(QToolButton.MenuButtonPopup)
                menu = QMenu()
                actions = [
                    ("edit-copy", "Copy to Clipboard", "📋", "clipboard"),
                    ("document-save", "Save to File", "💾", "file"),
                    ("select-rectangular", "Capture Region", "⭕", "region")
                ]
                for icon_name, text, fallback_icon, mode in actions:
                    action = QAction(fallback_icon + " " + text, self)
                    icon = QIcon.fromTheme(icon_name)
                    if not icon.isNull():
                        action.setIcon(icon)
                    action.triggered.connect(lambda _, m=mode: self.take_screenshot(m))
                    menu.addAction(action)
                btn.setMenu(menu)

        # Add URL container to toolbar
        nav_bar.addWidget(url_container)

        # Right-side navigation buttons with fallback
        nav_buttons_right = [
            ("search", "system-search", "Search", "🔍"),
            ("bookmarks", "bookmarks", "Bookmarks", "📑"),
            ("downloads", "folder-download", "Downloads", "⏬"),
            ("history", "view-history", "History", "🕒"),
            ("settings", "preferences-system", "Settings", "⚙")
        ]

        for var_name, icon_name, tooltip, fallback_text in nav_buttons_right:
            btn = QAction(fallback_text, self)
            icon = QIcon.fromTheme(icon_name)
            if not icon.isNull():
                btn.setIcon(icon)
            btn.setToolTip(tooltip)
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

        # Connect tab close signal
        self.tab_widget.tabCloseRequested.connect(self.close_tab_handler)



    def start_region_screenshot(self):
        """Start capturing a custom rectangular region of the screen."""
        from PyQt5.QtWidgets import QApplication, QLabel, QRubberBand
        from PyQt5.QtCore import Qt, QRect

        # Create overlay and capture logic similar to what was pasted earlier
        self.screenshot_overlay = QLabel(self)
        self.screenshot_overlay.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.screenshot_overlay.setAttribute(Qt.WA_TranslucentBackground)
        self.screenshot_overlay.setStyleSheet("background-color: rgba(0,0,0,0.5);")
        self.screenshot_overlay.setGeometry(self.geometry())
        
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self.screenshot_overlay)
        self.screenshot_overlay.mousePressEvent = self.region_mouse_press
        self.screenshot_overlay.mouseMoveEvent = self.region_mouse_move
        self.screenshot_overlay.mouseReleaseEvent = self.region_mouse_release
        
        self.screenshot_overlay.show()

    def region_mouse_press(self, event):
        self.origin = event.pos()
        self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())
        self.rubber_band.show()

    def region_mouse_move(self, event):
        if self.rubber_band.isVisible():
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def region_mouse_release(self, event):
        rect = self.rubber_band.geometry()
        self.rubber_band.hide()
        self.screenshot_overlay.hide()
        
        # Finalize the capture
        self._capture_region_final(rect)


    def close_tab_handler(self, index):
        """Properly clean up web engine before closing tab"""
        widget = self.tab_widget.widget(index)
        
        if widget:
            # Find the web view in the tab
            webview = widget.findChild(QWebEngineView)
            if webview:
                # Stop media playback
                webview.page().setAudioMuted(True)
                webview.page().runJavaScript("""
                    document.querySelectorAll('video, audio').forEach(media => {
                        media.pause();
                        media.currentTime = 0;
                        media.removeAttribute('src');
                    });
                """)
                
                # Clear browsing data
                webview.page().profile().clearHttpCache()
                
                # Store closed tab info for possible restoration
                self.closed_tabs.append({
                    'url': webview.url().toString(),
                    'title': self.tab_widget.tabText(index),
                    'content': webview.page().toHtml(lambda html: html)
                })
                
                # Clean up the web view
                webview.setPage(QWebEnginePage())
                webview.page().deleteLater()
                webview.deleteLater()
        
        # Remove the tab
        self.tab_widget.removeTab(index)
        
        # If last tab was closed, create a new empty tab
        if self.tab_widget.count() == 0:
            self.add_new_tab(QUrl(self.settings_manager.get("home_page")))


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
        self.download_manager.download_list_updated.connect(self.update_downloads_lists)

    def _setup_password_handling(self):
        """Setup auto-save and auto-fill for passwords"""
        for i in range(self.tab_widget.count()):
            browser = self.tab_widget.widget(i).findChild(QWebEngineView)
            if browser:
                self._connect_password_handlers(browser)

    def _connect_password_handlers(self, browser):
        """Connect password handlers to a browser instance"""
        # Auto-fill detection
        browser.page().loadFinished.connect(
            lambda ok, browser=browser: self._auto_fill_passwords(browser) if ok else None)
        
        # Auto-save detection
        browser.page().featurePermissionRequested.connect(
            lambda url, feature, browser=browser: self._handle_password_save(browser, url, feature))

    def _auto_fill_passwords(self, browser):
        """Robust auto-fill that handles most modern login forms"""
        url = browser.url().toString()
        credentials = self.password_manager.get_password(url)
        if credentials:
            # JavaScript with comprehensive field detection
            js = """
            function fillCredentials(u, p) {
                // Priority list of username field selectors
                const userSelectors = [
                    'input[autocomplete="username"]',
                    'input[type="email"]', 
                    'input[name*="user"]',
                    'input[id*="user"]',
                    'input[name*="login"]',
                    'input[autocomplete="email"]',
                    'input[name="email"]'
                ];
                
                // Priority list of password field selectors
                const passSelectors = [
                    'input[autocomplete="current-password"]',
                    'input[type="password"]',
                    'input[name*="pass"]',
                    'input[id*="pass"]'
                ];
                
                // Fill first matching username field
                userSelectors.some(sel => {
                    const field = document.querySelector(sel);
                    if (field && !field.value) {
                        field.value = u;
                        return true;
                    }
                    return false;
                });
                
                // Fill first matching password field
                passSelectors.some(sel => {
                    const field = document.querySelector(sel);
                    if (field && !field.value) {
                        field.value = p;
                        return true;
                    }
                    return false;
                });
            }
            
            fillCredentials('%s', '%s');
            """ % (
                credentials['username'].replace("'", r"\'"),
                credentials['password'].replace("'", r"\'")
            )
            
            # Run with 1s delay to ensure all dynamic elements are loaded
            QTimer.singleShot(1000, lambda: browser.page().runJavaScript(js))

    def _handle_password_save(self, browser, url, feature):
        """Improved password save detection"""
        if feature == QWebEnginePage.Feature.PasswordManager:
            browser.page().runJavaScript("""
                function getFormData() {
                    try {
                        const forms = document.querySelectorAll('form');
                        for (const form of forms) {
                            const inputs = form.querySelectorAll('input');
                            let username = '';
                            let password = '';
                            
                            for (const input of inputs) {
                                if ((input.type === 'text' || input.type === 'email') && 
                                    !username && 
                                    (input.id.includes('user') || 
                                     input.name.includes('user') ||
                                     input.placeholder.includes('name'))) {
                                    username = input.value;
                                }
                                
                                if (input.type === 'password' && !password) {
                                    password = input.value;
                                }
                            }
                            
                            if (username && password) {
                                return {
                                    username: username,
                                    password: password
                                };
                            }
                        }
                        return null;
                    } catch (e) {
                        console.log('Password save error:', e);
                        return null;
                    }
                }
                getFormData();
            """, lambda result: self._save_password_data(url, result) if result else None)

    def _save_password_data(self, url, form_data):
        """Save password data after user confirmation"""
        if form_data and form_data.get('username') and form_data.get('password'):
            reply = QMessageBox.question(
                self,
                "Save Password?",
                "Would you like to save the password for this site?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.password_manager.save_password(
                    url.toString(),
                    form_data['username'],
                    form_data['password']
                )



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
        """Capture a custom region of the browser window."""
        # Create transparent overlay for region selection
        overlay = QLabel(self)
        overlay.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        overlay.setAttribute(Qt.WA_TranslucentBackground)
        overlay.setStyleSheet("background-color: rgba(0,0,0,0.5);")
        overlay.setGeometry(self.geometry())
        overlay.show()

        # Create selection rubber band
        rubber_band = QRubberBand(QRubberBand.Rectangle, overlay)
        rubber_band.setStyleSheet("border: 2px dashed blue;")

        start_pos = None
        selection_rect = None
        
        def mouse_press(event):
            nonlocal start_pos
            start_pos = event.pos()
            rubber_band.setGeometry(QRect(start_pos, QSize()))
            rubber_band.show()
        
        def mouse_move(event):
            if start_pos:
                rubber_band.setGeometry(QRect(start_pos, event.pos()).normalized())
        
        def mouse_release(event):
            nonlocal start_pos, selection_rect
            if start_pos:
                selection_rect = rubber_band.geometry()
                if selection_rect.width() > 10 and selection_rect.height() > 10:  # Minimum size
                    # Hide rubber band before capturing
                    rubber_band.hide()
                    overlay.hide()
                    
                    # Small delay to ensure UI updates before capture
                    QTimer.singleShot(50, lambda: self._capture_region_final(selection_rect))
                
                rubber_band.hide()
                overlay.hide()
                start_pos = None
        
        overlay.mousePressEvent = mouse_press
        overlay.mouseMoveEvent = mouse_move
        overlay.mouseReleaseEvent = mouse_release

    def _capture_region_final(self, rect):
        """Final step to capture the region after UI elements are hidden."""
        # Capture the selected region from the browser window
        screenshot = QPixmap(rect.size())
        painter = QPainter(screenshot)
        self.render(painter, QPoint(), QRegion(rect))
        painter.end()
        
        self._show_screenshot_options(screenshot)



    def setup_shortcuts(self):
        """Set up global keyboard shortcuts for the browser."""
        # Clear any existing shortcuts to avoid duplication
        if hasattr(self, 'shortcuts'):
            for shortcut in self.shortcuts:
                shortcut.setEnabled(False)
                shortcut.disconnect()
        self.shortcuts = []

        def _create_shortcut(key_sequence, callback):
            """Helper to create and store a QShortcut"""
            shortcut = QShortcut(QKeySequence(key_sequence), self)
            shortcut.setContext(Qt.ApplicationShortcut)  # Works globally
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)

        # Get current shortcut values from settings or use defaults
        get_shortcut = lambda action: self.settings_manager.get_shortcut(action)

        # === Navigation Shortcuts ===
        _create_shortcut(get_shortcut("back"), lambda: self.current_browser().back())
        _create_shortcut(get_shortcut("forward"), lambda: self.current_browser().forward())
        _create_shortcut(get_shortcut("reload"), lambda: self.current_browser().reload())
        _create_shortcut(get_shortcut("reload_ignore_cache"), lambda: self.current_browser().reloadAndBypassCache())
        _create_shortcut(get_shortcut("stop"), lambda: self.current_browser().stop())
        _create_shortcut(get_shortcut("home"), self.go_home)

        # === Tab Management ===
        _create_shortcut(get_shortcut("new_tab"), self.add_new_tab)
        _create_shortcut(get_shortcut("close_tab"), lambda: self.close_tab(self.tab_widget.currentIndex()))
        _create_shortcut(get_shortcut("next_tab"), self.focus_next_tab)
        _create_shortcut(get_shortcut("prev_tab"), self.focus_prev_tab)
        _create_shortcut(get_shortcut("restore_tab"), self.restore_closed_tab)

        # === Focus Shortcuts ===
        _create_shortcut(get_shortcut("focus_url"), self.focus_url_bar)
        _create_shortcut(get_shortcut("focus_search"), self.focus_search_bar)

        # === Tools and Features ===
        _create_shortcut(get_shortcut("bookmark_search"), self.show_bookmarks)
        _create_shortcut(get_shortcut("bookmark_page"), self.add_current_to_bookmarks)
        _create_shortcut(get_shortcut("downloads"), self.show_downloads)
        _create_shortcut(get_shortcut("history"), self.show_history)
        _create_shortcut(get_shortcut("print"), self.print_current_page)
        _create_shortcut(get_shortcut("print_pdf"), self.print_to_pdf)
        _create_shortcut(get_shortcut("screenshot"), lambda: self.take_screenshot("ask"))
        _create_shortcut(get_shortcut("full_screenshot"), lambda: self.take_full_page_screenshot())
        _create_shortcut(get_shortcut("region_screenshot"), lambda: self.start_region_screenshot())
        _create_shortcut(get_shortcut("dev_tools"), self.toggle_dev_tools)
        _create_shortcut(get_shortcut("view_source"), lambda: self.current_browser().page().runJavaScript("document.documentElement.outerHTML"))

        # === Zoom Shortcuts ===
        _create_shortcut(get_shortcut("zoom_in"), self.zoom_in)
        _create_shortcut(get_shortcut("zoom_out"), self.zoom_out)
        _create_shortcut(get_shortcut("zoom_reset"), self.zoom_reset)

        # === Search / URL Shortcuts ===
        _create_shortcut(get_shortcut("autocomplete_url"), self.autocomplete_url)
        _create_shortcut(get_shortcut("search_selected"), self.search_selected_text)

        # === Settings Shortcut (Dynamic) ===
        _create_shortcut(get_shortcut("settings"), self.show_settings)



    def _create_shortcut(self, key_sequence, callback):
        """Helper to create and store a QShortcut"""
        shortcut = QShortcut(QKeySequence(key_sequence), self)
        shortcut.setContext(Qt.ApplicationShortcut)  # Works globally
        shortcut.activated.connect(callback)
        return shortcut


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
        # Fix for setUrl() TypeError - ensure url is always a QUrl object
        if url is None:
            url = QUrl(self.settings_manager.get("home_page"))
        elif isinstance(url, str):
            url = QUrl(url)
        elif not isinstance(url, QUrl):
            url = QUrl()

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
        self.focus_url_bar()

        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Set up favicon handling
        browser.iconChanged.connect(self.update_tab_icon)
        self.update_tab_icon(browser.icon())

        # Request favicon
        self.load_favicon_for_url(url)

        return browser
    def load_favicon_for_url(self, url):
        """Load favicon for the given URL."""
        if not url or not url.host():
            return
            
        domain = url.host()
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # Use favicon manager to get or fetch the icon
        self.favicon_manager.get_favicon(url.toString())

    def update_tab_icon(self, icon):
        """Update the tab icon for the current browser."""
        current_browser = self.sender() or self.current_browser()
        if not current_browser:
            return
            
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i).findChild(QWebEngineView) == current_browser:
                self.tab_widget.setTabIcon(i, icon)
                break

    def update_tab_favicon(self, domain, icon):
        """Update tab icon when favicon is loaded."""
        current_browser = self.current_browser()
        if not current_browser:
            return
            
        current_domain = current_browser.url().host()
        if current_domain.startswith('www.'):
            current_domain = current_domain[4:]
            
        if current_domain == domain:
            self.update_tab_icon(icon)

    def update_tab_title(self, browser, title):
        """Update tab title when page title changes."""
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i).findChild(QWebEngineView) == browser:
                # Truncate long titles
                display_title = title[:20] + "..." if len(title) > 20 else title
                self.tab_widget.setTabText(i, display_title)
                self.tab_widget.setTabToolTip(i, title)
                
                # Update favicon if needed
                self.load_favicon_for_url(browser.url())
                break




        

    def update_urlbar(self, qurl):
        """Update the URL bar when navigation occurs.
        Only updates if the change comes from the current tab.
        Also updates the tab's favicon."""
        current_browser = self.current_browser()
        if current_browser and current_browser.url() == qurl:
            # Update URL text
            self.url_bar.setText(qurl.toString())
            self.url_bar.setCursorPosition(0)
            
            # Update tab title if empty (for new tabs)
            current_index = self.tab_widget.currentIndex()
            if not self.tab_widget.tabText(current_index) or self.tab_widget.tabText(current_index) == "New Tab":
                current_browser.page().titleChanged.connect(
                    lambda title: self.update_tab_title(current_browser, title)
                )
            
            # Add to history
            title = self.tab_widget.tabText(current_index)
            self.history_manager.add_history_entry(qurl.toString(), title)
            
            # Load favicon for this URL
            self.load_favicon_for_url(qurl)
            
            # Update SSL security icon (if you have one)
            if hasattr(self, 'security_icon'):
                self.update_security_icon(qurl)

    def on_tab_changed(self, index):
        """Handle tab changes to update URL bar and other UI elements."""
        if index >= 0:  # Check for valid index
            browser = self.tab_widget.widget(index).findChild(QWebEngineView)
            if browser:
                self.update_urlbar(browser.url())

    def close_tab(self, index):
        """
        Safely closes a tab at the given index without affecting adjacent tabs.
        Uses direct widget reference for reliability and avoids index shifting issues.
        """

        # Step 1: Validate index
        if index < 0 or index >= self.tab_widget.count():
            print(f"[ERROR] Invalid tab index: {index}")
            return

        # Step 2: Get the tab widget at this index
        tab_to_remove = self.tab_widget.widget(index)

        if not tab_to_remove:
            print(f"[ERROR] No widget found at index: {index}")
            return

        # Step 3: Find the QWebEngineView inside the tab
        browser = tab_to_remove.findChild(QWebEngineView)
        if browser:
            # Stop audio playback
            browser.page().setAudioMuted(True)

            # Pause all video/audio elements using JavaScript
            browser.page().runJavaScript("""
                document.querySelectorAll('video, audio').forEach(media => {
                    media.pause();
                    media.currentTime = 0;
                    media.src = '';
                    media.load();
                });
            """)

            # Store closed tab info for restoration
            if not hasattr(self, 'closed_tabs'):
                self.closed_tabs = []
            self.closed_tabs.append({
                'url': browser.url().toString(),
                'title': self.tab_widget.tabText(index),
                'timestamp': datetime.now().isoformat()
            })

            # Clean up resources
            browser.setPage(QWebEnginePage())
            browser.page().deleteLater()

        # Step 4: Remove only one tab at a time
        try:
            self.tab_widget.removeTab(index)
        except Exception as e:
            print(f"[ERROR] Failed to remove tab at index {index}: {str(e)}")
            return

        # Step 5: Ensure at least one tab remains open
        if self.tab_widget.count() == 0:
            self.add_new_tab(QUrl(self.settings_manager.get("home_page")))

        # Optional: Log confirmation
        print(f"[INFO] Tab closed successfully. Remaining tabs: {self.tab_widget.count()}")




    def restore_closed_tab(self):
        """Restore the most recently closed tab."""
        if hasattr(self, 'closed_tabs') and self.closed_tabs:
            tab_info = self.closed_tabs.pop()
            self.add_new_tab(QUrl(tab_info['url']), tab_info['title'])
        else:
            self.status_bar.showMessage("No tabs to restore", 2000)



    def update_urlbar(self, url):
        """Update the URL bar when navigation occurs."""
        url_string = url.toString()

        # Optionally hide 'about:blank' from showing in the URL bar
        if url_string == "about:blank":
            self.url_bar.clear()
        else:
            self.url_bar.setText(url_string)
            self.url_bar.setCursorPosition(0)

        # Optional: Automatically select all text in the URL bar
        # self.url_bar.selectAll()  # Uncomment if you want the URL highlighted every time

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
        """Show bookmarks dialog with search and import options."""
        # Create dialog if it doesn't exist
        if not hasattr(self, 'bookmarks_dialog') or not self.bookmarks_dialog:
            self.bookmarks_dialog = QDialog(self)
            self.bookmarks_dialog.setWindowTitle("Bookmarks")
            self.bookmarks_dialog.setMinimumSize(700, 600)

            layout = QVBoxLayout()
            
            # Search bar
            search_layout = QHBoxLayout()
            self.bookmark_search_bar = QLineEdit()
            self.bookmark_search_bar.setPlaceholderText("Search bookmarks...")
            self.bookmark_search_bar.textChanged.connect(self.filter_bookmarks)
            clear_btn = QPushButton("Clear")
            clear_btn.clicked.connect(lambda: [self.bookmark_search_bar.clear(), self.filter_bookmarks()])
            search_layout.addWidget(QLabel("Search:"))
            search_layout.addWidget(self.bookmark_search_bar)
            search_layout.addWidget(clear_btn)
            layout.addLayout(search_layout)

            # Import buttons
            import_layout = QHBoxLayout()
            chrome_btn = QPushButton("Import from Chrome")
            firefox_btn = QPushButton("Import from Firefox")
            import_layout.addWidget(chrome_btn)
            import_layout.addWidget(firefox_btn)
            layout.addLayout(import_layout)

            # Initialize bookmarks tree if it doesn't exist
            if not hasattr(self, 'bookmarks_tree') or not self.bookmarks_tree:
                self.bookmarks_tree = QTreeWidget()
                self.bookmarks_tree.setHeaderLabels(["Name", "URL", "Description", "Folder"])
                self.bookmarks_tree.setColumnWidth(0, 200)
                self.bookmarks_tree.setColumnWidth(1, 350)
                self.bookmarks_tree.setColumnWidth(2, 150)
                self.bookmarks_tree.itemDoubleClicked.connect(self.open_bookmark)
                self.bookmarks_tree.setContextMenuPolicy(Qt.CustomContextMenu)
                self.bookmarks_tree.customContextMenuRequested.connect(self.show_bookmark_context_menu)
            
            layout.addWidget(self.bookmarks_tree)

            # Buttons
            btn_layout = QHBoxLayout()
            add_btn = QPushButton("Add Current Page")
            remove_btn = QPushButton("Remove Selected")
            new_folder_btn = QPushButton("New Folder")
            btn_layout.addWidget(add_btn)
            btn_layout.addWidget(remove_btn)
            btn_layout.addWidget(new_folder_btn)
            layout.addLayout(btn_layout)

            # Connect signals
            chrome_btn.clicked.connect(lambda: self.import_bookmarks("chrome"))
            firefox_btn.clicked.connect(lambda: self.import_bookmarks("firefox"))
            add_btn.clicked.connect(self.add_current_to_bookmarks)
            remove_btn.clicked.connect(self.remove_selected_bookmark)
            new_folder_btn.clicked.connect(self.create_new_folder)

            self.bookmarks_dialog.setLayout(layout)
        
        self.refresh_bookmarks_tree()
        self.bookmarks_dialog.exec_()

    def open_bookmark(self, item, column):
        """Open bookmark in current tab."""
        if item.childCount() == 0:  # Not a folder
            bookmark = item.data(0, Qt.UserRole)
            if bookmark and self.current_browser():
                self.current_browser().setUrl(QUrl(bookmark["url"]))

    def filter_bookmarks(self):
        """Filter bookmarks based on search text."""
        search_text = self.bookmark_search_bar.text().lower()
        
        def filter_items(item):
            search_text = self.bookmark_search_bar.text().lower()
            
            if item.childCount() > 0:  # Folder
                any_visible = False
                for i in range(item.childCount()):
                    child = item.child(i)
                    if filter_items(child):
                        any_visible = True
                item.setHidden(not any_visible)
                return any_visible
            else:
                title = item.text(0).lower()
                url = item.text(1).lower()
                folder = item.text(2).lower()
                bookmark_data = item.data(0, Qt.UserRole)
                description = bookmark_data.get("description", "").lower()

                matches = (search_text in title or 
                           search_text in url or 
                           search_text in folder or 
                           search_text in description)
                
                item.setHidden(not matches)
                return matches
        
        root = self.bookmarks_tree.invisibleRootItem()
        for i in range(root.childCount()):
            folder_item = root.child(i)
            filter_items(folder_item)

    def refresh_bookmarks_tree(self):
        """Refresh the bookmarks tree view with all bookmarks."""
        if not hasattr(self, 'bookmarks_tree') or not self.bookmarks_tree:
            return  # Exit if tree not initialized
            
        try:
            # Clear existing items but preserve column settings
            self.bookmarks_tree.clear()
            
            # Get all bookmarks including folder information
            all_bookmarks = []
            for folder, bookmarks in self.bookmark_manager.bookmarks["folders"].items():
                for bookmark in bookmarks:
                    bookmark_copy = bookmark.copy()
                    bookmark_copy["folder"] = folder
                    all_bookmarks.append(bookmark_copy)
            
            # Create folder structure
            folders = {}
            for bookmark in all_bookmarks:
                folder_name = bookmark.get("folder", "Main")
                if folder_name not in folders:
                    folders[folder_name] = []
                folders[folder_name].append(bookmark)
            
            # Add to tree with sorting
            for folder_name, bookmarks in sorted(folders.items()):
                folder_item = QTreeWidgetItem(self.bookmarks_tree, [folder_name, "", folder_name])
                for bookmark in sorted(bookmarks, key=lambda x: x["title"].lower()):
                    item = QTreeWidgetItem(folder_item, [
                        bookmark["title"][:50] + "..." if len(bookmark["title"]) > 50 else bookmark["title"],
                        bookmark["url"][:100] + "..." if len(bookmark["url"]) > 100 else bookmark["url"],
                        bookmark.get("folder", "Main")
                    ])
                    item.setData(0, Qt.UserRole, bookmark)
                    item.setToolTip(0, bookmark["title"])
                    item.setToolTip(1, bookmark["url"])
                folder_item.setExpanded(True)
            
            # Auto-resize columns
            for i in range(self.bookmarks_tree.columnCount()):
                self.bookmarks_tree.resizeColumnToContents(i)
                
        except Exception as e:
            print(f"Error refreshing bookmarks tree: {str(e)}")
            self.notification_manager.show_notification(
                "Bookmarks Error",
                f"Failed to refresh bookmarks: {str(e)}",
                3000
            )


    def ensure_bookmarks_tree_exists(self):
        """Ensure the bookmarks tree widget is initialized."""
        if not hasattr(self, 'bookmarks_tree') or not self.bookmarks_tree:
            self.bookmarks_tree = QTreeWidget()
            self.bookmarks_tree.setHeaderLabels(["Name", "URL", "Description", "Folder"])
            self.bookmarks_tree.setColumnWidth(0, 200)
            self.bookmarks_tree.setColumnWidth(1, 350)
            self.bookmarks_tree.setColumnWidth(2, 150)
            self.bookmarks_tree.itemDoubleClicked.connect(self.open_bookmark)
            self.bookmarks_tree.setContextMenuPolicy(Qt.CustomContextMenu)
            self.bookmarks_tree.customContextMenuRequested.connect(self.show_bookmark_context_menu)            

    def show_bookmark_context_menu(self, position):
        """Show context menu for bookmarks."""
        item = self.bookmarks_tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        if item.childCount() > 0:  # Folder item
            rename_action = QAction("Rename Folder", self)
            rename_action.triggered.connect(lambda: self.rename_folder(item))
            delete_action = QAction("Delete Folder", self)
            delete_action.triggered.connect(lambda: self.delete_folder(item))
            menu.addAction(rename_action)
            menu.addAction(delete_action)
        else:  # Bookmark item
            open_action = QAction("Open", self)
            open_action.triggered.connect(lambda: self.open_bookmark(item, 0))
            edit_action = QAction("Edit", self)
            edit_action.triggered.connect(lambda: self.edit_bookmark(item))
            menu.addAction(open_action)
            menu.addAction(edit_action)
        
        menu.exec_(self.bookmarks_tree.viewport().mapToGlobal(position))

    def create_new_folder(self):
        """Create a new bookmark folder."""
        folder_name, ok = QInputDialog.getText(
            self, "New Folder", "Enter folder name:"
        )
        if ok and folder_name:
            if folder_name not in self.bookmark_manager.bookmarks["folders"]:
                self.bookmark_manager.bookmarks["folders"][folder_name] = []
                self.refresh_bookmarks_tree()

    def rename_folder(self, folder_item):
        """Rename an existing bookmark folder."""
        old_name = folder_item.text(0)
        new_name, ok = QInputDialog.getText(
            self, "Rename Folder", "New folder name:", text=old_name
        )
        if ok and new_name and new_name != old_name:
            if new_name not in self.bookmark_manager.bookmarks["folders"]:
                self.bookmark_manager.bookmarks["folders"][new_name] = self.bookmark_manager.bookmarks["folders"].pop(old_name)
                self.refresh_bookmarks_tree()
            else:
                QMessageBox.warning(self, "Error", "A folder with that name already exists")

    def delete_folder(self, folder_item):
        """Delete a bookmark folder."""
        folder_name = folder_item.text(0)
        reply = QMessageBox.question(
            self, "Delete Folder",
            f"Delete folder '{folder_name}' and all its bookmarks?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            del self.bookmark_manager.bookmarks["folders"][folder_name]
            self.refresh_bookmarks_tree()

    def edit_bookmark(self, item):
        """Edit an existing bookmark."""
        bookmark = item.data(0, Qt.UserRole)
        if not bookmark:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Bookmark")
        layout = QFormLayout()
        
        title_edit = QLineEdit(bookmark["title"])
        url_edit = QLineEdit(bookmark["url"])
        
        # Folder selection
        folder_combo = QComboBox()
        folder_combo.addItems(self.bookmark_manager.bookmarks["folders"].keys())
        if "folder" in bookmark:
            folder_combo.setCurrentText(bookmark["folder"])
        
        layout.addRow("Title:", title_edit)
        layout.addRow("URL:", url_edit)
        layout.addRow("Folder:", folder_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            # Remove from old folder
            old_folder = bookmark.get("folder", "Main")
            if old_folder in self.bookmark_manager.bookmarks["folders"]:
                self.bookmark_manager.bookmarks["folders"][old_folder] = [
                    b for b in self.bookmark_manager.bookmarks["folders"][old_folder]
                    if b["url"] != bookmark["url"]
                ]
            
            # Add to new folder
            new_folder = folder_combo.currentText()
            bookmark["title"] = title_edit.text()
            bookmark["url"] = url_edit.text()
            bookmark["folder"] = new_folder
            
            if new_folder not in self.bookmark_manager.bookmarks["folders"]:
                self.bookmark_manager.bookmarks["folders"][new_folder] = []
            
            self.bookmark_manager.bookmarks["folders"][new_folder].append(bookmark)
            self.refresh_bookmarks_tree()

    def import_bookmarks(self, browser):
        """Import bookmarks from another browser."""
        count = self.bookmark_manager.import_browser_bookmarks(browser)
        self.refresh_bookmarks_tree()
        self.notification_manager.show_notification(
            "Bookmarks Imported", 
            f"Successfully imported {count} bookmarks from {browser.capitalize()}"
        )

    def add_current_to_bookmarks(self):
        """Add current page to bookmarks with a dialog to include a description."""
        browser = self.current_browser()
        if not browser:
            return

        url = browser.url().toString()
        title = browser.page().title()

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Bookmark")
        layout = QVBoxLayout(dialog)

        # Title
        title_edit = QLineEdit(title)
        layout.addWidget(QLabel("Title:"))
        layout.addWidget(title_edit)

        # URL
        url_edit = QLineEdit(url)
        layout.addWidget(QLabel("URL:"))
        layout.addWidget(url_edit)

        # Description
        description_edit = QLineEdit()
        layout.addWidget(QLabel("Description (optional):"))
        layout.addWidget(description_edit)

        # Folder selection
        folder_combo = QComboBox()
        folder_combo.addItems(self.bookmark_manager.bookmarks["folders"].keys())
        layout.addWidget(QLabel("Folder:"))
        layout.addWidget(folder_combo)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            final_title = title_edit.text()
            final_url = url_edit.text()
            final_description = description_edit.text()
            final_folder = folder_combo.currentText()

            self.bookmark_manager.add_bookmark(final_url, final_title, final_folder, final_description)
            self.refresh_bookmarks_tree()

    def remove_selected_bookmark(self):
        """Remove selected bookmark."""
        selected = self.bookmarks_tree.currentItem()
        if selected and selected.childCount() == 0:  # Not a folder
            bookmark = selected.data(0, Qt.UserRole)
            if bookmark:
                self.bookmark_manager.remove_bookmark(bookmark["url"])
                self.refresh_bookmarks_tree()

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
        """Show the download manager dialog with active and completed downloads."""
        # Create a new instance of the download dialog each time it's shown
        self.show_downloads_dialog = QDialog(self)
        self.show_downloads_dialog.setWindowTitle("Downloads")
        self.show_downloads_dialog.setMinimumSize(700, 500)
        layout = QVBoxLayout()

        # Tabs for active and completed downloads
        tab_widget = QTabWidget()

        # Active Downloads Tab
        active_tab = QWidget()
        active_layout = QVBoxLayout()
        self.active_downloads_list = QListWidget()
        active_layout.addWidget(self.active_downloads_list)
        active_tab.setLayout(active_layout)

        # Completed Downloads Tab
        completed_tab = QWidget()
        completed_layout = QVBoxLayout()
        self.completed_downloads_list = QListWidget()
        completed_layout.addWidget(self.completed_downloads_list)
        completed_tab.setLayout(completed_layout)

        # Double-click support for opening files
        self.completed_downloads_list.itemDoubleClicked.connect(self.open_selected_download)

        tab_widget.addTab(active_tab, "Active Downloads")
        tab_widget.addTab(completed_tab, "Completed Downloads")
        layout.addWidget(tab_widget)

        # Buttons Layout
        btn_layout = QHBoxLayout()
        open_btn = QPushButton("Open File")
        open_folder_btn = QPushButton("Open Folder")
        cancel_btn = QPushButton("Cancel Download")
        clear_btn = QPushButton("Clear Completed")
        delete_file_btn = QPushButton("Delete File")  # <-- NEW BUTTON

        btn_layout.addWidget(open_btn)
        btn_layout.addWidget(open_folder_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(delete_file_btn)  # <-- ADD NEW BUTTON TO LAYOUT

        layout.addLayout(btn_layout)

        # Connect signals
        open_btn.clicked.connect(self.open_selected_download)
        open_folder_btn.clicked.connect(self.open_download_folder)
        cancel_btn.clicked.connect(self.cancel_selected_download)
        clear_btn.clicked.connect(self.download_manager.clear_completed_downloads)
        delete_file_btn.clicked.connect(self.delete_selected_download_file)  # <-- NEW CONNECTION

        # Connect DownloadManager signals to update the UI dynamically
        self.download_manager.download_started.connect(self.update_downloads_lists)
        self.download_manager.download_progress.connect(self.update_downloads_lists)
        self.download_manager.download_finished.connect(self.update_downloads_lists)
        self.download_manager.download_list_updated.connect(self.update_downloads_lists)

        # Populate lists initially
        self.update_downloads_lists()

        # Set layout and show dialog
        self.show_downloads_dialog.setLayout(layout)
        self.show_downloads_dialog.exec_()



    def delete_selected_download_file(self):
        """Delete the selected downloaded file from disk."""
        if self.completed_downloads_list.currentItem():
            path = self.completed_downloads_list.currentItem().data(Qt.UserRole)

            # Confirm deletion with user
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete '{os.path.basename(path)}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    os.remove(path)
                    self.notification_manager.show_notification(
                        "File Deleted",
                        f"'{os.path.basename(path)}' was deleted successfully.",
                        5000
                    )
                    # Remove from list and update storage
                    row = self.completed_downloads_list.currentRow()
                    self.completed_downloads_list.takeItem(row)
                    self.download_manager.remove_completed_download(row)
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Could not delete file: {str(e)}"
                    )


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


    def update_downloads_lists(self):
        """Update active and completed downloads lists dynamically."""
        
        # Only try to clear and repopulate lists if they exist
        if hasattr(self, 'active_downloads_list'):
            self.active_downloads_list.clear()
        if hasattr(self, 'completed_downloads_list'):
            self.completed_downloads_list.clear()

        # === ACTIVE DOWNLOADS ===
        if hasattr(self, 'active_downloads_list'):
            for download_id, download in self.download_manager.active_downloads.items():
                if 'item' in download:
                    received = download.get('received', 0)
                    total = download.get('total', 1)  # Prevent division by zero
                    percent = (received / total * 100) if total > 0 else 0

                    speed = download.get("speed", 0)
                    if speed > 0:
                        eta_seconds = max(0, int((total - received) / speed))
                    else:
                        eta_seconds = -1  # Indicates unknown or calculating

                    eta_str = format_time(eta_seconds) if eta_seconds >= 0 else "Calculating..."

                    item_text = (
                        f"{download['filename']} - {percent:.1f}% "
                        f"({format_size(received)} of {format_size(total)}) | Speed: {speed} | ETA: {eta_str}"
                    )
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, download_id)
                    self.active_downloads_list.addItem(item)

        # === COMPLETED DOWNLOADS ===
        if hasattr(self, 'completed_downloads_list'):
            for download in self.download_manager.completed_downloads:
                success_icon = "✓" if download.get('success', True) else "✗"
                size = format_size(download.get('received', 0))
                file_path = download.get('path', '')
                filename = os.path.basename(file_path) if file_path else download.get('filename', 'Unknown')

                item_text = f"{success_icon} {filename} - {size}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, file_path)
                self.completed_downloads_list.addItem(item)

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

        tab_widget = QTabWidget()

        # ==================== GENERAL TAB ====================
        general_tab = QWidget()
        general_layout = QFormLayout()
        general_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.home_page_edit = QLineEdit(self.settings_manager.get("home_page"))
        general_layout.addRow(QLabel("Home Page:"), self.home_page_edit)

        self.search_engine_edit = QLineEdit(self.settings_manager.get("search_engine"))
        general_layout.addRow(QLabel("Search Engine:"), self.search_engine_edit)

        # Download Directory
        download_layout = QHBoxLayout()
        self.download_dir_edit = QLineEdit(self.settings_manager.get("download_dir"))
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_download_dir)
        download_layout.addWidget(self.download_dir_edit)
        download_layout.addWidget(browse_btn)
        general_layout.addRow(QLabel("Download Directory:"), download_layout)

        # Appearance Settings
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout()
        self.dark_mode_check = QCheckBox("Enable Dark Mode")
        self.dark_mode_check.setChecked(self.settings_manager.get("dark_mode"))
        appearance_layout.addWidget(self.dark_mode_check)
        appearance_group.setLayout(appearance_layout)
        general_layout.addRow(appearance_group)

        # Media Settings
        media_group = QGroupBox("Media Playback")
        media_layout = QVBoxLayout()
        self.hls_check = QCheckBox("Enable HLS Streaming Support")
        self.hls_check.setChecked(self.settings_manager.get("hls_enabled", HLS_ENABLED))
        media_layout.addWidget(self.hls_check)

        self.drm_check = QCheckBox("Enable DRM Content (Widevine)")
        self.drm_check.setChecked(self.settings_manager.get("drm_enabled", DRM_ENABLED))
        media_layout.addWidget(self.drm_check)
        media_group.setLayout(media_layout)
        general_layout.addRow(media_group)

        general_tab.setLayout(general_layout)

        # ==================== PRIVACY TAB ====================
        privacy_tab = QWidget()
        privacy_layout = QFormLayout()

        # Content Settings
        content_group = QGroupBox("Content Settings")
        content_layout = QVBoxLayout()
        self.ad_blocker_check = QCheckBox("Enable Ad Blocker")
        self.ad_blocker_check.setChecked(self.settings_manager.get("ad_blocker"))
        content_layout.addWidget(self.ad_blocker_check)

        self.js_check = QCheckBox("Enable JavaScript")
        self.js_check.setChecked(self.settings_manager.get("javascript_enabled"))
        content_layout.addWidget(self.js_check)

        self.images_check = QCheckBox("Load Images Automatically")
        self.images_check.setChecked(self.settings_manager.get("auto_load_images"))
        content_layout.addWidget(self.images_check)
        content_group.setLayout(content_layout)
        privacy_layout.addRow(content_group)

        # User Agent Settings
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

        # ==================== SHORTCUTS TAB ====================
        shortcuts_tab = QWidget()
        shortcuts_layout = QVBoxLayout(shortcuts_tab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Shortcut Categories
        categories = {
            "Navigation": [
                ("Back", "back", "Alt+Left"),
                ("Forward", "forward", "Alt+Right"),
                ("Reload", "reload", "F5"),
                ("Hard Reload", "reload_ignore_cache", "Shift+F5"),
                ("Stop Loading", "stop", "Esc"),
                ("Go to Home", "home", "Alt+Home"),
            ],
            "Tab Management": [
                ("New Tab", "new_tab", "Ctrl+T"),
                ("Close Tab", "close_tab", "Ctrl+W"),
                ("Next Tab", "next_tab", "Ctrl+Tab"),
                ("Previous Tab", "prev_tab", "Ctrl+Shift+Tab"),
                ("Restore Closed Tab", "restore_tab", "Ctrl+Shift+T"),
            ],
            "Focus & Search": [
                ("Focus URL Bar", "focus_url", "Ctrl+L"),
                ("Focus Search Bar", "focus_search", "Ctrl+K"),
                ("Search Selected Text", "search_selected", "Ctrl+E"),
                ("Autocomplete URL", "autocomplete_url", "Ctrl+Return"),
            ],
            "Bookmarks": [
                ("Bookmark Search", "bookmark_search", "Ctrl+B"),
                ("Bookmark Current Page", "bookmark_page", "Ctrl+D"),
            ],
            "Tools": [
                ("Downloads", "downloads", "Ctrl+J"),
                ("History", "history", "Ctrl+H"),
                ("Settings", "settings", "Ctrl+,"),  # This is what we're testing!
                ("Print", "print", "Ctrl+P"),
                ("Save as PDF", "print_pdf", "Ctrl+Shift+P"),
            ],
            "Screenshots": [
                ("Capture Screenshot", "screenshot", "Ctrl+Shift+S"),
                ("Full Page Screenshot", "full_screenshot", "Ctrl+Alt+Shift+S"),
                ("Region Screenshot", "region_screenshot", "Ctrl+Shift+R"),
            ],
            "Developer Tools": [
                ("Toggle DevTools", "dev_tools", "F12"),
                ("View Page Source", "view_source", "Ctrl+U"),
            ],
            "Zoom": [
                ("Zoom In", "zoom_in", "Ctrl++"),
                ("Zoom Out", "zoom_out", "Ctrl+-"),
                ("Reset Zoom", "zoom_reset", "Ctrl+0"),
            ]
        }

        self.shortcut_editors = {}

        for category_name, items in categories.items():
            group = QGroupBox(category_name)
            group_layout = QFormLayout()
            for label, name, default in items:
                editor = QKeySequenceEdit(QKeySequence(self.settings_manager.get_shortcut(name) or default))
                self.shortcut_editors[name] = editor
                group_layout.addRow(label + ":", editor)
            group.setLayout(group_layout)
            scroll_layout.addWidget(group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        shortcuts_layout.addWidget(scroll)

        reset_btn = QPushButton("Reset All Shortcuts to Defaults")
        reset_btn.clicked.connect(self.reset_shortcuts_to_defaults)
        shortcuts_layout.addWidget(reset_btn, alignment=Qt.AlignRight)

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

        main_layout = QVBoxLayout(dialog)
        main_layout.addWidget(tab_widget)
        main_layout.addWidget(button_box)

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
    
    # Use our dark theme browser class
    window = StormBrowserDark()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()