import tkinter as tk
from tkinter import messagebox
from tkcalendar import DateEntry
import pandas as pd
import sqlite3
from pypfopt import expected_returns, risk_models, EfficientFrontier

def ticker_selection_window(tickers):
    selected_tickers = []
    ticker_vars = {}
    root = tk.Tk()
    root.title("Select S&P 500 Tickers")

    search_var = tk.StringVar()
    search_var.trace("w", lambda *args: update_checkboxes(search_var, checkbox_frame, tickers, ticker_vars))

    tk.Label(root, text="Search Ticker:").pack(pady=(10, 0))
    tk.Entry(root, textvariable=search_var).pack(fill="x", padx=10)

    select_all_var = tk.BooleanVar()

    def toggle_select_all():
        for var in ticker_vars.values():
            var.set(select_all_var.get())

    tk.Checkbutton(root, text="Select All", variable=select_all_var,
                   command=toggle_select_all).pack(anchor="w", padx=10, pady=(5, 0))

    canvas = tk.Canvas(root, height=400)
    scroll_y = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    checkbox_frame = tk.Frame(canvas)

    canvas_frame = canvas.create_window((0, 0), window=checkbox_frame, anchor='nw')
    canvas.configure(yscrollcommand=scroll_y.set)
    checkbox_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    scroll_y.pack(side="right", fill="y")

    update_checkboxes(search_var, checkbox_frame, tickers, ticker_vars)

    def submit_selection():
        nonlocal selected_tickers
        selected_tickers = [ticker for ticker, var in ticker_vars.items() if var.get()]
        if selected_tickers:
            root.destroy()
        else:
            messagebox.showwarning("No Selection", "Please select at least one ticker.")

    tk.Button(root, text="Submit", command=submit_selection).pack(pady=10)
    root.mainloop()

    return selected_tickers

def update_checkboxes(search_var, checkbox_frame, tickers, ticker_vars):
    search_text = search_var.get().strip().lower()
    for widget in checkbox_frame.winfo_children():
        widget.destroy()
    filtered = [t for t in tickers if search_text in t.lower()]
    for ticker in filtered:
        if ticker not in ticker_vars:
            ticker_vars[ticker] = tk.BooleanVar()
        tk.Checkbutton(checkbox_frame, text=ticker, variable=ticker_vars[ticker]).pack(anchor='w')

def allocation_window(tickers):
    allocations = {}
    allocation_root = tk.Tk()
    allocation_root.title("Portfolio Allocation & Time Period")

    tk.Label(allocation_root,
             text="Enter allocation % for each asset (total must not exceed 100%)",
             font=("Arial", 12)).pack(pady=10)

    frame = tk.Frame(allocation_root)
    frame.pack(padx=10, pady=10)

    canvas = tk.Canvas(allocation_root, height=300)  # Limit height for scrolling
    scroll_y = tk.Scrollbar(allocation_root, orient="vertical", command=canvas.yview)
    frame = tk.Frame(canvas)

    canvas_frame = canvas.create_window((0, 0), window=frame, anchor='nw')
    canvas.configure(yscrollcommand=scroll_y.set)
    frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    canvas.pack(side="left", fill="both", expand=True, padx=10)
    scroll_y.pack(side="right", fill="y")

    allocation_vars = {}
    last_changed_var = tk.DoubleVar()

    def validate_total():
        total = sum(var.get() for var in allocation_vars.values())
        if total > 100:
            messagebox.showerror("Allocation Error",
                                 f"Total allocation exceeds 100% (currently {total:.2f}%).")
            last_changed_var.set(0.0)
        elif total < 100:
            remaining_label.config(text=f"Remaining: {100 - total:.2f}%")
        else:
            remaining_label.config(text="✅ Total = 100%")

    def make_callback(var):
        def callback(*args):
            nonlocal last_changed_var
            last_changed_var = var
            validate_total()
        return callback

    base_alloc = 100 / len(tickers)
    allocations_list = [base_alloc] * len(tickers)
    allocations_list[-1] = 100 - sum(allocations_list[:-1])

    for i, ticker in enumerate(tickers):
        tk.Label(frame, text=ticker, width=10, anchor="w").grid(row=i, column=0, padx=5, pady=3)
        var = tk.DoubleVar(value=allocations_list[i])
        allocation_vars[ticker] = var
        var.trace_add("write", make_callback(var))
        tk.Entry(frame, textvariable=var, width=10).grid(row=i, column=1, padx=5, pady=3)

    remaining_label = tk.Label(allocation_root, text="Remaining: 100.00%", font=("Arial", 10, "italic"))
    remaining_label.pack(pady=5)

    date_frame = tk.Frame(allocation_root)
    date_frame.pack(pady=10)


    tk.Label(date_frame, text="Start Date:").grid(row=0, column=0, padx=5)
    start_var = tk.StringVar()
    start_date = DateEntry(date_frame, textvariable=start_var, width=12,
                           background='darkblue', foreground='white',
                           borderwidth=2, date_pattern='yyyy-mm-dd')
    start_date.grid(row=0, column=1, padx=5)

    tk.Label(date_frame, text="End Date:").grid(row=0, column=2, padx=5)
    end_var = tk.StringVar()
    end_date = DateEntry(date_frame, textvariable=end_var, width=12,
                         background='darkblue', foreground='white',
                         borderwidth=2, date_pattern='yyyy-mm-dd')
    end_date.grid(row=0, column=3, padx=5)

    def submit():
        total = sum(v.get() for v in allocation_vars.values())
        if total != 100:
            messagebox.showerror("Invalid Allocation",
                                 f"Total allocation must equal 100% (currently {total:.2f}%).")
            return
        nonlocal allocations
        allocations = {ticker: var.get() for ticker, var in allocation_vars.items()}
        if not start_var.get() or not end_var.get():
            messagebox.showerror("Date Error", "Please select both start and end dates.")
            return
        allocation_root.destroy()

    tk.Button(allocation_root, text="Submit", command=submit).pack(pady=10)
    allocation_root.mainloop()

    return allocations, start_var.get(), end_var.get()

