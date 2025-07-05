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

import re
import json
import logging
import subprocess
import time
import re
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import shutil

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

from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtWidgets import QMenu, QFileDialog
from PyQt5.QtCore import QPoint
from datetime import datetime

from PyQt5.QtWidgets import QAction
from PyQt5.QtCore import QStandardPaths

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StormBrowser")

# Initialize Notify2 for desktop notifications
NOTIFICATION_AVAILABLE = False
try:
    import notify2
    notify2.init("Qt Simple Browser")
    NOTIFICATION_AVAILABLE = True
except ImportError:
    logger.warning("notify2 not available. Desktop notifications disabled.")
except Exception as e:
    logger.error(f"Error initializing notify2: {e}. Desktop notifications disabled.")

# --- Helper Functions ---
def sanitize_filename(filename):
    """Sanitizes a string to be a valid filename."""
    s = re.sub(r'[^\w\-.\s]', '_', filename)
    s = s.strip(' ._')
    if len(s) > 200: # Limit length to avoid path too long issues on some OS
        s = s[:200]
    return s

def _format_bytes(bytes_num):
    """Helper to format bytes into a human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"

# --- Tab Group Class (No changes needed) ---
class TabGroup:
    def __init__(self, name):
        self.name = name
        self.tabs = []

    def add_tab(self, tab):
        self.tabs.append(tab)

    def remove_tab(self, tab):
        if tab in self.tabs:
            self.tabs.remove(tab)






class CustomWebEnginePage(QWebEnginePage):
    new_window_requested = pyqtSignal(QWebEngineView)  # Emits the view instead of page
    force_download_requested = pyqtSignal(QUrl)
    historyChanged = pyqtSignal()

    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.browser_main_window = None
        self.browser_window = None
        self._child_views = []  # Maintain strong references to child views
        self._alive = True  # Track if this object is still alive
        self.adblocker = AdBlocker()  # Add ad-blocker instance

        # Connect signals
        self.loadFinished.connect(self._emit_history_changed)
        self.loadFinished.connect(self._check_drm_support)

        # Configure WebEngine settings
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.HyperlinkAuditingEnabled, False)
        settings.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, False)
        settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, True)
        settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        settings.setAttribute(QWebEngineSettings.AllowGeolocationOnInsecureOrigins, True)
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.WebRTCPublicInterfacesOnly, False)

    def _emit_history_changed(self, ok):
        """Emit historyChanged signal when page finishes loading"""
        self.historyChanged.emit()

    def _check_drm_support(self, ok):
        """Check for Widevine DRM support"""
        if ok:
            self.runJavaScript("""
                navigator.requestMediaKeySystemAccess('com.widevine.alpha', [{
                    initDataTypes: ['cenc'],
                    videoCapabilities: [{
                        contentType: 'video/mp4; codecs="avc1.42E01E"'
                    }]
                }]).then(() => console.log('Widevine OK')).catch(e => console.error('DRM Error:', e));
            """)

    def contextMenuEvent(self, event):
        """Handle context menu creation with custom download options"""
        menu = self.createStandardContextMenu()
        
        # Get URL information
        link_url = self.linkAt(event.pos())
        page_url = self.url()
        
        # Determine which URL to use for download actions
        url_to_download = link_url if link_url.isValid() else page_url
        
        if url_to_download.isValid():
            menu.addSeparator()
            
            # Add curl download action
            filename = url_to_download.fileName()
            action_text = f"Download '{filename}' with curl" if filename else "Download with curl"
            curl_action = QAction(action_text, menu)
            curl_action.triggered.connect(lambda: self._download_with_curl(url_to_download))
            menu.addAction(curl_action)
            
            # Add yt-dlp action if applicable
            if url_to_download.scheme() in ["http", "https"]:
                if hasattr(self, 'browser_main_window') and hasattr(self.browser_main_window, 'download_manager'):
                    yt_dlp_action = QAction("Download Video with yt-dlp", menu)
                    yt_dlp_action.triggered.connect(
                        lambda: self.browser_main_window.download_manager.initiate_yt_dlp_download(url_to_download))
                    menu.addAction(yt_dlp_action)
        
        menu.exec_(event.globalPos())

    def _download_with_curl(self, url):
        """Handle file download using curl"""
        browser = self.browser_main_window or self.browser_window
        if not browser:
            return
            
        try:
            download_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or os.path.expanduser("~/Downloads")
            filename = os.path.basename(url.path()) or f"download_{int(time.time())}"
            filepath = os.path.join(download_dir, filename)
            
            cmd = [
                'curl',
                '-L',  # Follow redirects
                '-o', filepath,
                '--progress-bar',
                url.toString()
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            browser.statusBar().showMessage(f"Downloading with curl: {filename}", 3000)
            
            def check_completion():
                if process.poll() is not None:
                    if process.returncode == 0:
                        browser.statusBar().showMessage(f"Download complete: {filename}", 5000)
                        if NOTIFICATION_AVAILABLE:
                            notify2.Notification("Download Complete", f"File saved to: {filepath}").show()
                    else:
                        error = process.stderr.read()
                        QMessageBox.critical(browser, "Download Failed", f"cURL error: {error or 'Unknown error'}")
            
            QTimer.singleShot(1000, check_completion)
            
        except Exception as e:
            QMessageBox.critical(browser, "Error", f"Failed to start curl download: {str(e)}")

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        """Override to block ads before navigation."""
        try:
            if self.adblocker.should_block(url):
                logger.info(f"Blocked ad/tracker: {url.toString()}")
                return False
        except Exception as e:
            logger.error(f"Ad-block check error: {e}")
        
        # Your existing force download logic
        url_str = url.toString().lower()
        force_download_extensions = (
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
            '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
            '.mp3', '.wav', '.flac', '.aac', '.ogg',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.odt', '.ods', '.odp',
            '.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm', '.appimage',
            '.iso', '.img', '.dmg', '.apk'
        )
        
        path = url.path().lower()
        if any(path.endswith(ext) for ext in force_download_extensions):
            self.force_download_requested.emit(url)
            return False

        return super().acceptNavigationRequest(url, _type, isMainFrame)

    def createWindow(self, window_type):
        """Handle new window/tab creation with proper cleanup"""
        if not self._alive:
            return None

        try:
            if window_type == QWebEnginePage.WebBrowserTab:
                new_webview = QWebEngineView()
                new_page = CustomWebEnginePage(self.profile(), new_webview)
                new_webview.setPage(new_page)
                
                # Set browser references
                new_page.browser_main_window = self.browser_main_window
                new_page.browser_window = self.browser_window
                
                # Add to tracked child views
                self._child_views.append(new_webview)
                
                # Safe cleanup connection
                def cleanup():
                    try:
                        if new_webview in self._child_views:
                            self._child_views.remove(new_webview)
                        if hasattr(new_page, '_alive'):
                            new_page._alive = False
                            if not sip.isdeleted(new_page):
                                new_page.deleteLater()
                    except:
                        pass
                
                new_webview.destroyed.connect(cleanup)
                
                self.new_window_requested.emit(new_webview)
                return new_page
            
            return super().createWindow(window_type)
            
        except Exception as e:
            logger.error(f"Error in createWindow: {str(e)}")
            if self.browser_main_window:
                QMessageBox.critical(self.browser_main_window, "Error", "Failed to create new window")
            return None
    def __del__(self):
        """Destructor to ensure proper cleanup"""
        self._alive = False
        for view in self._child_views[:]:  # Iterate over a copy
            try:
                if view and hasattr(view, 'deleteLater'):
                    view.deleteLater()
            except RuntimeError:
                pass
        self._child_views.clear()

    def _handle_full_screen_request(self, request):
        """Toggle fullscreen mode"""
        browser = self.browser_main_window or self.browser_window
        if browser:
            if request.toggleOn():
                browser.showFullScreen()
            else:
                browser.showNormal()
        request.accept()

class AdBlocker:
    """Handles ad-blocking functionality using EasyList filters."""
    def __init__(self):
        self.enabled = True
        self.filter_lists = []
        self.blocked_urls = set()
        self.load_filters()

    def load_filters(self):
        """Load ad-blocking filters from file or online."""
        try:
            # Try to load from local file first
            filter_path = os.path.join(QStandardPaths.writableLocation(
                QStandardPaths.AppDataLocation), "adblock_filters.txt")
            
            if os.path.exists(filter_path):
                with open(filter_path, 'r') as f:
                    self.filter_lists = [line.strip() for line in f if line.strip()]
            else:
                # Default basic filters if no file exists
                self.filter_lists = [
                    '||ads.example.com^',
                    '||doubleclick.net^',
                    '||googleadservices.com^',
                    '/advertisement.',
                    '||adservice.google.com^',
                    '||advertising.com^',
                    '||analytics.com^',
                    '||tracking.com^',
                    '||popupads.com^'
                ]
        except Exception as e:
            logger.error(f"Error loading ad filters: {e}")
            self.filter_lists = []

    def should_block(self, url):
        """Check if a URL should be blocked."""
        if not self.enabled:
            return False
            
        url_str = url.toString()
        for pattern in self.filter_lists:
            try:
                if pattern.startswith('||') and pattern.endswith('^'):
                    domain = pattern[2:-1]
                    if domain in url_str:
                        return True
                elif pattern.startswith('/') and pattern.endswith('/'):
                    if re.search(pattern[1:-1], url_str):
                        return True
                elif pattern in url_str:
                    return True
            except Exception as e:
                logger.error(f"Error checking filter {pattern}: {e}")
        return False




class CombinedLauncher(QDialog):
    def __init__(self, parent=None, bookmarks=None):
        super().__init__(parent)
        self.setWindowTitle("Open URL or Bookmark")
        self.resize(800, 400)
        self.bookmarks = bookmarks or []
        self.selected_url = None
        self.parent_browser = parent

        layout = QVBoxLayout(self)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Enter URL or search bookmarks")
        self.entry.textChanged.connect(self.update_results)
        self.entry.returnPressed.connect(self.on_open_clicked)
        layout.addWidget(self.entry)

        self.result_list = QListWidget()
        self.result_list.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self.result_list)

        button_box = QDialogButtonBox(QDialogButtonBox.Open | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_open_clicked)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.update_results()
        QTimer.singleShot(0, self.entry.setFocus)

    def update_results(self):
        query = self.entry.text().strip().lower()
        self.result_list.clear()
        
        # Show all bookmarks if query is empty
        if not query:
            for bookmark in self.bookmarks:
                item_text = f"{bookmark['name']} - {bookmark['uri']}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, bookmark['uri'])
                self.result_list.addItem(item)
            return
        
        # Filter bookmarks based on query
        matches = []
        for bookmark in self.bookmarks:
            if (query in bookmark['name'].lower() or 
                query in bookmark['uri'].lower()):
                matches.append(bookmark)
        
        # Add matching bookmarks
        for bookmark in matches:
            item_text = f"{bookmark['name']} - {bookmark['uri']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, bookmark['uri'])
            self.result_list.addItem(item)
        
        # If no bookmarks match, add the query itself as a potential URL
        if not matches:
            item = QListWidgetItem(f"Open: {query}")
            item.setData(Qt.UserRole, query)
            self.result_list.addItem(item)

    def on_open_clicked(self):
        item = self.result_list.currentItem()
        if item:
            self.selected_url = item.data(Qt.UserRole)
            self.accept()
        else:
            # If no item selected, try to open the text in the entry field as a URL
            text = self.entry.text().strip()
            if text:
                self.selected_url = text
                self.accept()
            else:
                QMessageBox.warning(self, "No Selection", "Please enter a URL or select a bookmark.")

    def _on_item_activated(self, item):
        self.selected_url = item.data(Qt.UserRole)
        self.accept()

# --- BookmarkManagerDialog (No changes needed) ---
class BookmarkManagerDialog(QDialog):
    def __init__(self, parent=None, bookmarks=None):
        super().__init__(parent)
        self.setWindowTitle("Bookmark Manager")
        self.resize(600, 500)
        self.bookmarks = bookmarks
        self.parent_browser = parent

        layout = QVBoxLayout(self)

        self.bookmark_list = QListWidget()
        self.bookmark_list.itemDoubleClicked.connect(self.open_selected_bookmark)
        layout.addWidget(self.bookmark_list)

        button_layout = QHBoxLayout()
        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(self.open_selected_bookmark)
        button_layout.addWidget(self.open_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_selected_bookmark)
        button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_selected_bookmark)
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.load_bookmarks_into_list()

    def load_bookmarks_into_list(self):
        self.bookmark_list.clear()
        for bookmark in self.bookmarks:
            item = QListWidgetItem(f"{bookmark['name']} - {bookmark['uri']}")
            item.setData(Qt.UserRole, bookmark) # Store the whole bookmark dict
            self.bookmark_list.addItem(item)

    def open_selected_bookmark(self):
        selected_item = self.bookmark_list.currentItem()
        if selected_item:
            bookmark = selected_item.data(Qt.UserRole)
            if self.parent_browser:
                # Open in a new tab
                self.parent_browser._add_new_tab(QUrl(bookmark['uri']))
            self.accept() # Close the dialog

    def edit_selected_bookmark(self):
        selected_item = self.bookmark_list.currentItem()
        if selected_item:
            current_bookmark = selected_item.data(Qt.UserRole)

            name, ok_name = QInputDialog.getText(self, "Edit Bookmark Name", "New Name:",
                                                 QLineEdit.Normal, current_bookmark['name'])
            if not ok_name:
                return

            uri, ok_uri = QInputDialog.getText(self, "Edit Bookmark URL", "New URL:",
                                               QLineEdit.Normal, current_bookmark['uri'])
            if not ok_uri:
                return

            current_bookmark['name'] = name
            current_bookmark['uri'] = uri
            selected_item.setText(f"{name} - {uri}")

            if self.parent_browser:
                self.parent_browser.save_bookmarks()
            QMessageBox.information(self, "Bookmark Edited", "Bookmark updated successfully.")

    def delete_selected_bookmark(self):
        selected_item = self.bookmark_list.currentItem()
        if selected_item:
            reply = QMessageBox.question(self, "Delete Bookmark",
                                         "Are you sure you want to delete this bookmark?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                bookmark_to_delete = selected_item.data(Qt.UserRole)
                self.bookmarks.remove(bookmark_to_delete)
                self.load_bookmarks_into_list() # Reload the list
                if self.parent_browser:
                    self.parent_browser.save_bookmarks()
                QMessageBox.information(self, "Bookmark Deleted", "Bookmark deleted successfully.")

# --- DownloadManager (Significant Improvements) ---


class DownloadManager(QObject):
    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.downloads = []  # List to hold download info dicts (serializable and live item references)
        
        # Use QStandardPaths for a more OS-agnostic download folder
        self.download_folder = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        if not self.download_folder:  # Fallback if QStandardPaths fails
            self.download_folder = os.path.expanduser("~/Downloads")

        # Create downloads folder if it doesn't exist
        os.makedirs(self.download_folder, exist_ok=True)
        
        self.download_history_file = os.path.join(self.download_folder, 'download_history.json')
        self.download_manager_window = None  # Reference to the QDialog window
        self.downloads_layout = None  # The QVBoxLayout within the scroll area of the dialog
        self.max_history_size = 100  # Maximum number of downloads to keep in history

        # This will hold references to temporary QWebEngineViews for forced downloads
        self.active_forced_downloads_webviews = []

        # Connect signals
        QWebEngineProfile.defaultProfile().downloadRequested.connect(self.handle_download_item)
        QWebEngineProfile.defaultProfile().setDownloadPath(self.download_folder)

        self.load_download_history()  # Load history at startup
        logger.info(f"DownloadManager initialized. Default download path: {self.download_folder}")



    def handle_forced_download_url(self, url: QUrl):
        """Entry point for forced downloads with curl → axel → yt-dlp fallback."""
        logger.info(f"DownloadManager: Forcing download for URL: {url.toString()}")
        self._download_with_curl(url)

    def _download_with_curl(self, url: QUrl):
        """Primary download method using curl."""
        # Setup download directory and filename
        download_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or os.path.expanduser("~/Downloads")
        filename = sanitize_filename(url.fileName() or f"download_{int(time.time())}")
        filepath = os.path.join(download_dir, filename)

        # Check for existing file
        if os.path.exists(filepath):
            reply = QMessageBox.question(
                self.browser,
                "File Exists",
                f"{filename} already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                self.browser.statusBar().showMessage("Download cancelled", 2000)
                return

        # Create download info dictionary
        info = {
            "uri": url.toString(),
            "filename": filename,
            "filepath": filepath,
            "progress": 0,
            "status": "Starting (curl)...",
            "start_time": datetime.now().isoformat(),
            "method": "curl",
            "attempts": 1
        }
        
        # Add to downloads list and UI
        self.downloads.append(info)
        self._trim_download_history()
        self.save_download_history()
        self._ensure_download_manager_visible()
        self._create_download_widgets(info)

        # Build curl command
        cmd = [
            'curl',
            '-L',  # Follow redirects
            '-o', filepath,
            '--progress-bar',
            '--connect-timeout', '30',
            '--max-time', '600',  # 10 minute timeout
            url.toString()
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            info["process"] = process
            self.browser.statusBar().showMessage(f"Downloading with curl: {filename}", 3000)

            def check_completion():
                return_code = process.poll()
                if return_code is not None:
                    info["end_time"] = datetime.now().isoformat()
                    if return_code == 0:
                        self._handle_download_success(info)
                    else:
                        error = process.stderr.read()
                        self._handle_curl_failure(info, error, url)
                else:
                    self._update_curl_progress(info, process)
                    QTimer.singleShot(1000, check_completion)

            QTimer.singleShot(1000, check_completion)

        except Exception as e:
            self._handle_download_error(info, e, url)

    def _ensure_download_manager_visible(self):
        """Ensure download manager window is visible."""
        if not hasattr(self, 'download_manager_window') or not self.download_manager_window:
            self.create_download_manager_window()
        self.download_manager_window.show()

    def _create_download_widgets(self, info):
        """Create UI widgets for a new download."""
        if not hasattr(self, 'downloads_layout'):
            return

        # Label showing filename and status
        info["label_widget"] = QLabel(f"{info['filename']} - {info['status']}")
        info["label_widget"].setWordWrap(True)
        
        # Progress bar
        info["progressbar_widget"] = QProgressBar()
        info["progressbar_widget"].setRange(0, 100)
        info["progressbar_widget"].setValue(info['progress'])
        info["progressbar_widget"].setFormat(info["status"])
        
        # Buttons
        info["cancel_button"] = QPushButton("Cancel")
        info["cancel_button"].clicked.connect(lambda: self._cancel_download(info))
        
        # Layout for this download
        entry_layout = QVBoxLayout()
        entry_layout.addWidget(info["label_widget"])
        entry_layout.addWidget(info["progressbar_widget"])
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(info["cancel_button"])
        button_layout.addStretch(1)
        entry_layout.addLayout(button_layout)
        
        # Add separator
        separator = QLabel("<hr>")
        separator.setMinimumHeight(1)
        entry_layout.addWidget(separator)
        
        # Add to downloads layout (before the stretch)
        self.downloads_layout.insertLayout(self.downloads_layout.count() - 1, entry_layout)

    def _update_curl_progress(self, info, process):
        """Update progress from curl's output."""
        try:
            stderr = process.stderr.read()
            if '%' in stderr:
                progress = int(stderr.split('%')[0].split()[-1])
                info["progress"] = progress
                info["status"] = f"{progress}% (curl)"
                self._update_download_widgets(info)
        except:
            pass

    def _handle_curl_failure(self, info, error, url):
        """Handle curl failure and fallback to axel or yt-dlp."""
        error_msg = error[:200] + "..." if len(error) > 200 else error
        info["status"] = f"Curl failed: {error_msg}"
        info["progress"] = 0
        self._update_download_widgets(info)
        
        if shutil.which('axel'):
            self.browser.statusBar().showMessage("Curl failed, trying axel...", 3000)
            self._download_with_axel(url, info)
        elif shutil.which('yt-dlp'):
            self.browser.statusBar().showMessage("Curl failed, trying yt-dlp...", 3000)
            self._download_with_ytdlp(url, info)
        else:
            QMessageBox.critical(
                self.browser,
                "Download Failed",
                f"cURL error: {error_msg}\n\nNo fallback downloaders available."
            )
            self._finalize_download(info, success=False)

    def _download_with_axel(self, url: QUrl, info: dict):
        """Secondary download method using axel."""
        info.update({
            "status": "Starting (axel)...",
            "method": "axel",
            "attempts": info.get("attempts", 0) + 1,
            "start_time": datetime.now().isoformat()
        })
        self._update_download_widgets(info)

        cmd = [
            'axel',
            '-n', '4',  # Use 4 connections
            '-o', info["filepath"],
            url.toString()
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            info["process"] = process
            self.browser.statusBar().showMessage(f"Downloading with axel: {info['filename']}", 3000)

            def check_completion():
                return_code = process.poll()
                if return_code is not None:
                    info["end_time"] = datetime.now().isoformat()
                    if return_code == 0:
                        self._handle_download_success(info)
                    else:
                        error = process.stderr.read()
                        self._handle_axel_failure(info, error, url)
                else:
                    self._update_axel_progress(info, process)
                    QTimer.singleShot(1000, check_completion)

            QTimer.singleShot(1000, check_completion)

        except Exception as e:
            self._handle_download_error(info, e, url)

    def _update_axel_progress(self, info, process):
        """Update progress from axel's output."""
        try:
            # Axel progress is in stderr, format: [ 12%] 1024/8192
            stderr = process.stderr.read()
            if '%' in stderr:
                progress = int(stderr.split('%')[0].strip().split()[-1])
                info["progress"] = progress
                info["status"] = f"{progress}% (axel)"
                self._update_download_widgets(info)
        except:
            pass

    def _handle_axel_failure(self, info, error, url):
        """Handle axel failure and fallback to yt-dlp."""
        error_msg = error[:200] + "..." if len(error) > 200 else error
        info["status"] = f"Axel failed: {error_msg}"
        info["progress"] = 0
        self._update_download_widgets(info)
        
        if shutil.which('yt-dlp'):
            self.browser.statusBar().showMessage("Axel failed, trying yt-dlp...", 3000)
            self._download_with_ytdlp(url, info)
        else:
            QMessageBox.critical(
                self.browser,
                "Download Failed",
                f"Axel error: {error_msg}\n\nNo more fallback options available."
            )
            self._finalize_download(info, success=False)

    def _download_with_ytdlp(self, url: QUrl, info: dict):
        """Final fallback method using yt-dlp."""
        info.update({
            "status": "Starting (yt-dlp)...",
            "method": "yt-dlp",
            "attempts": info.get("attempts", 0) + 1,
            "start_time": datetime.now().isoformat()
        })
        self._update_download_widgets(info)

        cmd = [
            'yt-dlp',
            '-o', os.path.join(os.path.dirname(info["filepath"]), '%(title)s.%(ext)s'),
            '--no-playlist',
            url.toString()
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            info["process"] = process
            self.browser.statusBar().showMessage(f"Downloading with yt-dlp...", 3000)

            def check_completion():
                return_code = process.poll()
                if return_code is not None:
                    info["end_time"] = datetime.now().isoformat()
                    if return_code == 0:
                        self._handle_download_success(info)
                    else:
                        error = process.stderr.read()
                        self._handle_ytdlp_failure(info, error)
                else:
                    QTimer.singleShot(1000, check_completion)

            QTimer.singleShot(1000, check_completion)

        except Exception as e:
            self._handle_download_error(info, e, url)

    def _handle_download_success(self, info):
        """Handle successful download completion."""
        info.update({
            "status": f"Completed ({info['method']})",
            "progress": 100,
            "duration": (datetime.fromisoformat(info["end_time"]) - 
                       datetime.fromisoformat(info["start_time"])).total_seconds()
        })
        self._finalize_download(info, success=True)
        self.browser.statusBar().showMessage(f"Download complete using {info['method']}", 5000)
        if NOTIFICATION_AVAILABLE:
            notify2.Notification(
                "Download Complete",
                f"File saved using {info['method']}: {info['filename']}"
            ).show()

    def _update_download_widgets(self, info):
        """Update all UI widgets for a download."""
        if info.get("label_widget"):
            info["label_widget"].setText(f"{info['filename']} - {info['status']}")
        if info.get("progressbar_widget"):
            info["progressbar_widget"].setValue(info['progress'])
            info["progressbar_widget"].setFormat(info["status"])

    def _finalize_download(self, info, success=True):
        """Finalize download state in UI and storage."""
        self._update_download_widgets(info)
        if info.get("cancel_button"):
            info["cancel_button"].setEnabled(False)
            info["cancel_button"].setText("Done" if success else "Failed")
        self.save_download_history()

    def _cancel_download(self, info):
        """Cancel an active download."""
        if info.get("process"):
            try:
                info["process"].terminate()
                info["status"] = "Cancelled"
                info["progress"] = 0
                info["end_time"] = datetime.now().isoformat()
                self._finalize_download(info, success=False)
                self.browser.statusBar().showMessage("Download cancelled", 3000)
            except Exception as e:
                logger.error(f"Error cancelling download: {e}")

    def _handle_ytdlp_failure(self, info, error):
        """Handle yt-dlp download failure (final fallback)."""
        error_msg = error[:200] + "..." if len(error) > 200 else error
        info["status"] = f"yt-dlp failed: {error_msg}"
        info["progress"] = 0
        self._update_download_widgets(info)
        
        QMessageBox.critical(
            self.browser,
            "Download Failed",
            f"All download methods failed.\n\nFinal error from yt-dlp: {error_msg}"
        )
        self._finalize_download(info, success=False)

    def _handle_download_error(self, info, error, url):
        """Handle general download errors."""
        error_msg = str(error)[:200] + "..." if len(str(error)) > 200 else str(error)
        info["status"] = f"{info['method']} error: {error_msg}"
        info["progress"] = 0
        self._update_download_widgets(info)
        
        # Determine next fallback
        if info["method"] == "curl" and shutil.which('axel'):
            self.browser.statusBar().showMessage("Curl error, trying axel...", 3000)
            self._download_with_axel(url, info)
        elif info["method"] in ["curl", "axel"] and shutil.which('yt-dlp'):
            self.browser.statusBar().showMessage(f"{info['method']} error, trying yt-dlp...", 3000)
            self._download_with_ytdlp(url, info)
        else:
            QMessageBox.critical(
                self.browser,
                "Download Failed",
                f"{info['method']} error: {error_msg}\n\nNo more fallback options available."
            )
            self._finalize_download(info, success=False)

    # The rest of your existing methods (_download_with_curl, _download_with_axel, 
    # _download_with_ytdlp, etc.) remain exactly the same as in the previous implementation



    def _cleanup_temp_webview_if_no_download(self, webview: QWebEngineView, url: QUrl):
        """Cleans up a temporary webview if it's still in the active list after a delay."""
        if webview in self.active_forced_downloads_webviews:
            self.active_forced_downloads_webviews.remove(webview)
            webview.deleteLater()
            logger.warning(f"DownloadManager: Cleaned up temporary webview for {url.toString()}. No download item was processed.")
            self.browser.statusBar_.showMessage(
                f"Could not initiate download for {url.fileName()}. It might be a streaming link or unsupported.", 
                4000
            )

    def handle_download_item(self, download_item: QWebEngineDownloadItem):
        """Primary entry point for all downloads detected by QWebEngineProfile."""
        logger.info(f"DownloadManager: Received QWebEngineDownloadItem for: {download_item.url().toString()}")

        # Check if this download item is already being managed
        if any(d.get("download_item") == download_item for d in self.downloads):
            logger.debug(f"Download item {download_item.url().toString()} already managed. Skipping.")
            return

        self.process_download_item(download_item)

    def process_download_item(self, download_item: QWebEngineDownloadItem):
        """Processes a QWebEngineDownloadItem, prompts user for save location, and sets up UI."""
        suggested_filename = sanitize_filename(download_item.suggestedFileName())
        suggested_path = os.path.join(self.download_folder, suggested_filename)

        # Prompt user for save location
        filepath, _ = QFileDialog.getSaveFileName(
            self.browser, 
            "Save File", 
            suggested_path, 
            "All Files (*);;"
        )
        
        if not filepath:
            download_item.cancel()
            logger.info(f"Download cancelled by user: {download_item.url().toString()}")
            self.browser.statusBar_.showMessage("Download cancelled.", 2000)
            self.remove_temp_webview_for_download_item(download_item)
            return

        download_item.setPath(filepath)
        download_item.accept()  # Start the download

        # Create download info dictionary
        info = {
            "uri": download_item.url().toString(),
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "progress": 0,
            "status": "Starting...",
            "download_item": download_item,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration": None,
            "received_bytes": 0,
            "total_bytes": 0,
            "label_widget": None,
            "progressbar_widget": None,
            "open_button": None,
            "folder_button": None,
            "cancel_button": None
        }
        
        self.downloads.append(info)
        self._trim_download_history()  # Ensure we don't keep too many items
        self.save_download_history()

        # Connect signals
        download_item.downloadProgress.connect(lambda received, total: self.on_progress(info, received, total))
        download_item.stateChanged.connect(lambda state: self.on_state_changed(info, state))

        self.browser.statusBar().showMessage(f"Download started: {info['filename']}", 3000)
        self.create_download_manager_window()
        self.add_download_widgets_to_ui(info)
        logger.info(f"Download initiated for {info['filename']} to {filepath}")

    def _trim_download_history(self):
        """Ensure we don't keep too many items in the download history."""
        if len(self.downloads) > self.max_history_size:
            # Remove oldest items (keep the most recent max_history_size items)
            self.downloads = self.downloads[-self.max_history_size:]

    def on_progress(self, info: dict, received_bytes: int, total_bytes: int):
        """Updates download progress in the stored info and UI."""
        info["received_bytes"] = received_bytes
        info["total_bytes"] = total_bytes

        if total_bytes > 0:
            percent = int((received_bytes / total_bytes) * 100)
            info["progress"] = percent
            info["status"] = f"{_format_bytes(received_bytes)} / {_format_bytes(total_bytes)} ({percent}%)"
        else:
            info["status"] = f"{_format_bytes(received_bytes)} downloaded"
            info["progress"] = 0

        if info["label_widget"] and info["progressbar_widget"]:
            info["label_widget"].setText(f"{info['filename']} - {info['status']}")
            info["progressbar_widget"].setValue(info['progress'])
            info["progressbar_widget"].setFormat(f"{info['progress']}%")

        # Throttle history saves during progress updates
        if info["progress"] % 5 == 0:  # Save every 5% progress
            self.save_download_history()

    def on_state_changed(self, info: dict, state: QWebEngineDownloadItem.DownloadState):
        """Updates download state (finished, cancelled, interrupted)."""
        logger.info(f"Download state changed for {info['filename']}: {state}")

        download_item = info["download_item"]
        info["end_time"] = datetime.now().isoformat()
        
        if state == QWebEngineDownloadItem.DownloadInterrupted:
            info["status"] = f"Interrupted: {download_item.interruptReasonString()}"
            logger.warning(f"Download interrupted for {info['filename']}: {download_item.interruptReasonString()}")
            self.browser.statusBar().showMessage(f"Download interrupted: {info['filename']}", 5000)

        elif state == QWebEngineDownloadItem.DownloadCancelled:
            info["status"] = "Cancelled"
            logger.info(f"Download cancelled for {info['filename']}")
            self.browser.statusBar().showMessage(f"Download cancelled: {info['filename']}", 3000)

        elif state == QWebEngineDownloadItem.DownloadCompleted:
            info["status"] = "Completed"
            info["progress"] = 100
            
            try:
                start_time_dt = datetime.fromisoformat(info["start_time"])
                info["duration"] = (datetime.now() - start_time_dt).total_seconds()
            except ValueError:
                info["duration"] = None

            self._show_download_complete_notification(info)
            logger.info(f"Download completed for {info['filename']}")
            self.browser.statusBar().showMessage(f"Download completed: {info['filename']}", 5000)

        # Clear reference to the live item
        info["download_item"] = None

        # Update UI
        if info["label_widget"] and info["progressbar_widget"]:
            info["label_widget"].setText(f"{info['filename']} - {info['status']}")
            info["progressbar_widget"].setValue(info['progress'])
            info["progressbar_widget"].setFormat(info["status"])

        if info["cancel_button"]:
            info["cancel_button"].setEnabled(False)
            info["cancel_button"].setText("Done" if state == QWebEngineDownloadItem.DownloadCompleted else "N/A")

        if info["open_button"]:
            info["open_button"].setVisible(state == QWebEngineDownloadItem.DownloadCompleted and os.path.exists(info["filepath"]))
        if info["folder_button"]:
            info["folder_button"].setVisible(state == QWebEngineDownloadItem.DownloadCompleted and os.path.exists(info["filepath"]))

        self.save_download_history()
        self.remove_temp_webview_for_download_item(download_item)

    def _show_download_complete_notification(self, info):
        """Shows a notification when download is complete."""
        if NOTIFICATION_AVAILABLE:
            duration_text = ""
            if info["duration"] is not None:
                minutes, seconds = divmod(info["duration"], 60)
                duration_text = f"\nTime taken: {int(minutes)}m {int(seconds)}s"
            try:
                notify2.Notification(
                    "Download Complete", 
                    f"'{info['filename']}' saved to: {info['filepath']}{duration_text}"
                ).show()
            except Exception as e:
                logger.error(f"Error showing notification: {e}")

    def remove_temp_webview_for_download_item(self, download_item: QWebEngineDownloadItem):
        """Removes the temporary QWebEngineView associated with a download."""
        for webview in list(self.active_forced_downloads_webviews):
            # Check if this webview matches the download item's URL
            if webview.url() == download_item.url():
                # Remove profile comparison since download_item doesn't have profile()
                self.active_forced_downloads_webviews.remove(webview)
                webview.deleteLater()
                logger.info(f"DownloadManager: Cleaned up temporary webview for {download_item.url().toString()}")
                break

    def create_download_manager_window(self):
        """Creates and shows the download manager window."""
        if self.download_manager_window is None:
            self.download_manager_window = QDialog(self.browser)
            self.download_manager_window.setWindowTitle("Download Manager")
            self.download_manager_window.resize(800, 400)

            # Apply dark theme
            self.download_manager_window.setStyleSheet("""
                QDialog {
                    background-color: #2b2b2b;
                    color: white;
                }
                QLabel {
                    color: white;
                }
                QProgressBar {
                    background-color: #1e1e1e;
                    border: 1px solid #3a3a3a;
                    color: white;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #00aa00;
                }
                QScrollArea {
                    border: none;
                }
                QWidget#scrollAreaWidgetContents {
                    background-color: #2b2b2b;
                }
                QPushButton {
                    background-color: #3a3a3a;
                    color: white;
                    border-radius: 4px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #555;
                }
                QLabel[text="<hr>"] {
                    background-color: #4a4a4a;
                    min-height: 1px;
                    max-height: 1px;
                    margin: 5px 0px;
                }
            """)

            layout = QVBoxLayout(self.download_manager_window)

            # Top buttons layout
            hbox_buttons = QHBoxLayout()
            clear_history_button = QPushButton("Clear History")
            clear_history_button.clicked.connect(self.on_clear_download_history)
            hbox_buttons.addWidget(clear_history_button)

            open_folder_button = QPushButton("Open Folder")
            open_folder_button.clicked.connect(self.open_downloads_folder)
            hbox_buttons.addWidget(open_folder_button)
            hbox_buttons.addStretch(1)
            layout.addLayout(hbox_buttons)

            # Scroll area for downloads
            scroll_area = QScrollArea()
            scroll_content = QWidget()
            scroll_content.setObjectName("scrollAreaWidgetContents")
            self.downloads_layout = QVBoxLayout(scroll_content)
            self.downloads_layout.addStretch(1)
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(scroll_content)
            layout.addWidget(scroll_area)

            self.download_manager_window.setLayout(layout)
            self.update_download_ui_list_initial()

        if not self.download_manager_window.isVisible():
            self.download_manager_window.show()
        self.download_manager_window.raise_()
        self.download_manager_window.activateWindow()

    def update_download_ui_list_initial(self):
        """Clears and repopulates the download UI with current download states."""
        if not self.downloads_layout:
            return

        self._clear_layout(self.downloads_layout)
        self.downloads_layout.addStretch(1)

        # Add downloads in reverse chronological order (newest first)
        for d in reversed(self.downloads):
            self.add_download_widgets_to_ui(d)

    def add_download_widgets_to_ui(self, download_info: dict):
        """Adds a single download entry's widgets to the UI."""
        if not self.downloads_layout:
            return

        # Create widgets if they don't exist
        if download_info.get("label_widget") is None:
            download_info["label_widget"] = QLabel(f"{download_info['filename']} - {download_info['status']}")
            download_info["label_widget"].setWordWrap(True)

            download_info["progressbar_widget"] = QProgressBar()
            download_info["progressbar_widget"].setRange(0, 100)
            download_info["progressbar_widget"].setValue(download_info['progress'])
            download_info["progressbar_widget"].setFormat(f"{download_info['progress']}%")

            download_info["open_button"] = QPushButton("Open")
            download_info["open_button"].clicked.connect(lambda: self.open_downloaded_file(download_info['filepath']))
            download_info["open_button"].setVisible(
                download_info['status'] == "Completed" and os.path.exists(download_info['filepath'])
            )

            download_info["folder_button"] = QPushButton("Folder")
            download_info["folder_button"].clicked.connect(lambda: self.open_download_folder(download_info['filepath']))
            download_info["folder_button"].setVisible(
                download_info['status'] == "Completed" and os.path.exists(download_info['filepath'])
            )

            download_info["cancel_button"] = QPushButton("Cancel")
            if download_info.get("download_item"):
                download_info["cancel_button"].clicked.connect(download_info["download_item"].cancel)
            download_info["cancel_button"].setEnabled(download_info['status'] in ["Starting...", "Downloading..."])
            download_info["cancel_button"].setText(
                "Done" if download_info['status'] == "Completed" else 
                "N/A" if download_info['status'] in ["Cancelled", "Interrupted"] else 
                "Cancel"
            )

        # Create layout for this download entry
        entry_layout = QVBoxLayout()
        entry_layout.addWidget(download_info["label_widget"])
        entry_layout.addWidget(download_info["progressbar_widget"])

        button_hbox = QHBoxLayout()
        button_hbox.addWidget(download_info["cancel_button"])
        button_hbox.addWidget(download_info["open_button"])
        button_hbox.addWidget(download_info["folder_button"])
        button_hbox.addStretch(1)
        entry_layout.addLayout(button_hbox)

        entry_layout.addWidget(QLabel("<hr>"))  # Separator

        # Insert at the top (before the stretch item)
        self.downloads_layout.insertLayout(self.downloads_layout.count() - 1, entry_layout)

    def _clear_layout(self, layout):
        """Clears a layout and deletes its widgets."""
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())

    def on_clear_download_history(self):
        """Clears the download history and updates the UI."""
        reply = QMessageBox.question(
            self.download_manager_window, 
            "Clear History",
            "Are you sure you want to clear all download history? This will not delete files from your disk.",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Cancel any active downloads
            for d in self.downloads:
                if d.get("download_item") and d["download_item"].state() == QWebEngineDownloadItem.DownloadInProgress:
                    d["download_item"].cancel()
            
            self.downloads = []
            self.save_download_history()
            self.update_download_ui_list_initial()
            
            logger.info("Download history cleared.")
            QMessageBox.information(
                self.download_manager_window, 
                "History Cleared", 
                "Download history cleared successfully."
            )
            self.browser.statusBar().showMessage("Download history cleared.", 2000)

    def open_downloads_folder(self, file_path=None):
        """Opens the downloads folder or the folder containing a specific file."""
        path_to_open = os.path.dirname(file_path) if file_path and os.path.exists(file_path) else self.download_folder

        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path_to_open))
            logger.info(f"Opened folder: {path_to_open}")
            self.browser.statusBar().showMessage(f"Opened folder: {path_to_open}", 2000)
        except Exception as e:
            logger.error(f"Failed to open folder {path_to_open}: {e}")
            QMessageBox.critical(self.browser, "Error", f"Could not open folder: {e}")

    def open_downloaded_file(self, file_path: str):
        """Opens the downloaded file using the default system application."""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            QMessageBox.warning(
                self.browser, 
                "File Not Found", 
                f"The file '{os.path.basename(file_path)}' could not be found."
            )
            self.browser.statusBar().showMessage(f"File not found: {os.path.basename(file_path)}", 3000)
            return

        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            logger.info(f"Opened downloaded file: {file_path}")
            self.browser.statusBar().showMessage(f"Opened file: {os.path.basename(file_path)}", 2000)
        except Exception as e:
            logger.error(f"Failed to open file {file_path}: {e}")
            QMessageBox.critical(self.browser, "Error Opening File", f"Could not open file: {e}")

    def save_download_history(self):
        """Save download history to a JSON file."""
        serializable_downloads = []
        for d in self.downloads:
            serializable_downloads.append({
                "uri": d.get("uri"),
                "filename": d.get("filename"),
                "filepath": d.get("filepath"),
                "progress": d.get("progress"),
                "status": d.get("status"),
                "start_time": d.get("start_time"),
                "end_time": d.get("end_time"),
                "duration": d.get("duration"),
                "received_bytes": d.get("received_bytes", 0),
                "total_bytes": d.get("total_bytes", 0)
            })
        
        try:
            with open(self.download_history_file, 'w') as f:
                json.dump(serializable_downloads, f, indent=4)
            logger.info("Download history saved.")
        except Exception as e:
            logger.error(f"Error saving download history to '{self.download_history_file}': {e}")

    def load_download_history(self):
        """Load download history from a JSON file."""
        if not os.path.exists(self.download_history_file):
            logger.info("No download history file found.")
            return

        try:
            with open(self.download_history_file, 'r') as f:
                history = json.load(f)
            self.downloads = history
            logger.info("Download history loaded.")
        except Exception as e:
            logger.error(f"Error loading download history from '{self.download_history_file}': {e}")
            self.downloads = []


class CustomTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setMouseTracking(True)
        self._preview = QLabel(self, flags=Qt.ToolTip | Qt.FramelessWindowHint)
        self._preview.setStyleSheet("""
            QLabel {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                padding: 5px;
            }
        """)
        self._preview.hide()
        
    def mouseMoveEvent(self, event):
        index = self.tabAt(event.pos())
        if index >= 0:
            webview = self.parent().widget(index)
            if webview:
                # Get a thumbnail of the page
                thumbnail = webview.grab().scaled(QSize(300, 200), Qt.KeepAspectRatio)
                
                # Create a pixmap with the thumbnail and title
                pixmap = QPixmap(300, 220)
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                painter.drawPixmap(0, 0, thumbnail)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(QRect(0, 200, 300, 20), Qt.AlignCenter, self.tabText(index))
                painter.end()
                
                self._preview.setPixmap(pixmap)
                self._preview.move(self.mapToGlobal(event.pos()) + QPoint(20, 20))
                self._preview.show()
        else:
            self._preview.hide()
        super().mouseMoveEvent(event)
        
    def leaveEvent(self, event):
        self._preview.hide()
        super().leaveEvent(event)



class VideoDownloader(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.browser = parent
        self.video_extensions = ('.mp4', '.webm', '.mkv', '.mov', '.avi')
        
    def setup_webview_connections(self, webview):
        """Connect signals for video download detection"""
        webview.loadFinished.connect(lambda ok: self.check_for_video(webview, ok))
        
    def check_for_video(self, webview, ok):
        """Check if loaded page contains a video"""
        if not ok:
            return
            
        url = webview.url().toString()
        if self.is_video_url(url):
            self.prompt_download(url)
            
    def is_video_url(self, url):
        """Check if URL ends with video extension"""
        url_lower = url.lower()
        return any(url_lower.endswith(ext) for ext in self.video_extensions)
        
    def prompt_download(self, url):
        """Ask user if they want to download the video"""
        reply = QMessageBox.question(
            self.browser,
            "Video Detected",
            f"Would you like to download this video?\n{url}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.handle_download(url)
            
    def handle_download(self, url):
        """Handle the video download process"""
        # Get download directory
        download_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        if not download_dir:
            download_dir = os.path.expanduser("~/Downloads")
        
        # Get filename
        filename = os.path.basename(urlparse(url).path)
        if not filename or '.' not in filename:
            filename = f"video_{int(time.time())}.mp4"
            
        filepath = os.path.join(download_dir, filename)
        
        # Check if file exists
        if os.path.exists(filepath):
            reply = QMessageBox.question(
                self.browser,
                "File Exists",
                f"{filename} already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
                
        # Start download in background without progress dialog
        self.download_with_curl(url, filepath)
        
    def download_with_curl(self, url, output_path):
        """Download using curl without progress dialog"""
        try:
            cmd = [
                'curl',
                '-L',  # Follow redirects
                '-o', output_path,
                '--silent',  # No progress output
                url
            ]
            
            # Start process in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Show message that download started
            self.browser.statusBar_.showMessage(f"Downloading {os.path.basename(output_path)}...", 3000)
            
            # Check completion in background
            def check_completion():
                return_code = process.poll()
                if return_code is not None:
                    if return_code == 0:
                        self.browser.statusBar_.showMessage(
                            f"Download complete: {os.path.basename(output_path)}", 
                            5000
                        )
                    else:
                        error = process.stderr.read()
                        QMessageBox.critical(
                            self.browser,
                            "Download Failed",
                            error or "Unknown error occurred"
                        )
                else:
                    # Check again in 1 second
                    QTimer.singleShot(1000, check_completion)
            
            # Start checking for completion
            QTimer.singleShot(1000, check_completion)
            
        except Exception as e:
            QMessageBox.critical(
                self.browser,
                "Error",
                f"Failed to start download:\n{str(e)}"
            )



    def force_download(self, url):
        """Force download of a URL that might otherwise try to display"""
        # Create a hidden webview to trigger the download
        temp_view = QWebEngineView()
        temp_view.setAttribute(Qt.WA_DontShowOnScreen, True)
        temp_view.setFixedSize(1, 1)
        
        # Create page with muted audio
        page = QWebEnginePage(QWebEngineProfile.defaultProfile(), temp_view)
        page.setAudioMuted(True)
        temp_view.setPage(page)
        
        # Load the URL which will trigger the download
        temp_view.load(QUrl(url))
        
        # Clean up after a delay
        QTimer.singleShot(30000, temp_view.deleteLater)  # 30 second timeout





# --- BrowserWindow (Main Application Window) ---

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        QObject.__init__(self)
        # Set up application attributes for better platform integration
        QCoreApplication.setApplicationName("StormBrowser")
        QCoreApplication.setOrganizationName("StormOS_Apps")
        QCoreApplication.setApplicationVersion("1.1")

        # --- User Data Directories ---
        # Ensure consistent user data and cache paths for the web engine profile
        self.app_data_dir = os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), "StormBrowser")
        self.cache_dir = os.path.join(self.app_data_dir, "cache")
        self.profile_dir = os.path.join(self.app_data_dir, "profile")
        os.makedirs(self.app_data_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.profile_dir, exist_ok=True)
        logger.info(f"User data directory: {self.app_data_dir}")

        # Set up QWebEngineProfile
        # This profile will be used by all QWebEnginePage instances
        self.web_profile = QWebEngineProfile("StormBrowserProfile", self)
        self.web_profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
        self.web_profile.setCachePath(self.cache_dir)
        self.web_profile.setPersistentStoragePath(self.profile_dir)

        # Removed the problematic lines:
        # self.browserView.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        # self.web_profile.defaultSettings().setAttribute(QWebEngineSettings.AutoLoadImages, True)
        # self.web_profile.defaultSettings().setAttribute(QWebEngineSettings.DnsPrefetchEnabled, False)
        # self.web_profile.defaultSettings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        # self.web_profile.defaultSettings().setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)
        # These settings should be applied to the QWebEngineView (or its QWebEnginePage)
        # when you create a new tab in your _add_new_tab method.

        # Handle proxy settings if needed
        # self.web_profile.setHttpProxy(...)

        # --- Bookmarks and History Files ---
        self.bookmarks_file = os.path.join(self.app_data_dir, "bookmarks.json")
        self.bookmarks = self.load_bookmarks()

        self.history_file = os.path.join(self.app_data_dir, "history.json")
        self.history = self.load_history()

        # --- Download Manager Instance ---
        self.download_manager = DownloadManager(self) # Pass self (BrowserWindow) to DownloadManager

        # --- Central Widget: Tabbed Browser ---
        self.tabs = QTabWidget()
        self.tabs.setTabBar(CustomTabBar())
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self._tab_double_clicked)
        self.tabs.currentChanged.connect(self._current_tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self.tabs)

        # Apply dark theme using QPalette (global for the app or specific to widgets)
        self._apply_dark_theme() # Note: 'app' needs to be accessible in this method's scope

        # --- Status Bar ---
        self.statusBar_ = self.statusBar() # Use standard statusBar() method
        self.statusBar_.showMessage("Ready", 3000)

        # --- Navigation Bar (ToolBar) ---
        self.nav_bar = QToolBar("Navigation")
        self.nav_bar.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.TopToolBarArea, self.nav_bar)

        # Navigation Buttons
        self.back_btn = QAction(QIcon.fromTheme("go-previous"), "Back", self)
        self.back_btn.setStatusTip("Go to previous page")
        self.back_btn.triggered.connect(self._go_back)
        self.nav_bar.addAction(self.back_btn)

        self.forward_btn = QAction(QIcon.fromTheme("go-next"), "Forward", self)
        self.forward_btn.setStatusTip("Go to next page")
        self.forward_btn.triggered.connect(self._go_forward)
        self.nav_bar.addAction(self.forward_btn)

        self.reload_btn = QAction(QIcon.fromTheme("view-refresh"), "Reload", self)
        self.reload_btn.setStatusTip("Reload current page")
        self.reload_btn.triggered.connect(self._reload_page)
        self.nav_bar.addAction(self.reload_btn)

        self.home_btn = QAction(QIcon.fromTheme("go-home"), "Home", self)
        self.home_btn.setStatusTip("Go to home page")
        self.home_btn.triggered.connect(self._navigate_home)
        self.nav_bar.addAction(self.home_btn)

        # URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.setStatusTip("Enter URL and press Enter")
        self.url_bar.returnPressed.connect(self._navigate_to_url)
        self.url_bar.installEventFilter(self)
        self.nav_bar.addWidget(self.url_bar)


        # Add this AFTER your existing toolbar buttons but BEFORE the URL bar:
        self.screenshot_btn = QAction(QIcon.fromTheme("camera-photo"), "Take Screenshot", self)
        self.screenshot_btn.setStatusTip("Capture page screenshot")
        self.screenshot_btn.triggered.connect(self._take_screenshot)
        self.nav_bar.addAction(self.screenshot_btn)


        # Add Tab Button on Navigation Bar
        self.add_tab_btn = QAction(QIcon.fromTheme("tab-new"), "New Tab", self)
        self.add_tab_btn.setStatusTip("Open a new tab")
        self.add_tab_btn.triggered.connect(self._add_new_tab_action)
        self.nav_bar.addAction(self.add_tab_btn)

        # --- Create Menus (File, Edit, View, Bookmarks, History, Tools, Help) ---
        self._create_menus()

        # Set Window Properties
        self.setWindowTitle("StormBrowser")
        self.setWindowIcon(QIcon.fromTheme("web-browser"))
        self.showMaximized() # Start maximized

        # Add initial tab
        self._add_new_tab(QUrl("https://www.google.com"))



        
    def move_tab_left(self):
        current_index = self.tabs.currentIndex()
        if current_index > 0:
            self.tabs.tabBar().moveTab(current_index, current_index - 1)
            
    def move_tab_right(self):
        current_index = self.tabs.currentIndex()
        if current_index < self.tabs.count() - 1:
            self.tabs.tabBar().moveTab(current_index, current_index + 1)

    def _take_screenshot(self):
        """Capture the current page and save to clipboard/file."""
        current_webview = self._current_tab_webview()
        if not current_webview:
            QMessageBox.warning(self, "No Tab", "No active tab to capture")
            return

        # Create menu for save options
        menu = QMenu(self)
        
        # Clipboard action
        clipboard_action = QAction(QIcon.fromTheme("edit-copy"), "Copy to Clipboard", self)
        clipboard_action.triggered.connect(lambda: self._capture_to_clipboard(current_webview))
        menu.addAction(clipboard_action)
        
        # Save file action
        save_action = QAction(QIcon.fromTheme("document-save"), "Save to File...", self)
        save_action.triggered.connect(lambda: self._save_screenshot_to_file(current_webview))
        menu.addAction(save_action)
        
        # Handle both menu button click and keyboard shortcut
        sender = self.sender()
        if sender == self.screenshot_btn:  # If called from toolbar button
            # Position menu under toolbar button
            action_rect = self.nav_bar.actionGeometry(sender)
            menu_width = menu.sizeHint().width()
            pos_x = action_rect.x() + (action_rect.width() - menu_width) // 2
            pos_y = action_rect.bottom()
            global_pos = self.nav_bar.mapToGlobal(QPoint(pos_x, pos_y))
            menu.exec_(global_pos)
        else:  # If called from keyboard shortcut or other source
            # Show menu at current mouse position
            menu.exec_(QCursor.pos())


    
    def _capture_to_clipboard(self, webview):
        """Capture the page to clipboard."""
        def _capture_callback(image):
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(QPixmap.fromImage(image))
            self.statusBar().showMessage("Screenshot copied to clipboard", 3000)

        self._capture_page(webview, _capture_callback)

    def _save_screenshot_to_file(self, webview):
        """Capture the page to a file."""
        def _save_callback(image):
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save Screenshot", 
                f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                "PNG Images (*.png);;JPEG Images (*.jpg *.jpeg);;All Files (*)"
            )
            
            if file_path:
                image.save(file_path)
                self.statusBar().showMessage(f"Screenshot saved to {file_path}", 3000)

        self._capture_page(webview, _save_callback)

    def _capture_page(self, webview, callback):
        """Generic page capture function."""
        rect = webview.contentsRect()
        image = QImage(rect.size(), QImage.Format_ARGB32)
        painter = QPainter(image)
        
        webview.render(painter)
        painter.end()
        
        callback(image)


    def eventFilter(self, obj, event):
        """Handle special key combinations in the URL bar."""
        if obj is self.url_bar and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                modifiers = event.modifiers()
                
                # Get the current text
                text = self.url_bar.text().strip()
                
                if text and not any(c in text for c in (' ', '/', '.')) and not text.startswith(('http://', 'https://')):
                    # Handle special enter key combinations
                    if modifiers & Qt.ControlModifier and modifiers & Qt.ShiftModifier:
                        # Ctrl+Shift+Enter -> add .org
                        text = f"www.{text}.org"
                    elif modifiers & Qt.ShiftModifier:
                        # Shift+Enter -> add .net
                        text = f"www.{text}.net"
                    elif modifiers & Qt.ControlModifier:
                        # Ctrl+Enter -> add .com
                        text = f"www.{text}.com"
                    
                    # Update the URL bar
                    self.url_bar.setText(f"https://{text}")
                    self.url_bar.setCursorPosition(len(self.url_bar.text()))
        
        # Let the base class handle other events
        return super().eventFilter(obj, event)



    def _download_with_curl(self, url):
        """Download a file using curl in the background"""
        try:
            # Get download directory
            download_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
            if not download_dir:
                download_dir = os.path.expanduser("~/Downloads")
            
            # Get filename from URL
            filename = os.path.basename(url.path())
            if not filename:
                filename = f"download_{int(time.time())}"
            
            filepath = os.path.join(download_dir, filename)
            
            # Build curl command
            cmd = [
                'curl',
                '-L',  # Follow redirects
                '-o', filepath,
                '--progress-bar',
                url.toString()
            ]
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Show notification
            self.statusBar_.showMessage(f"Downloading with curl: {filename}", 3000)
            
            # Check completion in background
            def check_completion():
                return_code = process.poll()
                if return_code is not None:
                    if return_code == 0:
                        self.statusBar_.showMessage(
                            f"Download complete: {filename}", 
                            5000
                        )
                        if NOTIFICATION_AVAILABLE:
                            notify2.Notification(
                                "Download Complete",
                                f"File saved to: {filepath}"
                            ).show()
                    else:
                        error = process.stderr.read()
                        QMessageBox.critical(
                            self,
                            "Download Failed",
                            f"cURL error: {error or 'Unknown error'}"
                        )
            
            QTimer.singleShot(1000, check_completion)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to start curl download: {str(e)}"
            )





    def _apply_dark_theme(self):
            """Applies a dark theme using QPalette and QSS."""
            # Ensure 'app' (QApplication instance) is accessible, e.g., via 'global app' or by passing it
            global app # This line might be needed if 'app' isn't in scope
            app.setStyle("Fusion") # Fusion style is good for customization

            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)

            # Corrected line: Set QPalette.Text for the Disabled group
            palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
            palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127)) # Also for disabled button text
            palette.setColor(QPalette.Disabled, QPalette.Button, QColor(63, 63, 63)) # Original disabled button color

            # Apply the palette to the entire application for consistent theming
            QApplication.instance().setPalette(palette)


            # Apply QSS for more detailed styling, especially for tab bar and URL bar
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                }
                QToolBar {
                    background-color: #333;
                    border: none;
                    spacing: 5px;
                }
                QToolButton {
                    background-color: #444;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 4px;
                }
                QToolButton:hover {
                    background-color: #555;
                }
                QToolButton:pressed {
                    background-color: #666;
                }
                QLineEdit {
                    background-color: #3a3a3a;
                    color: white;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 5px;
                    selection-background-color: #4285F4;
                }
                QTabWidget::pane { /* The tab widget frame */
                    border: 1px solid #3a3a3a;
                    background-color: #2b2b2b;
                }
                QTabWidget::tab-bar {
                    left: 5px; /* move to the right by 5px */
                }
                QTabBar::tab {
                    background: #3a3a3a;
                    border: 1px solid #4a4a4a;
                    border-bottom-color: #3a3a3a; /* same as pane color */
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    min-width: 8ex;
                    padding: 5px 10px;
                    color: white;
                }
                QTabBar::tab:selected {
                    background: #2b2b2b;
                    border-bottom-color: #2b2b2b; /* matches pane color */
                }
                QTabBar::tab:hover {
                    background: #4a4a4a;
                }
                QTabBar::tab:!selected {
                    margin-top: 2px; /* make non-selected tabs look sunken */
                }
                QTabBar::close-button {
                    image: url(close_icon.png); /* You might need custom close icons */
                    background: none;
                    border: none;
                }
                QTabBar::close-button:hover {
                    background: #f44336; /* Red on hover */
                }
                QStatusBar {
                    background-color: #333;
                    color: white;
                    border-top: 1px solid #555;
                }
                QMenu {
                    background-color: #3a3a3a;
                    border: 1px solid #555;
                    color: white;
                }
                QMenu::item {
                    padding: 5px 20px 5px 25px; /* top, right, bottom, left */
                    border: 1px solid transparent; /* reserve space for selection border */
                }
                QMenu::item:selected {
                    background-color: #4285F4; /* Google Blue */
                    color: white;
                }
                QMenu::separator {
                    height: 1px;
                    background: #555;
                    margin-left: 10px;
                    margin-right: 10px;
                    margin-top: 5px;
                    margin-bottom: 5px;
                }
            """)

    def _create_menus(self):
        # --- File Menu ---
        file_menu = self.menuBar().addMenu("&File")


        # Add to your existing back/forward button setup:
        self.back_btn.setShortcut("Alt+Left")
        self.forward_btn.setShortcut("Alt+Right")



        new_tab_action = QAction(QIcon.fromTheme("tab-new"), "&New Tab", self)
        new_tab_action.setShortcut("Ctrl+T")  # <-- Add this line
        new_tab_action.setStatusTip("Open a new blank tab")
        new_tab_action.triggered.connect(self._add_new_tab_action)
        file_menu.addAction(new_tab_action)

        close_tab_action = QAction(QIcon.fromTheme("tab-close"), "&Close Current Tab", self)
        close_tab_action.setShortcut("Ctrl+W")  # <-- Add this line
        close_tab_action.setStatusTip("Close the current tab")
        close_tab_action.triggered.connect(self._close_current_tab)
        file_menu.addAction(close_tab_action)

        print_action = QAction(QIcon.fromTheme("document-print"), "&Print...", self)
        print_action.setShortcut("Ctrl+P")  # <-- Add this line
        print_action.setStatusTip("Print the current page")
        print_action.triggered.connect(self._print_page)
        file_menu.addAction(print_action)

        exit_action = QAction(QIcon.fromTheme("application-exit"), "&Exit", self)
        exit_action.setShortcut("Ctrl+Q")  # <-- Add this line
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        file_menu.addSeparator()

        # Add this new action for opening bookmarks/URLs with Ctrl+O
        open_action = QAction("&Open Location/Bookmark", self, shortcut="Ctrl+O")
        open_action.setStatusTip("Open bookmark or URL")
        open_action.triggered.connect(self._open_bookmark_or_url)
        file_menu.addAction(open_action)



        file_menu.addSeparator()


        # --- Edit Menu ---
        edit_menu = self.menuBar().addMenu("&Edit")

        # --- THE CORRECTED COPY ACTION ---
        copy_action = QAction(QIcon.fromTheme("edit-copy"), "&Copy", self, shortcut=QKeySequence.Copy)
        copy_action.setStatusTip("Copy selected text to clipboard")
        edit_menu.addAction(copy_action)
        copy_action.triggered.connect(self._perform_copy_action)

        cut_action = QAction(QIcon.fromTheme("edit-cut"), "Cu&t", self, shortcut=QKeySequence.Cut)
        cut_action.setStatusTip("Cut selected text to clipboard")
        edit_menu.addAction(cut_action)
        cut_action.triggered.connect(self._perform_cut_action)

        paste_action = QAction(QIcon.fromTheme("edit-paste"), "&Paste", self, shortcut=QKeySequence.Paste)
        paste_action.setStatusTip("Paste text from clipboard")
        edit_menu.addAction(paste_action)
        paste_action.triggered.connect(self._perform_paste_action)

        edit_menu.addSeparator()

        select_all_action = QAction(QIcon.fromTheme("edit-select-all"), "Select &All", self, shortcut=QKeySequence.SelectAll)
        select_all_action.setStatusTip("Select all content on the page")
        edit_menu.addAction(select_all_action)
        select_all_action.triggered.connect(self._perform_select_all_action)

        # --- View Menu ---
        view_menu = self.menuBar().addMenu("&View")

        zoom_in_action = QAction(QIcon.fromTheme("zoom-in"), "Zoom &In", self, shortcut="Ctrl++")
        zoom_in_action.setStatusTip("Zoom in on the current page")
        view_menu.addAction(zoom_in_action)
        zoom_in_action.triggered.connect(self._zoom_in)

        zoom_out_action = QAction(QIcon.fromTheme("zoom-out"), "Zoom &Out", self, shortcut="Ctrl+-")
        zoom_out_action.setStatusTip("Zoom out on the current page")
        view_menu.addAction(zoom_out_action)
        zoom_out_action.triggered.connect(self._zoom_out)

        reset_zoom_action = QAction(QIcon.fromTheme("zoom-original"), "&Actual Size", self, shortcut="Ctrl+0")
        reset_zoom_action.setStatusTip("Reset page zoom to actual size")
        view_menu.addAction(reset_zoom_action)
        reset_zoom_action.triggered.connect(self._reset_zoom)

        view_menu.addSeparator()

        full_screen_action = QAction(QIcon.fromTheme("view-fullscreen"), "&Full Screen", self, shortcut="F11", checkable=True)
        full_screen_action.setStatusTip("Toggle full screen mode")
        full_screen_action.toggled.connect(self._toggle_full_screen)
        view_menu.addAction(full_screen_action)

        # --- Bookmarks Menu ---
        bookmarks_menu = self.menuBar().addMenu("&Bookmarks")

        add_bookmark_action = QAction(QIcon.fromTheme("bookmark-new"), "&Add Bookmark...", self, shortcut="Ctrl+D")
        add_bookmark_action.setStatusTip("Add the current page to bookmarks")
        add_bookmark_action.triggered.connect(self._add_current_page_as_bookmark)
        bookmarks_menu.addAction(add_bookmark_action)

        show_bookmarks_action = QAction(QIcon.fromTheme("bookmarks-organize"), "&Show All Bookmarks", self)
        show_bookmarks_action.setStatusTip("Manage your bookmarks")
        show_bookmarks_action.triggered.connect(self._show_bookmark_manager)
        bookmarks_menu.addAction(show_bookmarks_action)

        # --- History Menu ---
        history_menu = self.menuBar().addMenu("&History")
        # Populate history menu dynamically or link to manager
        show_history_action = QAction(QIcon.fromTheme("document-open-recent"), "&Show All History", self, shortcut="Ctrl+H")
        show_history_action.setStatusTip("View your Browse history")
        show_history_action.triggered.connect(self._show_history_dialog)
        history_menu.addAction(show_history_action)

        clear_history_action = QAction(QIcon.fromTheme("edit-clear"), "Clear Browse &Data...", self)
        clear_history_action.setStatusTip("Clear Browse history, cache, and cookies")
        clear_history_action.triggered.connect(self._clear_Browse_data)
        history_menu.addAction(clear_history_action)

        # --- Tools Menu ---
        tools_menu = self.menuBar().addMenu("&Tools")
        download_manager_action = QAction(QIcon.fromTheme("folder-download"), "&Downloads", self, shortcut="Ctrl+J")
        download_manager_action.setStatusTip("Open the download manager")
        download_manager_action.triggered.connect(self.download_manager.create_download_manager_window)
        tools_menu.addAction(download_manager_action)



        # Ad-blocker toggle
        self.adblock_action = QAction("Enable Ad-blocker", self, checkable=True)
        self.adblock_action.setChecked(True)
        self.adblock_action.triggered.connect(self.toggle_adblocker)
        tools_menu.addAction(self.adblock_action)



        # Add this with your other tools menu actions
        screenshot_action = QAction(QIcon.fromTheme("camera-photo"), "Take Screenshot", self)
        screenshot_action.setShortcut("Ctrl+Shift+S")  # Set your preferred shortcut here
        screenshot_action.setStatusTip("Capture page screenshot")
        screenshot_action.triggered.connect(self._take_screenshot)
        tools_menu.addAction(screenshot_action)


        devtools_action = QAction(QIcon.fromTheme("applications-development"), "&Developer Tools", self, shortcut="F12")
        devtools_action.setStatusTip("Open web developer tools for the current page")
        devtools_action.triggered.connect(self._open_developer_tools)
        tools_menu.addAction(devtools_action)

        # --- Help Menu ---
        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("About &StormBrowser", self)
        about_action.setStatusTip("Show information about StormBrowser")
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)


        # In the help_menu section of _create_menus():
        shortcuts_action = QAction("Keyboard &Shortcuts", self)
        shortcuts_action.setStatusTip("Show all available keyboard shortcuts")
        shortcuts_action.triggered.connect(self._show_shortcuts_help)
        help_menu.addAction(shortcuts_action)


    # --- Browser Core Functionality ---

    def toggle_adblocker(self, enabled):
        """Toggle ad-blocker on/off for all tabs."""
        for i in range(self.tabs.count()):
            webview = self.tabs.widget(i)
            if hasattr(webview, 'page') and hasattr(webview.page(), 'adblocker'):
                webview.page().adblocker.enabled = enabled
        status = "enabled" if enabled else "disabled"
        self.statusBar().showMessage(f"Ad-blocker {status}", 2000)





    def _show_shortcuts_help(self):
        """Display a dialog with all available keyboard shortcuts."""
        shortcuts_dialog = QDialog(self)
        shortcuts_dialog.setWindowTitle("Keyboard Shortcuts")
        shortcuts_dialog.resize(500, 600)
        
        layout = QVBoxLayout()
        
        # Create a text area with all shortcuts
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("font-family: monospace;")
        
        # Format the shortcuts in aligned columns
        shortcuts = [
            ("Navigation", ""),
            ("Ctrl+T", "New Tab"),
            ("Ctrl+W", "Close Tab"),
            ("Ctrl+Tab", "Next Tab"),
            ("Ctrl+Shift+Tab", "Previous Tab"),
            ("Ctrl+O", "Open URL/Bookmark"),
            ("Ctrl+L", "Focus URL Bar"),
            ("F5/Ctrl+R", "Reload"),
            ("Ctrl+H", "History"),
            ("Ctrl+J", "Downloads"),
            ("", ""),
            ("Zoom", ""),
            ("Ctrl++", "Zoom In"),
            ("Ctrl+-", "Zoom Out"),
            ("Ctrl+0", "Reset Zoom"),
            ("", ""),
            ("Page Control", ""),
            ("Alt+Left", "Back"),
            ("Alt+Right", "Forward"),
            ("Ctrl+P", "Print"),
            ("F11", "Fullscreen"),
            ("F12", "Developer Tools"),
            ("", ""),
            ("Editing", ""),
            ("Ctrl+C", "Copy"),
            ("Ctrl+X", "Cut"),
            ("Ctrl+V", "Paste"),
            ("Ctrl+A", "Select All"),
            ("", ""),
            ("Application", ""),
            ("Ctrl+N", "New Window"),
            ("Ctrl+Q", "Quit")
        ]
        
        # Calculate maximum key length for alignment
        max_key_len = max(len(shortcut[0]) for shortcut in shortcuts)
        
        # Build the formatted text
        formatted_text = ""
        for key, description in shortcuts:
            if not description:  # Section header
                formatted_text += f"\n<b>{key}</b>\n" if key else "\n"
            else:
                formatted_text += f"{key.ljust(max_key_len)}   {description}\n"
        
        text_edit.setText(formatted_text)
        
        # Add OK button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(shortcuts_dialog.accept)
        
        layout.addWidget(text_edit)
        layout.addWidget(button_box)
        shortcuts_dialog.setLayout(layout)
        
        shortcuts_dialog.exec_()

    def _open_bookmark_or_url(self):
        """Open the URL/bookmark launcher dialog with blank URL field"""
        # Create the launcher dialog with current bookmarks
        launcher = CombinedLauncher(self, self.bookmarks)
        
        # Clear the entry field (instead of pre-filling with current URL)
        launcher.entry.clear()
        launcher.update_results()
        
        # Show the dialog and handle the result
        if launcher.exec_() == QDialog.Accepted and launcher.selected_url:
            url_text = launcher.selected_url
            
            # Ensure the URL has a scheme (default to https:// if none)
            if not any(url_text.startswith(proto) for proto in ('http://', 'https://', 'ftp://', 'file://')):
                if '.' in url_text:  # Looks like a domain
                    url_text = f'https://{url_text}'
                else:  # Treat as search query
                    url_text = f'https://www.google.com/search?q={url_text}'
            
            qurl = QUrl(url_text)
            if qurl.isValid():
                # Open in new tab and add to history
                self._add_new_tab(qurl, add_to_history=True)
                self.statusBar_.showMessage(f"Opened: {url_text}", 3000)
            else:
                self.statusBar_.showMessage(f"Invalid URL: {url_text}", 3000)


    def _add_new_tab(self, qurl=QUrl(''), make_current=True, add_to_history=True):
        """Adds a new browser tab with all necessary connections and features."""
        webview = QWebEngineView()
        custom_page = CustomWebEnginePage(self.web_profile, webview)
        webview.setPage(custom_page)
        
        # Initialize ad-blocker if available
        if hasattr(custom_page, 'adblocker') and hasattr(self, 'adblock_action'):
            custom_page.adblocker.enabled = self.adblock_action.isChecked()
        
        # Set initial URL
        if qurl.isEmpty() or not qurl.isValid():
            qurl = QUrl("https://www.google.com")
        webview.setUrl(qurl)

        # Add tab to UI
        tab_index = self.tabs.addTab(webview, "Loading...")
        webview.setProperty("tab_index", tab_index)

        # Connect signals
        webview.urlChanged.connect(lambda q, wv=webview: self._update_url_bar(q, wv))
        webview.loadFinished.connect(lambda ok, wv=webview: self._on_load_finished(ok, wv))
        webview.titleChanged.connect(lambda title, wv=webview: self._update_tab_title(title, wv))
        webview.iconChanged.connect(lambda icon: self._update_tab_icon(webview, icon))
        
        custom_page.new_window_requested.connect(self._handle_new_webview_request)
        custom_page.force_download_requested.connect(self.download_manager.handle_forced_download_url)
        webview.page().linkHovered.connect(self.statusBar().showMessage)
        webview.loadStarted.connect(lambda: self.statusBar().showMessage(f"Loading: {webview.url().toString()}", 0))

        # Set up context menu
        webview.setContextMenuPolicy(Qt.CustomContextMenu)
        webview.customContextMenuRequested.connect(
            lambda pos: self._show_tab_context_menu(webview, pos))

        if make_current:
            self.tabs.setCurrentIndex(tab_index)

        self._update_url_bar(qurl, webview)
        self._update_buttons_state()
        
        if add_to_history:
            self._add_to_history(qurl.toString(), "New Tab")
            
        return webview

    def _update_tab_icon(self, webview, icon):
        """Update the tab icon for the given webview."""
        try:
            tab_index = self.tabs.indexOf(webview)
            if tab_index != -1:
                if icon.isNull():
                    # Set default icon if no favicon available
                    icon = QIcon.fromTheme("text-html")
                self.tabs.setTabIcon(tab_index, icon)
        except Exception as e:
            logger.error(f"Error updating tab icon: {e}")

    def _show_tab_context_menu(self, webview, pos):
        """Show context menu for the tab."""
        menu = QMenu(self)
        
        # Get the page's standard context menu
        if hasattr(webview, 'page') and hasattr(webview.page(), 'createStandardContextMenu'):
            page_menu = webview.page().createStandardContextMenu()
            menu.addMenu(page_menu)
        
        # Add custom tab actions
        menu.addSeparator()
        
        reload_action = QAction("Reload Tab", self)
        reload_action.triggered.connect(webview.reload)
        menu.addAction(reload_action)
        
        close_action = QAction("Close Tab", self)
        close_action.triggered.connect(lambda: self._close_tab(self.tabs.indexOf(webview)))
        menu.addAction(close_action)
        
        menu.exec_(webview.mapToGlobal(pos))

    def _handle_new_webview_request(self, webview):
        """Handle new window requests with QWebEngineView parameter"""
        try:
            i = self.tabs.addTab(webview, "New Window")
            webview.setProperty("tab_index", i)
            self.tabs.setCurrentIndex(i)
            
            # Reconnect signals
            webview.urlChanged.connect(lambda q, wv=webview: self._update_url_bar(q, wv))
            webview.loadFinished.connect(lambda ok, wv=webview: self._on_load_finished(ok, wv))
            webview.titleChanged.connect(lambda title, wv=webview: self._update_tab_title(title, wv))
            webview.page().linkHovered.connect(self.statusBar_.showMessage)
            webview.loadStarted.connect(lambda wv=webview: self.statusBar_.showMessage(f"Loading: {wv.url().toString()}", 0))
        except Exception as e:
            logger.error(f"Error handling new webview: {str(e)}")
            QMessageBox.critical(self, "Error", "Failed to create new window")

    def _add_new_tab_action(self):
        """Action handler for opening a new blank tab."""
        self._add_new_tab()

    def _handle_new_window_request(self, page: QWebEnginePage):
        """Handles requests from web content to open a new window/tab."""
        webview = QWebEngineView()
        webview.add_to_history = False  # Don't add popup windows to history by default
        webview.setPage(page)

        # Re-connect signals - CORRECTED VERSION:
        webview.urlChanged.connect(lambda q, wv=webview: self._update_url_bar(q, wv))
        webview.loadFinished.connect(lambda ok, wv=webview: self._on_load_finished(ok, wv))
        webview.titleChanged.connect(lambda title, wv=webview: self._update_tab_title(title, wv))
        webview.page().linkHovered.connect(self.statusBar_.showMessage)  # <-- Connect to page() not webview
        webview.loadStarted.connect(lambda wv=webview: self.statusBar_.showMessage(f"Loading: {wv.url().toString()}", 0))

        if isinstance(page, CustomWebEnginePage):
            page.browser_main_window = self

        i = self.tabs.addTab(webview, "New Window")
        webview.setProperty("tab_index", i)
        self.tabs.setCurrentIndex(i)
        self.statusBar_.showMessage(f"New window requested by page: {page.url().toString()}", 3000)
        logger.info(f"New window/tab requested by web content for URL: {page.url().toString()}")

    def _current_tab_webview(self) -> QWebEngineView:
        """Returns the QWebEngineView of the currently active tab, or None."""
        return self.tabs.currentWidget()

    def _update_url_bar(self, q: QUrl, browser: QWebEngineView = None):
        """Updates the URL bar with the current page's URL."""
        # Only update if the URL change is for the currently active browser
        if browser is None or browser != self._current_tab_webview():
            return
        self.url_bar.setText(q.toDisplayString()) # Use toDisplayString for cleaner URLs
        self.url_bar.setCursorPosition(0) # Move cursor to the beginning
        logger.debug(f"URL bar updated to: {q.toDisplayString()}")

    def _update_tab_title(self, title: str, webview: QWebEngineView):
        """Updates the tab's title."""
        index = self.tabs.indexOf(webview)
        if index != -1:
            self.tabs.setTabText(index, title or "Untitled") # Default to "Untitled" if no title
            self.tabs.setTabToolTip(index, title or webview.url().toDisplayString())
            logger.debug(f"Tab {index} title updated to: {title}")

    def _on_load_finished(self, ok: bool, webview: QWebEngineView):
        """Handles actions after a page finishes loading."""
        if webview != self._current_tab_webview():
            return  # Only process for the active tab

        if ok:
            title = webview.page().title()
            url = webview.url().toDisplayString()
            self._update_tab_title(title, webview)
            self._update_url_bar(webview.url(), webview)
            
            # Only add to history if the tab was created with add_to_history=True
            if getattr(webview, 'add_to_history', True):
                self._add_to_history(url, title)
                
            self.statusBar_.showMessage(f"Page loaded: {title}", 3000)
            logger.info(f"Page loaded successfully: {url}")
        else:
            self.statusBar_.showMessage(f"Page failed to load: {webview.url().toDisplayString()}", 5000)
            logger.warning(f"Page failed to load: {webview.url().toString()}")

    def _navigate_to_url(self):
        """Navigates the current tab to the URL entered in the URL bar."""
        text = self.url_bar.text().strip()
        if not text:
            return

        if ' ' in text and not any(c in text for c in ('.', '/')):
            search_query = urlencode({'q': text})
            q = QUrl(f"https://www.google.com/search?{search_query}")
        else:
            q = QUrl(text)
            if not q.isValid() or q.scheme() == "":
                if not text.startswith(('http://', 'https://')):
                    text = f"https://{text}"
                q = QUrl(text)
                
                if not q.isValid():
                    search_query = urlencode({'q': text})
                    q = QUrl(f"https://www.google.com/search?{search_query}")

        current_webview = self._current_tab_webview()
        if current_webview:
            current_webview.setUrl(q)
            self.statusBar_.showMessage(f"Navigating to: {q.toDisplayString()}", 3000)
            logger.info(f"User navigated to: {q.toString()}")
        else:
            # Regular navigation should add to history
            self._add_new_tab(q, add_to_history=True)
            self.statusBar_.showMessage(f"Opened new tab for: {q.toDisplayString()}", 3000)
            logger.info(f"New tab opened via URL bar for: {q.toString()}")


    def _is_valid_url(self, text):
        """Check if the text is a valid URL."""
        # Simple check for common URL patterns
        patterns = [
            r'^https?://',  # http:// or https://
            r'^ftp://',      # ftp://
            r'^file://',     # file://
            r'^www\.',       # www.
            r'^\d+\.\d+\.\d+\.\d+',  # IP address
            r'^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}'  # domain.tld
        ]
        return any(re.match(pattern, text) for pattern in patterns)


    def _go_back(self):
        current_webview = self._current_tab_webview()
        if current_webview:
            current_webview.back()
            # Force update after a short delay
            QTimer.singleShot(100, self._update_buttons_state)

    def _go_forward(self):
        current_webview = self._current_tab_webview()
        if current_webview:
            current_webview.forward()
            # Force update after a short delay
            QTimer.singleShot(100, self._update_buttons_state)

    def _reload_page(self):
        """Reloads the current page."""
        current_webview = self._current_tab_webview()
        if current_webview:
            current_webview.reload()
            self.statusBar_.showMessage("Reloading page.", 1000)
            logger.info("Current page reloaded.")

    def _navigate_home(self):
        """Navigates the current tab to the default home page."""
        current_webview = self._current_tab_webview()
        if current_webview:
            current_webview.setUrl(QUrl("https://www.google.com"))
            self.statusBar_.showMessage("Navigating to home page.", 2000)
            logger.info("Navigated to home page.")
        else:
            self._add_new_tab(QUrl("https://www.google.com"))
            self.statusBar_.showMessage("Opened home page in new tab.", 2000)

    def _tab_double_clicked(self, index: int):
        """Handles double-clicking on the tab bar (opens new tab)."""
        if index == -1: # Double-clicked in the empty area of the tab bar
            self._add_new_tab_action()

    def _current_tab_changed(self, index: int):
        """Updates the URL bar and status bar when the active tab changes."""
        if index != -1:
            current_webview = self.tabs.widget(index)
            if current_webview:
                qurl = current_webview.url()
                self._update_url_bar(qurl, current_webview)
                self._update_buttons_state() # Update back/forward buttons
                self.statusBar_.showMessage(f"Tab changed to: {current_webview.page().title() or 'Untitled'}", 2000)
            logger.debug(f"Switched to tab index: {index}")
        else:
            self.url_bar.setText("") # Clear URL bar if no tabs open
            self.back_btn.setEnabled(False)
            self.forward_btn.setEnabled(False)
            self.statusBar_.showMessage("No active tab.", 2000)
            logger.debug("No active tabs.")

    def _close_tab(self, index):
        """Safely close a tab with proper resource cleanup.
        
        Args:
            index: Index of the tab to close
        """
        if index < 0 or index >= self.tabs.count():
            return
            
        widget = self.tabs.widget(index)
        
        # Skip if not a webview or already closed
        if not isinstance(widget, QWebEngineView):
            self.tabs.removeTab(index)
            return
            
        try:
            # Clean up the page
            page = widget.page()
            
            if hasattr(page, '_alive'):
                page._alive = False
                
                # Disconnect all signals first
                try:
                    if hasattr(page, 'disconnect'):
                        page.disconnect()
                except:
                    pass
                    
                # Safe deletion
                if hasattr(page, 'deleteLater') and not sip.isdeleted(page):
                    page.deleteLater()
                    
            # Clean up the webview
            if hasattr(widget, 'deleteLater') and not sip.isdeleted(widget):
                # Disconnect all signals first
                try:
                    if hasattr(widget, 'disconnect'):
                        widget.disconnect()
                except:
                    pass
                    
                widget.deleteLater()
                
        except RuntimeError as e:
            logger.error(f"RuntimeError cleaning up tab {index}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning up tab {index}: {e}")
        finally:
            # Always remove the tab from UI
            self.tabs.removeTab(index)
            
            # Update UI if last tab closed
            if self.tabs.count() == 0:
                self._add_new_tab()
                
            logger.info(f"Closed tab {index}")


        
    def _close_current_tab(self):
        """Closes the currently active tab."""
        self._close_tab(self.tabs.currentIndex())

    def _update_buttons_state(self):
        """Updates back/forward button states based on current tab's history"""
        current_webview = self._current_tab_webview()
        if current_webview:
            try:
                history = current_webview.page().history()
                self.back_btn.setEnabled(history.canGoBack())
                self.forward_btn.setEnabled(history.canGoForward())
            except Exception as e:
                logger.error(f"Error updating button states: {e}")
        else:
            self.back_btn.setEnabled(False)
            self.forward_btn.setEnabled(False)




    # --- Print Functionality ---
    def _print_page(self):
        """Initiates printing of the current web page."""
        current_webview = self._current_tab_webview()
        if not current_webview:
            self.statusBar_.showMessage("No page to print.", 2000)
            return

        printer = QPrinter(QPrinter.HighResolution)
        print_dialog = QPrintDialog(printer, self)
        if print_dialog.exec_() == QDialog.Accepted:
            current_webview.page().print_(printer)
            self.statusBar_.showMessage("Printing page...", 3000)
            logger.info("Print dialog opened and print initiated.")
        else:
            self.statusBar_.showMessage("Print cancelled.", 2000)
            logger.info("Print dialog cancelled.")

    # --- Clipboard / Edit Actions ---
    def _perform_copy_action(self):
        """Performs a copy action on the current web view."""
        current_webview = self._current_tab_webview()
        if current_webview and current_webview.page():
            current_webview.page().copy()
            self.statusBar_.showMessage("Copied selected text.", 1000)
            logger.debug("Copy action performed.")
        else:
            self.statusBar_.showMessage("No active web page to copy from.", 2000)

    def _perform_cut_action(self):
        """Performs a cut action on the current web view."""
        current_webview = self._current_tab_webview()
        if current_webview and current_webview.page():
            current_webview.page().cut()
            self.statusBar_.showMessage("Cut selected text.", 1000)
            logger.debug("Cut action performed.")
        else:
            self.statusBar_.showMessage("No active web page to cut from.", 2000)

    def _perform_paste_action(self):
        """Performs a paste action on the current web view."""
        current_webview = self._current_tab_webview()
        if current_webview and current_webview.page():
            current_webview.page().paste()
            self.statusBar_.showMessage("Pasted text.", 1000)
            logger.debug("Paste action performed.")
        else:
            self.statusBar_.showMessage("No active web page to paste to.", 2000)

    def _perform_select_all_action(self):
        """Performs a select all action on the current web view."""
        current_webview = self._current_tab_webview()
        if current_webview and current_webview.page():
            current_webview.page().selectAll()
            self.statusBar_.showMessage("Selected all content.", 1000)
            logger.debug("Select All action performed.")
        else:
            self.statusBar_.showMessage("No active web page to select all from.", 2000)

    # --- Zoom / View Actions ---
    def _zoom_in(self):
        """Increases the zoom factor of the current web view."""
        current_webview = self._current_tab_webview()
        if current_webview:
            current_webview.setZoomFactor(current_webview.zoomFactor() + 0.1)
            self.statusBar_.showMessage(f"Zoom: {current_webview.zoomFactor()*100:.0f}%", 1000)
            logger.debug(f"Zoomed in to {current_webview.zoomFactor()}")

    def _zoom_out(self):
        """Decreases the zoom factor of the current web view."""
        current_webview = self._current_tab_webview()
        if current_webview:
            current_webview.setZoomFactor(current_webview.zoomFactor() - 0.1)
            self.statusBar_.showMessage(f"Zoom: {current_webview.zoomFactor()*100:.0f}%", 1000)
            logger.debug(f"Zoomed out to {current_webview.zoomFactor()}")

    def _reset_zoom(self):
        """Resets the zoom factor of the current web view to 1.0 (100%)."""
        current_webview = self._current_tab_webview()
        if current_webview:
            current_webview.setZoomFactor(1.0)
            self.statusBar_.showMessage("Zoom: 100%", 1000)
            logger.debug("Zoom reset to 100%.")

    def _toggle_full_screen(self, checked: bool):
        """Toggles full screen mode."""
        if checked:
            self.showFullScreen()
            self.statusBar_.showMessage("Entered full screen mode.", 2000)
        else:
            self.showNormal()
            self.statusBar_.showMessage("Exited full screen mode.", 2000)
        logger.info(f"Full screen toggled: {checked}")

    def _open_new_browser_window(self):
        """Opens a new independent browser window."""
        new_window = BrowserWindow()
        new_window.show()
        logger.info("Opened a new browser window.")

    # --- Bookmarks Management ---
    def load_bookmarks(self):
        """Loads bookmarks from a JSON file."""
        if not os.path.exists(self.bookmarks_file):
            logger.info("No bookmarks file found.")
            return []
        try:
            with open(self.bookmarks_file, 'r') as f:
                bookmarks = json.load(f)
            logger.info("Bookmarks loaded successfully.")
            return bookmarks
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding bookmarks JSON: {e}")
            QMessageBox.warning(self, "Bookmarks Error", f"Could not load bookmarks: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading bookmarks from '{self.bookmarks_file}': {e}")
            QMessageBox.warning(self, "Bookmarks Error", f"Could not load bookmarks: {e}")
            return []

    def save_bookmarks(self):
        """Saves current bookmarks to a JSON file."""
        try:
            with open(self.bookmarks_file, 'w') as f:
                json.dump(self.bookmarks, f, indent=4)
            logger.info("Bookmarks saved successfully.")
        except Exception as e:
            logger.error(f"Error saving bookmarks to '{self.bookmarks_file}': {e}")
            QMessageBox.critical(self, "Save Error", f"Could not save bookmarks: {e}")

    def _add_current_page_as_bookmark(self):
        """Prompts to add the current page as a bookmark."""
        current_webview = self._current_tab_webview()
        if not current_webview:
            self.statusBar_.showMessage("No page to bookmark.", 2000)
            return

        url = current_webview.url().toString()
        title = current_webview.page().title() or "Untitled Page"

        name, ok = QInputDialog.getText(self, "Add Bookmark", "Bookmark Name:", QLineEdit.Normal, title)
        if ok and name:
            new_bookmark = {"name": name, "uri": url}
            # Check for duplicates before adding
            if any(b['uri'] == url for b in self.bookmarks):
                QMessageBox.information(self, "Bookmark Exists", "This URL is already bookmarked.")
                self.statusBar_.showMessage("Bookmark already exists.", 2000)
                return

            self.bookmarks.append(new_bookmark)
            self.save_bookmarks()
            self.statusBar_.showMessage(f"Bookmark added: {name}", 2000)
            logger.info(f"Added bookmark: {name} - {url}")
        elif ok: # User clicked OK but entered empty name
             self.statusBar_.showMessage("Bookmark name cannot be empty.", 2000)
        else:
             self.statusBar_.showMessage("Bookmark addition cancelled.", 2000)


    def _show_bookmark_manager(self):
        """Shows the bookmark manager dialog."""
        dialog = BookmarkManagerDialog(self, self.bookmarks)
        dialog.exec_()
        logger.info("Bookmark Manager dialog shown.")

    # --- History Management ---
    def load_history(self):
        """Loads Browse history from a JSON file."""
        if not os.path.exists(self.history_file):
            logger.info("No history file found.")
            return []
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            logger.info("History loaded successfully.")
            return history
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding history JSON: {e}")
            QMessageBox.warning(self, "History Error", f"Could not load history: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading history from '{self.history_file}': {e}")
            QMessageBox.warning(self, "History Error", f"Could not load history: {e}")
            return []

    def save_history(self):
        """Saves current Browse history to a JSON file."""
        try:
            # Keep history to a reasonable size (e.g., last 1000 entries)
            history_to_save = self.history[-1000:]
            with open(self.history_file, 'w') as f:
                json.dump(history_to_save, f, indent=4)
            logger.info("History saved successfully.")
        except Exception as e:
            logger.error(f"Error saving history to '{self.history_file}': {e}")
            QMessageBox.critical(self, "Save Error", f"Could not save history: {e}")

    def _add_to_history(self, url: str, title: str):
        """Adds a URL and title to the Browse history."""
        # Avoid adding duplicate consecutive entries (e.g., from reloads)
        if self.history and self.history[-1]['url'] == url:
            self.history[-1]['timestamp'] = datetime.now().isoformat() # Update timestamp
            self.history[-1]['title'] = title # Update title in case it changed
        else:
            self.history.append({
                "url": url,
                "title": title,
                "timestamp": datetime.now().isoformat()
            })
        self.save_history() # Save history after each addition
        logger.debug(f"Added to history: {title} - {url}")

    def _show_history_dialog(self):
        """Displays a dialog showing Browse history."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Browse History")
        dialog.resize(800, 600)
        layout = QVBoxLayout(dialog)

        history_list = QListWidget()
        history_list.itemDoubleClicked.connect(lambda item: self._open_history_item(item, dialog))
        layout.addWidget(history_list)

        # Populate list in reverse chronological order
        for entry in reversed(self.history):
            timestamp_dt = datetime.fromisoformat(entry['timestamp'])
            time_str = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")
            item_text = f"[{time_str}] {entry['title']} - {entry['url']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, entry['url'])
            history_list.addItem(item)

        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        dialog.exec_()
        logger.info("History dialog shown.")

    def _open_history_item(self, item: QListWidgetItem, dialog: QDialog):
        """Opens a selected history item in a new tab."""
        url = item.data(Qt.UserRole)
        if url:
            self._add_new_tab(QUrl(url))
            dialog.accept() # Close history dialog
            self.statusBar_.showMessage(f"Opened history item: {url}", 2000)
            logger.info(f"Opened history item: {url}")

    def _clear_Browse_data(self):
        """Clears Browse history, cache, and cookies."""
        reply = QMessageBox.question(self, "Clear Browse Data",
                                     "Are you sure you want to clear Browse history, cache, and cookies? "
                                     "This action cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Clear history
            self.history = []
            self.save_history()
            logger.info("Browse history cleared.")

            # Clear cache
            try:
                self.web_profile.clearHttpCache()
                # Also delete contents of the cache directory directly for certainty
                if os.path.exists(self.cache_dir):
                    shutil.rmtree(self.cache_dir)
                    os.makedirs(self.cache_dir, exist_ok=True) # Recreate empty directory
                logger.info("Browser cache cleared.")
            except Exception as e:
                logger.error(f"Error clearing cache: {e}")

            # Clear cookies
            try:
                cookie_store = self.web_profile.cookieStore()
                cookie_store.deleteAllCookies()
                logger.info("Browser cookies cleared.")
            except Exception as e:
                logger.error(f"Error clearing cookies: {e}")

            QMessageBox.information(self, "Browse Data Cleared", "Browse history, cache, and cookies have been cleared.")
            self.statusBar_.showMessage("Browse data cleared.", 3000)
            logger.info("All Browse data cleared.")
        else:
            self.statusBar_.showMessage("Clear Browse data cancelled.", 2000)

    # --- Developer Tools ---
    def _open_developer_tools(self):
        """Opens developer tools for the current web view."""
        current_webview = self._current_tab_webview()
        if current_webview:
            current_webview.page().triggerAction(QWebEnginePage.InspectElement)
            self.statusBar_.showMessage("Opening Developer Tools.", 2000)
            logger.info("Developer tools opened.")
        else:
            self.statusBar_.showMessage("No active page for Developer Tools.", 2000)

    # --- About Dialog ---
    def _show_about_dialog(self):
        """Displays an about dialog for the browser."""
        QMessageBox.about(self, "About StormBrowser",
                          f"<h3>{QCoreApplication.applicationName()} v{QCoreApplication.applicationVersion()}</h3>"
                          "<p>A simple web browser built with PyQt5 and QtWebEngine.</p>"
                          "<p>Developed by Seeker</p>"
                          "<p>&copy; 2025</p>"
                          "<p>Powered by Chromium</p>")
        self.statusBar_.showMessage("About StormBrowser.", 2000)
        logger.info("About dialog shown.")

    def closeEvent(self, event):
        """Handle main window closing with proper cleanup of all web resources.
        
        Args:
            event: QCloseEvent from Qt
        """
        # Clean up all tabs and web pages
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            
            # Skip if widget is not a webview
            if not isinstance(widget, QWebEngineView):
                continue
                
            try:
                # Safely access and clean up the page
                page = widget.page()
                
                if hasattr(page, '_alive'):
                    page._alive = False  # Mark as not alive
                    
                    # Only try to delete if Qt object still exists
                    if hasattr(page, 'deleteLater') and not sip.isdeleted(page):
                        page.deleteLater()
                        
                # Clean up the webview itself
                if hasattr(widget, 'deleteLater') and not sip.isdeleted(widget):
                    widget.deleteLater()
                    
            except RuntimeError as e:
                logger.error(f"Error cleaning up tab {i}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error cleaning up tab {i}: {e}")
        
        # Clean up download manager resources
        if hasattr(self, 'download_manager'):
            try:
                self.download_manager.save_download_history()
                for download in self.download_manager.downloads:
                    if 'process' in download and download['process']:
                        try:
                            download['process'].terminate()
                        except:
                            pass
            except Exception as e:
                logger.error(f"Error cleaning up downloads: {e}")
        
        # Save session state
        try:
            self.save_bookmarks()
            self.save_history()
        except Exception as e:
            logger.error(f"Error saving session data: {e}")
        
        # Accept the close event
        event.accept()
        logger.info("Browser window closed cleanly")

# Main application entry point
if __name__ == '__main__':
    # Enable high DPI scaling (optional, for better appearance on high-res screens)
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    # Enable use of native OpenGL (optional, can help with rendering issues)
    QApplication.setAttribute(Qt.AA_UseDesktopOpenGL)

    app = QApplication(sys.argv)

    # Set default icon theme if available on the system
    if hasattr(QIcon, 'fromTheme'):
        # On some systems, icon themes need to be explicitly set or available
        # You might need to install 'adwaita-icon-theme' on Linux for example
        # if QIcon.fromTheme('application-exit').isNull():
        #     print("Warning: Icon theme might not be fully functional. Icons may not appear.")
        #     # Fallback to custom icons or a different theme if desired
        pass

    window = BrowserWindow()
    window.show()
    sys.exit(app.exec_())