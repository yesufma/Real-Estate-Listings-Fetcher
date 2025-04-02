#!/usr/bin/env python
# coding: utf-8

# In[1]:


pip install PySide6 pandas xlsxwriter openpyxl


# In[ ]:


import sys
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QTableWidget, QTableWidgetItem,
                              QDockWidget, QProgressBar, QPushButton, QLineEdit, QLabel,
                              QFileDialog, QMessageBox, QStyleFactory, QVBoxLayout,
                              QHBoxLayout, QFrame, QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QSize, QTimer
from PySide6.QtGui import QIcon, QColor, QBrush, QAction, QFont
from scraping_functions import *  # Your existing scraping functions

# ========================
# MODERN GUI COMPONENTS
# ========================
class ScraperThread(QThread):
    update_progress = Signal(int, str)
    scraping_complete = Signal(pd.DataFrame)
    error_occurred = Signal(str)

    def __init__(self, sites_pages):
        super().__init__()
        self.sites_pages = sites_pages

    def run(self):
        try:
            all_data = []
            total = len([p for p in self.sites_pages.values() if p > 0])
            completed = 0

            for site, pages in self.sites_pages.items():
                if pages > 0:
                    try:
                        df = globals()[f"scrape_{site}"](pages)
                        if not df.empty:
                            all_data.append(df)
                            completed += 1
                            self.update_progress.emit(int((completed/total)*100), 
                                                    f"Scraping {site}...")
                    except Exception as e:
                        self.error_occurred.emit(f"{site} error: {str(e)}")

            if all_data:
                final_df = pd.concat(all_data).reset_index(drop=True)
                self.scraping_complete.emit(final_df)
            else:
                self.scraping_complete.emit(pd.DataFrame())

        except Exception as e:
            self.error_occurred.emit(f"Thread error: {str(e)}")

class ModernTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setup_table()
        self.setSortingEnabled(True)

    def setup_table(self):
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["Title", "Price", "Location", "Size (sqm)", "Source", "Link"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.setColumnWidth(1, 120)
        self.setColumnWidth(2, 150)
        self.setColumnWidth(3, 100)
        self.setColumnWidth(4, 120)
        self.setColumnHidden(5, True)  # Hide link column

class RealEstateApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real Estate Scraper Pro")
        self.setGeometry(100, 100, 1280, 800)
        self.setWindowIcon(QIcon("icon.png"))

        # Initialize UI
        self.init_ui()
        self.load_stylesheet("dark")

        # State variables
        self.current_df = pd.DataFrame()
        self.dark_mode = True

    def init_ui(self):
        # Create main widgets
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Setup sidebar
        self.create_sidebar()

        # Main layout
        main_layout = QVBoxLayout(self.central_widget)

        # Control Panel
        control_panel = self.create_control_panel()
        main_layout.addLayout(control_panel)

        # Progress Bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        main_layout.addWidget(self.progress)

        # Results Table
        self.table = ModernTable()
        main_layout.addWidget(self.table)

        # Status Bar
        self.status_bar = self.statusBar()

        # Setup theme toggle
        self.theme_action = QAction("🌓 Toggle Theme", self)
        self.theme_action.triggered.connect(self.toggle_theme)
        self.addAction(self.theme_action)

    def create_sidebar(self):
        sidebar = QDockWidget("Navigation", self)
        sidebar.setFeatures(QDockWidget.NoDockWidgetFeatures)
        sidebar.setFixedWidth(200)

        scroll = QScrollArea()
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Add sidebar components
        sites = ["Jiji", "Realethio", "EthiopiaRealty", "Living Ethio"]
        self.page_inputs = {}

        for site in sites:
            frame = QFrame()
            frame.setFrameShape(QFrame.StyledPanel)
            flayout = QVBoxLayout(frame)

            label = QLabel(f"{site} Pages:")
            input_field = QLineEdit()
            input_field.setPlaceholderText("Pages")
            input_field.setMaximumWidth(80)

            flayout.addWidget(label)
            flayout.addWidget(input_field)
            layout.addWidget(frame)
            self.page_inputs[site.lower()] = input_field

        # Add export button
        self.export_btn = QPushButton("💾 Export Data")
        self.export_btn.clicked.connect(self.export_data)
        layout.addWidget(self.export_btn)

        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        sidebar.setWidget(scroll)
        self.addDockWidget(Qt.LeftDockWidgetArea, sidebar)

    def create_control_panel(self):
        control_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶ Start Scraping")
        self.start_btn.setFixedSize(120, 40)
        self.start_btn.clicked.connect(self.start_scraping)

        control_layout.addWidget(self.start_btn)
        control_layout.addStretch()
        return control_layout

    def load_stylesheet(self, theme):
        style = """
        QMainWindow {
            background-color: $bg_color;
        }
        QTableWidget {
            background: $table_bg;
            alternate-background-color: $alt_bg;
            gridline-color: $grid_color;
            border: 1px solid $border_color;
        }
        QHeaderView::section {
            background: $header_bg;
            color: $text_color;
            padding: 8px;
        }
        QProgressBar {
            background: $progress_bg;
            border-radius: 4px;
            height: 12px;
        }
        QProgressBar::chunk {
            background: $progress_chunk;
            border-radius: 4px;
        }
        """

        colors = {
            "dark": {
                "bg_color": "#2D2D2D",
                "text_color": "#FFFFFF",
                "table_bg": "#3A3A3A",
                "alt_bg": "#454545",
                "grid_color": "#505050",
                "border_color": "#606060",
                "header_bg": "#404040",
                "progress_bg": "#454545",
                "progress_chunk": "#4FC1E9"
            },
            "light": {
                "bg_color": "#F5F6FA",
                "text_color": "#2D2D2D",
                "table_bg": "#FFFFFF",
                "alt_bg": "#F8F9FA",
                "grid_color": "#E0E0E0",
                "border_color": "#D0D0D0",
                "header_bg": "#E9ECEF",
                "progress_bg": "#E9ECEF",
                "progress_chunk": "#4FC1E9"
            }
        }

        for k, v in colors[theme].items():
            style = style.replace(f"${k}", v)

        self.setStyleSheet(style)
        self.table.setStyleSheet(f"QTableWidget::item {{ color: {colors[theme]['text_color'] }; }}")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.load_stylesheet("dark" if self.dark_mode else "light")

    def start_scraping(self):
        try:
            pages = {
                'jiji': int(self.page_inputs['jiji'].text() or 0),
                'realethio': int(self.page_inputs['realethio'].text() or 0),
                'ethiopiarealty': int(self.page_inputs['ethiopiarealty'].text() or 0),
                'livingethio': int(self.page_inputs['living ethio'].text() or 0)
            }
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid page numbers")
            return

        self.start_btn.setEnabled(False)
        self.table.setRowCount(0)

        self.thread = ScraperThread(pages)
        self.thread.update_progress.connect(self.update_progress)
        self.thread.scraping_complete.connect(self.display_results)
        self.thread.error_occurred.connect(self.show_error)
        self.thread.start()

    def update_progress(self, value, message):
        self.progress.setValue(value)
        self.status_bar.showMessage(message)

    def display_results(self, df):
        self.start_btn.setEnabled(True)
        self.progress.setValue(0)

        if df.empty:
            QMessageBox.information(self, "Info", "No properties found")
            return

        self.current_df = df
        self.table.setRowCount(len(df))

        for row in range(len(df)):
            item = df.iloc[row]
            self.table.setItem(row, 0, QTableWidgetItem(str(item['Title'])))
            self.table.setItem(row, 1, QTableWidgetItem(str(item['Price'])))
            self.table.setItem(row, 2, QTableWidgetItem(str(item['Location'])))
            self.table.setItem(row, 3, QTableWidgetItem(str(item['Size (sqm)'])))
            self.table.setItem(row, 4, QTableWidgetItem(str(item['Source'])))
            link_item = QTableWidgetItem(str(item['Link']))
            link_item.setForeground(QBrush(QColor("#4FC1E9")))
            self.table.setItem(row, 5, link_item)

        self.status_bar.showMessage(f"Found {len(df)} properties", 5000)

    def show_error(self, message):
        self.start_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", message)

    def export_data(self):
        if self.current_df.empty:
            QMessageBox.warning(self, "Warning", "No data to export")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Data",
            "",
            "CSV (*.csv);;Excel (*.xlsx);;JSON (*.json)"
        )

        if filename:
            try:
                if filename.endswith('.csv'):
                    self.current_df.to_csv(filename, index=False)
                elif filename.endswith('.xlsx'):
                    self.current_df.to_excel(filename, index=False)
                elif filename.endswith('.json'):
                    self.current_df.to_json(filename, orient='records', indent=2)

                QMessageBox.information(self, "Success", f"Data saved to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    window = RealEstateApp()
    window.show()
    sys.exit(app.exec())