def get_price(selected_tickers, end, start, allocation, mpt_weights):
    if len(selected_tickers) > 1:
        query = f"""
            SELECT date, ticker, close 
            FROM price
            WHERE ticker IN {tuple(selected_tickers)}
            AND date BETWEEN '{start}' AND '{end}'
        """
    else:
        query = f"""
            SELECT date, ticker, close 
            FROM price
            WHERE ticker = '{selected_tickers[0]}'
            AND date BETWEEN '{start}' AND '{end}'
        """
    conn = sqlite3.connect('sp500_stocks.db')
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    results_df = pd.DataFrame(results, columns=['Date', 'Ticker', 'Close'])
    results_df['Date'] = pd.to_datetime(results_df['Date']).dt.date
    pivot_df = results_df.pivot(index='Date', columns='Ticker', values='Close')
    pivot_df = pivot_df.fillna(method="bfill")
    pivot_df['Value'] = 0
    for i in range(len(selected_tickers)):
        pivot_df['Value'] += (1 + pivot_df.iloc[:,i].pct_change()).cumprod() * (1000 * list(allocation.values())[i] /100)
    
    pivot_df['MPT Value'] = 0
    for ticker in mpt_weights.keys():
        pivot_df['MPT Value'] += (1 + pivot_df.loc[:,ticker].pct_change()).cumprod() * (1000 * mpt_weights[ticker])
    return pivot_df
def get_mpt_allocation(selected_tickers, start):
    query = f"""
    SELECT date, ticker, close
    FROM price
    WHERE date BETWEEN '{start - pd.DateOffset(years=5)}' AND '{start - pd.DateOffset(days=1)}'
    AND ticker IN {tuple(selected_tickers)}
    """
    conn = sqlite3.connect('sp500_stocks.db')
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    mpt_df = pd.DataFrame(results, columns=['Date', 'Ticker', 'Close'])
    mpt_df['Date'] = pd.to_datetime(mpt_df['Date']).dt.date
    mpt_pivot = mpt_df.pivot(index='Date', columns='Ticker', values='Close')
    mpt_pivot = mpt_pivot.fillna(method="bfill")

    # Calculate daily returns and covariance matrix
    returns = expected_returns.mean_historical_return(mpt_pivot)
    cov = risk_models.sample_cov(mpt_pivot)
    ef = EfficientFrontier(returns, cov)
    mpt_weights = ef.max_sharpe(risk_free_rate=0.04)
    return mpt_weights
