import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import webbrowser
from fpdf import FPDF
from datetime import datetime
import threading
import queue
import os
import re
from collections import OrderedDict

class WebScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Web Scraper")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
        
        # Configure styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#f5f5f5')
        self.style.configure('TLabel', background='#f5f5f5', font=('Segoe UI', 10))
        self.style.configure('TButton', font=('Segoe UI', 10), padding=5)
        self.style.configure('TEntry', font=('Segoe UI', 10), padding=5)
        self.style.configure('TRadiobutton', background='#f5f5f5', font=('Segoe UI', 10))
        self.style.map('TButton', 
                      foreground=[('active', 'black'), ('!active', 'black')],
                      background=[('active', '#e1e1e1'), ('!active', '#f0f0f0')])
        
        # Queue for thread-safe GUI updates
        self.queue = queue.Queue()
        
        # Dictionary to store URLs and their scraped data
        self.url_data = OrderedDict()
        
        # Create widgets
        self.create_widgets()
        
        # Check queue periodically
        self.root.after(100, self.process_queue)
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header frame
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Logo/Title
        ttk.Label(header_frame, text="Multi-URL Web Scraper", font=('Segoe UI', 16, 'bold')).pack(side=tk.LEFT)
        
        # URL Management frame
        url_management_frame = ttk.Frame(main_frame)
        url_management_frame.pack(fill=tk.X, pady=5)
        
        # URL Entry frame
        url_frame = ttk.Frame(url_management_frame)
        url_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        ttk.Label(url_frame, text="Website URL:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.url_entry.insert(0, "https://example.com")
        
        # URL List buttons frame
        url_buttons_frame = ttk.Frame(url_management_frame)
        url_buttons_frame.pack(side=tk.RIGHT)
        
        ttk.Button(
            url_buttons_frame, 
            text="+ Add URL", 
            command=self.add_url,
            style='TButton'
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            url_buttons_frame, 
            text="Clear All", 
            command=self.clear_urls,
            style='TButton'
        ).pack(side=tk.LEFT, padx=2)
        
        # URL List display
        self.url_list_frame = ttk.Frame(main_frame)
        self.url_list_frame.pack(fill=tk.X, pady=5)
        
        self.url_listbox = tk.Listbox(
            self.url_list_frame,
            height=4,
            selectmode=tk.MULTIPLE,
            font=('Consolas', 9),
            bg='white',
            relief=tk.SUNKEN
        )
        self.url_listbox.pack(fill=tk.X, expand=True)
        
        # Scraping Options frame
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(options_frame, text="Scrape Content:").pack(side=tk.LEFT)
        self.scrape_type = tk.StringVar(value="text")
        
        options = [
            ("Text Content", "text"),
            ("All Links", "links"),
            ("Images", "images"),
            ("Headings", "headings"),
            ("Tables", "tables")
        ]
        
        for text, mode in options:
            ttk.Radiobutton(
                options_frame, 
                text=text, 
                variable=self.scrape_type, 
                value=mode
            ).pack(side=tk.LEFT, padx=5)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        buttons = [
            ("Fetch Selected", self.fetch_selected_urls, '#4CAF50'),
            ("Fetch All", self.fetch_all_urls, '#4CAF50'),
            ("Clear Results", self.clear_results, '#f44336'),
            ("Open Selected", self.open_selected_in_browser, '#2196F3'),
            ("Export to TXT", self.export_to_txt, '#607D8B'),
            ("Export to PDF", self.export_to_pdf, '#9C27B0')
        ]
        
        for text, command, color in buttons:
            btn = ttk.Button(
                button_frame, 
                text=text, 
                command=command,
                style='TButton'
            )
            btn.pack(side=tk.LEFT, padx=2)
            btn.configure(style='TButton')
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)
        
        # Results Display
        results_frame = ttk.Frame(main_frame)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(results_frame, text="Scraped Results:", font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W)
        
        # Create a Notebook for multiple tabs
        self.notebook = ttk.Notebook(results_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Main results tab
        self.results_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.results_tab, text="Results")
        
        self.results_text = scrolledtext.ScrolledText(
            self.results_tab, 
            wrap=tk.WORD, 
            font=('Consolas', 10),
            padx=10,
            pady=10
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        ttk.Label(
            main_frame, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN,
            padding=5,
            font=('Segoe UI', 9)
        ).pack(fill=tk.X, pady=(5,0))
    
    def process_queue(self):
        """Process messages from the queue (for thread-safe GUI updates)"""
        try:
            while True:
                func, args = self.queue.get_nowait()
                func(*args)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)
    
    def add_url(self):
        """Add a URL to the list of URLs to scrape"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        if url in self.url_data:
            messagebox.showwarning("Warning", "This URL is already in the list")
            return
        
        self.url_data[url] = None  # Initialize with no data
        self.update_url_listbox()
        self.url_entry.delete(0, tk.END)
    
    def clear_urls(self):
        """Clear all URLs from the list"""
        self.url_data.clear()
        self.update_url_listbox()
        self.clear_results()
    
    def update_url_listbox(self):
        """Update the URL listbox display"""
        self.url_listbox.delete(0, tk.END)
        for url in self.url_data:
            status = "✓" if self.url_data[url] is not None else " "
            self.url_listbox.insert(tk.END, f"{status} {url}")
    
    def clear_results(self):
        """Clear the results display"""
        self.results_text.delete(1.0, tk.END)
        self.status_var.set("Ready")
    
    def clear_results_display(self):
        """Thread-safe clear results"""
        self.results_text.delete(1.0, tk.END)
    
    def fetch_selected_urls(self):
        """Fetch data from selected URLs"""
        selected_indices = self.url_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select URLs to fetch")
            return
        
        urls = [list(self.url_data.keys())[i] for i in selected_indices]
        self._fetch_urls(urls)
    
    def fetch_all_urls(self):
        """Fetch data from all URLs"""
        if not self.url_data:
            messagebox.showwarning("Warning", "No URLs to fetch")
            return
        
        self._fetch_urls(list(self.url_data.keys()))
    
    def _fetch_urls(self, urls):
        """Fetch data from multiple URLs"""
        self.toggle_buttons(False)
        self.progress['value'] = 0
        self.status_var.set(f"Fetching data from {len(urls)} URLs...")
        
        # Start fetch in a separate thread
        threading.Thread(
            target=self._fetch_urls_thread, 
            args=(urls,),
            daemon=True
        ).start()
    
    def _fetch_urls_thread(self, urls):
        """Thread function to fetch multiple URLs"""
        try:
            total_urls = len(urls)
            for i, url in enumerate(urls):
                try:
                    self.queue.put((self.update_status, (f"Fetching {i+1}/{total_urls}: {url}",)))
                    self.queue.put((self.update_progress, (i/total_urls*100,)))
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    scrape_type = self.scrape_type.get()
                    
                    if scrape_type == "text":
                        result = self.scrape_text_content(soup)
                    elif scrape_type == "links":
                        result = self.scrape_links(soup, url)
                    elif scrape_type == "images":
                        result = self.scrape_images(soup, url)
                    elif scrape_type == "headings":
                        result = self.scrape_headings(soup)
                    elif scrape_type == "tables":
                        result = self.scrape_tables(soup)
                    else:
                        result = "Invalid scrape type"
                    
                    self.url_data[url] = result
                    self.queue.put((self.update_url_listbox, ()))
                    
                except Exception as e:
                    self.url_data[url] = f"Error fetching {url}: {str(e)}"
                    self.queue.put((self.update_url_listbox, ()))
                    continue
            
            # Combine all results for display
            combined_result = []
            for url, data in self.url_data.items():
                if data:
                    combined_result.append(f"\n=== Results from {url} ===\n")
                    combined_result.append(data)
                    combined_result.append("\n" + "="*50 + "\n")
            
            self.queue.put((self.update_results, ("\n".join(combined_result),)))
            self.queue.put((self.update_status, (f"Successfully fetched data from {len(urls)} URLs",)))
            
        except Exception as e:
            self.queue.put((self.show_error, (f"Failed to fetch data: {str(e)}",)))
        finally:
            self.queue.put((self.toggle_buttons, (True,)))
            self.queue.put((self.update_progress, (100,)))
    
    def scrape_text_content(self, soup):
        """Scrape all text content from paragraphs and headings"""
        paragraphs = [p.get_text().strip() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        paragraphs = [p for p in paragraphs if p]  # Remove empty strings
        return "\n\n".join(paragraphs)
    
    def scrape_links(self, soup, base_url):
        """Scrape all links from the page"""
        links = []
        for a in soup.find_all('a', href=True):
            link = a['href']
            if not link.startswith(('http://', 'https://')):
                link = urljoin(base_url, link)
            link_text = a.get_text().strip()
            links.append(f"{link} ({link_text})" if link_text else link)
        return "\n".join(links)
    
    def scrape_images(self, soup, base_url):
        """Scrape all images from the page"""
        images = []
        for img in soup.find_all('img', src=True):
            img_url = img['src']
            if not img_url.startswith(('http://', 'https://')):
                img_url = urljoin(base_url, img_url)
            alt_text = img.get('alt', 'No alt text')
            images.append(f"{img_url} (Alt: {alt_text})")
        return "\n".join(images)
    
    def scrape_headings(self, soup):
        """Scrape all headings from the page"""
        headings = []
        for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in soup.find_all(level):
                text = heading.get_text().strip()
                if text:
                    headings.append(f"{level.upper()}: {text}")
        return "\n".join(headings)
    
    def scrape_tables(self, soup):
        """Scrape all tables from the page"""
        tables = []
        for i, table in enumerate(soup.find_all('table'), 1):
            tables.append(f"\n=== TABLE {i} ===\n")
            for row in table.find_all('tr'):
                cells = [cell.get_text().strip() for cell in row.find_all(['td', 'th'])]
                tables.append(" | ".join(cells))
            tables.append("\n")
        return "\n".join(tables)
    
    def open_selected_in_browser(self):
        """Open selected URLs in default browser"""
        selected_indices = self.url_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select URLs to open")
            return
        
        urls = [list(self.url_data.keys())[i] for i in selected_indices]
        for url in urls:
            try:
                webbrowser.open(url)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open {url}: {str(e)}")
        
        self.status_var.set(f"Opened {len(urls)} URLs in browser")
    
    def export_to_txt(self):
        """Export all results to a single text file"""
        if not any(self.url_data.values()):
            messagebox.showwarning("Warning", "No data to export")
            return
        
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save All Results as Text File"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for url, data in self.url_data.items():
                        if data:
                            f.write(f"\n=== Results from {url} ===\n\n")
                            f.write(data)
                            f.write("\n" + "="*50 + "\n")
                
                messagebox.showinfo("Success", f"All content exported to {file_path}")
                self.status_var.set(f"Exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def export_to_pdf(self):
        """Export all results to a single PDF file"""
        if not any(self.url_data.values()):
            messagebox.showwarning("Warning", "No data to export")
            return
        
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                title="Save All Results as PDF File"
            )
            
            if not file_path:
                return

            # Create PDF with Unicode support
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)

            # Configure fonts with multiple fallback options
            font_configured = False
            font_family = "Arial"  # Default fallback
            
            # Try to use DejaVu fonts if available
            try:
                pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
                pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
                pdf.add_font('DejaVu', 'I', 'DejaVuSans-Oblique.ttf', uni=True)
                font_family = 'DejaVu'
                font_configured = True
            except:
                messagebox.showwarning("Font Warning", 
                    "DejaVu fonts not found. Using Arial which may not support all characters.")

            # Add cover page
            pdf.add_page()
            pdf.set_font(font_family, 'B', 20)
            pdf.cell(0, 40, "Web Scraping Report", 0, 1, 'C')
            pdf.ln(20)
            
            pdf.set_font(font_family, '', 14)
            pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
            pdf.ln(10)
            
            pdf.set_font(font_family, 'B', 16)
            pdf.cell(0, 10, "Scraped URLs:", 0, 1)
            pdf.set_font(font_family, '', 12)
            
            for url in self.url_data:
                pdf.cell(0, 10, f"- {url}", 0, 1)
            
            # Add content for each URL
            for url, data in self.url_data.items():
                if data:
                    pdf.add_page()
                    pdf.set_font(font_family, 'B', 16)
                    pdf.cell(0, 10, f"Results from: {url}", 0, 1)
                    pdf.ln(10)
                    
                    pdf.set_font(font_family, '', 12)
                    
                    # Clean content and handle special characters
                    cleaned_content = self.clean_special_chars(data)
                    
                    # Split content into lines and add to PDF
                    for line in cleaned_content.split('\n'):
                        line = line.strip()
                        if line:
                            try:
                                if (line.upper() == line and len(line) < 50) or line.endswith(':'):
                                    pdf.set_font(font_family, 'B', 12)
                                    pdf.cell(0, 10, line, 0, 1)
                                    pdf.set_font(font_family, '', 12)
                                elif line.startswith(('http://', 'https://')):
                                    pdf.set_text_color(0, 0, 255)
                                    pdf.cell(0, 10, line, 0, 1, link=line)
                                    pdf.set_text_color(0, 0, 0)
                                else:
                                    pdf.multi_cell(0, 10, line)
                                pdf.ln(2)
                            except:
                                # If any error occurs with this line, try ASCII fallback
                                safe_line = line.encode('ascii', 'ignore').decode('ascii')
                                pdf.multi_cell(0, 10, safe_line)
                                pdf.ln(2)
            
            # Save PDF
            pdf.output(file_path)
            messagebox.showinfo("Success", f"All results exported to {file_path}")
            self.status_var.set(f"PDF exported to {file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")

    def clean_special_chars(self, text):
        """Replace problematic Unicode characters with ASCII equivalents"""
        replacements = {
            '\u2018': "'", '\u2019': "'",  # Curly single quotes
            '\u201C': '"', '\u201D': '"',   # Curly double quotes
            '\u2013': '-', '\u2014': '--',  # En/em dashes
            '\u2026': '...',                # Ellipsis
            '\u00A0': ' ',                  # Non-breaking space
            '\u00B0': '°',                  # Degree symbol
            '\u20AC': 'EUR',                # Euro symbol
            '\u00A3': 'GBP',                # Pound symbol
            '\u00A5': 'JPY',                # Yen symbol
            '\u00A9': '(c)',                # Copyright
            '\u00AE': '(R)',                # Registered trademark
        }
        for uni_char, replacement in replacements.items():
            text = text.replace(uni_char, replacement)
        return text
    
    def toggle_buttons(self, state):
        """Enable/disable all buttons"""
        for child in self.root.winfo_children():
            if isinstance(child, ttk.Button):
                child.state(['!disabled' if state else 'disabled'])
    
    def update_progress(self, value):
        """Update progress bar"""
        self.progress['value'] = value
    
    def update_results(self, content):
        """Update results display"""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, content)
    
    def update_status(self, message):
        """Update status bar"""
        self.status_var.set(message)
    
    def show_error(self, message):
        """Show error message"""
        messagebox.showerror("Error", message)
        self.status_var.set("Error occurred")

if __name__ == "__main__":
    root = tk.Tk()
    
    # Set window icon
    try:
        root.iconbitmap('scraper_icon.ico')
    except:
        pass
    
    app = WebScraperApp(root)
    
    # Center the window
    window_width = 1000
    window_height = 800
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2)
    center_y = int(screen_height/2 - window_height/2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    
    root.mainloop()