import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText
import yfinance as yf
import pandas as pd
import json
import os
import threading
import time
from datetime import datetime

# Constants
JSON_FILE = 'stocks.json'
DEFAULT_STOCKS = ["AAPL", "MSFT", "NVDA", "TSLA"]
UPDATE_INTERVAL = 60  # in seconds

class StockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Tracker")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        self.stocks = self.load_stocks()
        self.is_running = False  # To control the start and stop of updates
        self.create_gui()
        self.populate_initial_stocks()

    def load_stocks(self):
        """Load stocks from JSON file or create default."""
        if not os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'w') as f:
                json.dump(DEFAULT_STOCKS, f)
            return DEFAULT_STOCKS.copy()
        try:
            with open(JSON_FILE, 'r') as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON file must contain a list of stock symbols.")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            messagebox.showerror("Error", f"Failed to load JSON file: {e}")
            with open(JSON_FILE, 'w') as f:
                json.dump(DEFAULT_STOCKS, f)
            return DEFAULT_STOCKS.copy()

    def save_stocks(self):
        """Save the current stock list to JSON file."""
        try:
            with open(JSON_FILE, 'w') as f:
                json.dump(self.stocks, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save JSON file: {e}")

    def create_gui(self):
        """Set up the GUI components."""
        # Style configuration
        style = ttk.Style()
        style.theme_use("clam")  # You can choose other themes like 'default', 'classic', etc.
        style.configure("Treeview",
                        background="#f0f0f0",
                        foreground="black",
                        rowheight=25,
                        fieldbackground="#f0f0f0")
        style.map('Treeview', background=[('selected', '#347083')])

        # Main Frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview Frame
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Create Treeview
        columns = ("Symbol", "Price", "Signal", "OSMA", "Action")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=10)
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "Action":
                self.tree.column(col, width=100, anchor='center')
            else:
                self.tree.column(col, width=120, anchor='center')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add a scrollbar to the Treeview
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons Frame
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.pack(side=tk.TOP, fill=tk.X)

        add_button = ttk.Button(button_frame, text="Add Stock", command=self.add_stock)
        add_button.pack(side=tk.LEFT, padx=5)

        remove_button = ttk.Button(button_frame, text="Remove Selected", command=self.remove_stock)
        remove_button.pack(side=tk.LEFT, padx=5)

        start_button = ttk.Button(button_frame, text="Start", command=self.start_updates)
        start_button.pack(side=tk.LEFT, padx=5)

        stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_updates)
        stop_button.pack(side=tk.LEFT, padx=5)

        # Log Frame
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, pady=(10,0))

        log_label = ttk.Label(log_frame, text="Action Log:", font=('Helvetica', 10, 'bold'))
        log_label.pack(anchor='w')

        self.log_text = ScrolledText(log_frame, height=10, state='disabled', background="#e8e8e8")
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def populate_initial_stocks(self):
        """Insert initial stocks into the Treeview with default values."""
        for symbol in self.stocks:
            self.tree.insert("", tk.END, values=(symbol, "Loading...", "Loading...", "Loading...", ""))

    def add_stock(self):
        """Add a new stock symbol."""
        symbol = simpledialog.askstring("Add Stock", "Enter stock symbol (e.g., GOOG):")
        if symbol:
            symbol = symbol.strip().upper()
            if symbol in self.stocks:
                messagebox.showinfo("Info", f"{symbol} is already being tracked.")
                return
            # Validate the symbol
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if 'regularMarketPrice' not in info or info['regularMarketPrice'] is None:
                    raise ValueError("Invalid stock symbol.")
                self.stocks.append(symbol)
                self.save_stocks()
                self.tree.insert("", tk.END, values=(symbol, "Loading...", "Loading...", "Loading...", ""))
                self.log_action(f"Added stock {symbol}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add stock {symbol}: {e}")

    def remove_stock(self):
        """Remove selected stock(s)."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No stock selected.")
            return
        for item in selected_items:
            symbol = self.tree.item(item, 'values')[0]
            self.stocks.remove(symbol)
            self.tree.delete(item)
            self.log_action(f"Removed stock {symbol}")
        self.save_stocks()

    def start_updates(self):
        """Start the periodic data updates."""
        if not self.is_running:
            self.is_running = True
            self.log_action("Started data updates.")
            self.update_data()

    def stop_updates(self):
        """Stop the periodic data updates."""
        if self.is_running:
            self.is_running = False
            self.log_action("Stopped data updates.")

    def update_data(self):
        """Fetch and update stock data."""
        def task():
            while self.is_running:
                for item in self.tree.get_children():
                    symbol = self.tree.item(item, 'values')[0]
                    try:
                        ticker = yf.Ticker(symbol)
                        # Fetch historical data for indicators
                        hist = ticker.history(period="1d", interval="1m")
                        if hist.empty:
                            raise ValueError("No historical data available.")
                        # Compute MACD
                        macd, signal, osma = self.compute_macd(hist)
                        # Get current price
                        current_price = hist['Close'][-1]
                        # Determine buy/sell signals
                        if len(osma) < 2 or len(signal) < 2:
                            action = ""
                        else:
                            if osma.iloc[-1] > signal.iloc[-1] and osma.iloc[-2] <= signal.iloc[-2]:
                                action = "BUY"
                                self.log_action(f"BUY signal for {symbol} at ${current_price:.2f}")
                            elif osma.iloc[-1] < signal.iloc[-1] and osma.iloc[-2] >= signal.iloc[-2]:
                                action = "SELL"
                                self.log_action(f"SELL signal for {symbol} at ${current_price:.2f}")
                            else:
                                action = ""
                        # Update the treeview
                        self.root.after(0, lambda item=item, symbol=symbol, price=current_price,
                                       sig=signal.iloc[-1], osma_val=osma.iloc[-1], action=action:
                                       self.tree.item(item, values=(
                                           symbol,
                                           f"{price:.2f}",
                                           f"{sig:.4f}",
                                           f"{osma_val:.4f}",
                                           action
                                       )))
                    except Exception as e:
                        self.root.after(0, lambda item=item: self.tree.item(item, values=(self.tree.item(item, 'values')[0], "Error", "Error", "Error", "")))
                        self.log_action(f"Error updating {symbol}: {e}")
                # Wait for the next update
                for _ in range(UPDATE_INTERVAL):
                    if not self.is_running:
                        break
                    time.sleep(1)
        threading.Thread(target=task, daemon=True).start()

    def compute_macd(self, hist):
        """Compute MACD, Signal, and OSMA."""
        close = hist['Close']
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        osma = macd - signal
        return macd, signal, osma

    def log_action(self, message):
        """Log an action with timestamp in the log window."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, log_message)
        self.log_text.configure(state='disabled')
        self.log_text.see(tk.END)  # Auto-scroll to the end

def main():
    root = tk.Tk()
    app = StockApp(root)
    app.start_updates()
    root.mainloop()

if __name__ == "__main__":
    main()
