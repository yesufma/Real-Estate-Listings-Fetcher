#!/usr/bin/env python
# coding: utf-8

# In[1]:


# hello world update

# In[2]:


import sys
import re
import requests
import warnings
import time
import os
import pandas as pd
import webbrowser
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import ctypes
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# ========================
# UTILITY FUNCTIONS
# ========================
def clean_text(text):
    """Clean text from encoding artifacts and extra spaces"""
    if pd.isna(text) or not isinstance(text, str):
        return text
    cleaned = re.sub(r'[Â©ª«¬®°±²³µ¶·¸¹º»¼½¾¿]', '', text)
    return re.sub(r'\s+', ' ', cleaned).strip()

def clean_numeric(value):
    """Extract and clean numeric values from text"""
    if pd.isna(value) or not isinstance(value, str):
        return value
    return re.sub(r'[^\d,]', '', value)

def format_price(price):
    """Format price with commas as thousand separators"""
    try:
        price_str = str(price)
        if price_str.replace(',', '').isdigit():
            return "{:,}".format(int(price_str.replace(',', '')))
        return price_str
    except Exception:
        return price

def safe_convert_to_float(value):
    """Safely convert string to float, handling commas and empty values"""
    try:
        if isinstance(value, str):
            value = value.replace(',', '')
        return float(value) if value else 0.0
    except (ValueError, TypeError):
        return 0.0

# ========================
# SCRAPING FUNCTIONS
# ========================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

def scrape_jiji(max_pages):
    data = []
    base_url = "https://jiji.com.et/api_web/v1/listing"
    
    for page in range(1, max_pages + 1):
        try:
            response = requests.get(
                base_url,
                params={
                    "slug": "houses-apartments-for-sale",
                    "webp": "true",
                    "filter_attr_188_property_type": "House",
                    "page": page
                },
                headers=HEADERS,
                timeout=10
            )
            json_data = response.json()
            
            for listing in json_data.get("adverts_list", {}).get("adverts", []):
                size_value = next((attr["value"] for attr in listing.get("attrs", []) 
                                if attr.get("name") == "Property size"), "0")
                price = clean_numeric(str(listing.get("price_obj", {}).get("value", "N/A")))
                entry = {
                    "Title": clean_text(listing.get("title", "N/A")),
                    "Price": f"ETB {format_price(price)}",
                    "Location": clean_text(listing.get("region_name", "N/A")),
                    "Size (sqm)": safe_convert_to_float(clean_numeric(size_value)),
                    "Link": f"https://jiji.com.et{listing.get('url', '')}",
                    "Source": "Jiji"
                }
                data.append(entry)
        except Exception:
            continue
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by=["Location", "Size (sqm)"])
    return df

def scrape_realethio(max_pages):
    data = []
    base_url = "https://realethio.com/property-type/house-for-sale/"
    
    for page in range(1, max_pages + 1):
        try:
            page_url = f"{base_url}page/{page}/" if page > 1 else base_url
            response = requests.get(page_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            property_cards = soup.select(".item-listing-wrap")

            for card in property_cards:
                try:
                    size_element = card.select_one("li:contains('m²')")
                    size_text = size_element.text.split('m²')[0] if size_element else "0"
                    price = clean_numeric(card.select_one(".item-price").text.replace('ETB', ''))
                    entry = {
                        "Title": clean_text(card.select_one(".item-title").text),
                        "Price": f"ETB {format_price(price)}",
                        "Location": clean_text(card.select_one(".item-address").text),
                        "Size (sqm)": safe_convert_to_float(clean_numeric(size_text)),
                        "Link": card.select_one(".item-title a")['href'],
                        "Source": "Realethio"
                    }
                    data.append(entry)
                except Exception:
                    continue
        except Exception:
            continue
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by="Size (sqm)")
    return df

def scrape_ethiopiarealty(max_pages):
    data = []
    BASE_URL = "https://ethiopiarealty.com"
    
    try:
        main_page = requests.get(f"{BASE_URL}/building-for-sale/", headers=HEADERS)
        soup = BeautifulSoup(main_page.content, 'html.parser')
        page_links = [urljoin(BASE_URL, a['href']) 
                     for a in soup.select('.pagination a.page-link') 
                     if 'href' in a.attrs][:max_pages] or [f"{BASE_URL}/building-for-sale/"]
    except Exception:
        page_links = [f"{BASE_URL}/building-for-sale/"]

    for page_url in page_links:
        try:
            soup = BeautifulSoup(requests.get(page_url, headers=HEADERS).content, 'html.parser')
            for listing in soup.select('div.d-flex.align-items-center.h-100'):
                try:
                    size_element = listing.select_one(".hz-figure")
                    size_text = size_element.text if size_element else "0"
                    price = clean_numeric(listing.select_one(".item-price").text)
                    entry = {
                        "Title": clean_text(listing.select_one(".item-title").text),
                        "Price": f"ETB {format_price(price)}",
                        "Location": clean_text(listing.select_one(".item-address").text.replace(" ,", ",")),
                        "Size (sqm)": safe_convert_to_float(clean_numeric(size_text)),
                        "Link": listing.select_one(".item-title a")['href'],
                        "Source": "EthiopiaRealty"
                    }
                    data.append(entry)
                except Exception:
                    continue
        except Exception:
            continue

    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by="Size (sqm)")
    return df

