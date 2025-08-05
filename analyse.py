import tkinter as tk
from tkinter import messagebox
import pandas as pd
import sqlite3

selected_tickers = []
ticker_vars = {}

def submit_selection():
    global selected_tickers
    selected_tickers = [ticker for ticker, var in ticker_vars.items() if var.get()]
    if selected_tickers:
        messagebox.showinfo("Selected", f"You selected {len(selected_tickers)} tickers.")
        root.destroy()
    else:
        messagebox.showwarning("No Selection", "Please select at least one ticker.")

def update_checkboxes(*args):
    search_text = search_var.get().strip().lower()
    
    for widget in checkbox_frame.winfo_children():
        widget.destroy()
        
    filtered = [t for t in tickers if search_text in t.lower()]
    
    for ticker in filtered:
        if ticker not in ticker_vars:
            ticker_vars[ticker] = tk.BooleanVar()
        tk.Checkbutton(checkbox_frame, text=ticker, variable=ticker_vars[ticker]).pack(anchor='w')

# Get tickers
tickers = sp_comp_tickers = pd.read_html(
    'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].to_list()

# Create GUI
root = tk.Tk()
root.title("Select S&P 500 Tickers")

# Search bar
search_var = tk.StringVar()
search_var.trace("w", update_checkboxes)

tk.Label(root, text="Search Ticker:").pack(pady=(10, 0))
tk.Entry(root, textvariable=search_var).pack(fill="x", padx=10)

# Scrollable canvas
canvas = tk.Canvas(root, height=400)
scroll_y = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
checkbox_frame = tk.Frame(canvas)

canvas_frame = canvas.create_window((0, 0), window=checkbox_frame, anchor='nw')
canvas.configure(yscrollcommand=scroll_y.set)
checkbox_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
scroll_y.pack(side="right", fill="y")

# Initialize checkboxes
update_checkboxes()

# Submit button
tk.Button(root, text="Submit", command=submit_selection).pack(pady=10)

root.mainloop()

# After GUI closes
print("Selected tickers:", selected_tickers)

# Query
query = f"""
    SELECT * 
    FROM price
    WHERE ticker IN {tuple(selected_tickers)}
"""
conn = sqlite3.connect('sp500_stocks.db')
cursor = conn.cursor()
cursor.execute(query)
results = cursor.fetchall()
results_df = pd.DataFrame(results, columns=['Ticker', 'Date', 'Close', 'High', 'Low', 'Open', 'Volume'])
print(results_df.head())