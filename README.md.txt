# 📊 Stock Allocation Optimizer (Streamlit App)

This app helps you allocate your investment across a list of stocks or ETFs based on target allocation percentages, using real-time market prices and optimization.

Built with [Streamlit](https://streamlit.io) and powered by [Yahoo Finance](https://finance.yahoo.com/) for live price data.

---

## 🚀 Features

- 📁 Upload a CSV file with your desired allocation
- 💰 Enter a total investment amount
- ⚙️ Optimized allocation using integer programming
- 📈 Visual output and pie chart for actual allocation
- 🌍 Deployable to Streamlit Cloud (free)

---

## 📝 Input Format

Upload a CSV file with the following structure:

```csv
symbol,target_allocation
AAPL,0.3
GOOG,0.2
MSFT,0.5