def scrape_livingethio(max_pages):
    data = []
    base_url = "https://18.223.203.43.nip.io/api/properties/findByCategoryPagination/house-for-sale"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://livingethio.com/"
    }

    page = 1
    total_pages = 1

    while page <= min(total_pages, max_pages):
        try:
            response = requests.get(
                base_url,
                params={"page": page, "limit": 100},
                headers=headers,
                verify=False,
                timeout=15
            )

            if response.status_code != 200:
                print(f"Stopped at page {page}. Status code: {response.status_code}")
                break

            json_data = response.json()
            total_pages = json_data.get('totalPages', 1)
            records = json_data.get('records', [])
            
            if not records:
                break

            for prop in records:
                if not prop.get('area'):
                    continue
                
                price_value = prop.get('price', 'N/A')
                if price_value != 'N/A':
                    cleaned_price = clean_numeric(str(price_value))
                    formatted_price = format_price(cleaned_price)
                else:
                    formatted_price = 'N/A'
                
                entry = {
                    "Title": clean_text(prop.get('title', 'N/A')),
                    "Price": f"Br. {formatted_price}",
                    "Location": clean_text(prop.get('location', {}).get('name', 'N/A')),
                    "Size (sqm)": safe_convert_to_float(prop.get('area', 0)),
                    "Link": f"https://livingethio.com/site/property-details/{prop.get('id', '')}",
                    "Source": "Living Ethio"
                }
                data.append(entry)
            
            page += 1
            time.sleep(1)  # Respectful delay

        except Exception as e:
            print(f"Error occurred: {str(e)}")
            break

    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by=['Location', 'Size (sqm)'])
    return df

# ========================
# PY_SIDE6 GUI APPLICATION
# ========================
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QTableWidget, QTableWidgetItem,
                               QDockWidget, QProgressBar, QPushButton, QLineEdit, QLabel,
                               QFileDialog, QMessageBox, QStyleFactory, QVBoxLayout,
                               QHBoxLayout, QFrame, QHeaderView)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QBrush, QColor

# QThread subclass for background scraping
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
            
            # Iterate over each site. The keys here should match the scraper function names.
            for site, pages in self.sites_pages.items():
                if pages > 0:
                    try:
                        scraper_func = globals().get(f"scrape_{site}")
                        if scraper_func is None:
                            self.error_occurred.emit(f"No scraper found for {site}")
                            continue
                        df = scraper_func(pages)
                        if not df.empty:
                            all_data.append(df)
                        completed += 1
                        self.update_progress.emit(int((completed/total)*100), f"Scraping {site}...")
                    except Exception as e:
                        self.error_occurred.emit(f"{site} error: {str(e)}")
            
            if all_data:
                final_df = pd.concat(all_data).reset_index(drop=True)
                self.scraping_complete.emit(final_df)
            else:
                self.scraping_complete.emit(pd.DataFrame())
        except Exception as e:
            self.error_occurred.emit(f"Thread error: {str(e)}")

class RealEstateApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real Estate Scraper Pro")
        self.setGeometry(100, 100, 1280, 800)
        icon_path = "icon.png"  # Adjust icon path if needed.
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.current_df = pd.DataFrame()
        self.init_ui()

    def init_ui(self):
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Control panel with Start button
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ Start Scraping")
        self.start_btn.clicked.connect(self.start_scraping)
        control_layout.addWidget(self.start_btn)
        layout.addLayout(control_layout)

        # Progress bar
        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        # Table to display results (including link column)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Title", "Price", "Location", "Size (sqm)", "Source", "Link"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.table.cellClicked.connect(self.handle_cell_click)

        # Sidebar for site settings
        sidebar = QDockWidget("Settings", self)
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)

        sites = ["Jiji", "Realethio", "EthiopiaRealty", "Living Ethio"]
        self.page_inputs = {}
        for site in sites:
            frame = QFrame()
            frame_layout = QVBoxLayout(frame)
            label = QLabel(f"{site} Pages:")
            entry = QLineEdit()
            entry.setPlaceholderText("Pages")
            frame_layout.addWidget(label)
            frame_layout.addWidget(entry)
            sidebar_layout.addWidget(frame)
            # Store key in lowercase with no spaces
            self.page_inputs[site.lower().replace(" ", "")] = entry

        self.export_btn = QPushButton("💾 Export Data")
        self.export_btn.clicked.connect(self.export_data)
        sidebar_layout.addWidget(self.export_btn)
        sidebar.setWidget(sidebar_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, sidebar)

    def start_scraping(self):
        try:
            pages = {
                'jiji': int(self.page_inputs['jiji'].text() or 0),
                'realethio': int(self.page_inputs['realethio'].text() or 0),
                'ethiopiarealty': int(self.page_inputs['ethiopiarealty'].text() or 0),
                'livingethio': int(self.page_inputs['livingethio'].text() or 0)
            }
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter valid page numbers")
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
        self.statusBar().showMessage(message)

    def display_results(self, df):
        self.start_btn.setEnabled(True)
        self.progress.setValue(0)
        
        if df.empty:
            QMessageBox.information(self, "Info", "No properties found")
            return
            
        self.current_df = df
        self.table.setRowCount(len(df))
        
        for row_idx, row in df.iterrows():
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(row.get('Title', ''))))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(row.get('Price', ''))))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(row.get('Location', ''))))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(row.get('Size (sqm)', ''))))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(row.get('Source', ''))))
            # Create a cell with "Go to" text; store the actual URL in the cell's user data.
            link_item = QTableWidgetItem("Go to")
            link_item.setData(Qt.UserRole, row.get('Link', ''))
            link_item.setForeground(QBrush(QColor("white")))
            self.table.setItem(row_idx, 5, link_item)

    def handle_cell_click(self, row, column):
        # If the "Link" column (index 5) is clicked, open the URL.
        if column == 5:
            item = self.table.item(row, column)
            if item:
                url = item.data(Qt.UserRole)
                if url:
                    webbrowser.open(url)

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
    # Set the application-wide icon
    icon_path = "icon.png"
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = RealEstateApp()
    window.show()
    sys.exit(app.exec())


# In[ ]:



