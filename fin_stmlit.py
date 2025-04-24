import streamlit as st
import pandas as pd
import yfinance as yf
from pulp import LpProblem, LpVariable, LpInteger, lpSum, LpMinimize, LpStatus

st.title("📊 Stock Allocation Optimizer")

st.markdown("""
Upload a CSV file with two columns:

- `symbol`: Stock or ETF ticker symbol
- `target_allocation`: The target weight (as a decimal, e.g., 0.25 for 25%)
""")

uploaded_file = st.file_uploader("Upload your stock allocation CSV", type=["csv"])

investment = st.number_input("Total investment amount ($)", min_value=0.0, step=100.0)
max_units = st.number_input("Maximum units per stock (for optimization)", min_value=1, step=1, value=30)

if uploaded_file and investment > 0:
    df = pd.read_csv(uploaded_file)
    df['symbol'] = df['symbol'].str.upper()

    st.write("### Uploaded Allocation Table")
    st.dataframe(df)

    st.write("Fetching current prices...")
    prices = {}
    for symbol in df['symbol']:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if not hist.empty:
            prices[symbol] = hist['Close'].iloc[-1]
        else:
            prices[symbol] = 0.0

    df['price'] = df['symbol'].map(prices)

    st.write("### Current Prices")
    st.dataframe(df[['symbol', 'price']])

    st.write("Running allocation optimizer...")
    prob = LpProblem("Stock Allocation", LpMinimize)

    units = {row['symbol']: LpVariable(f"units_{row['symbol']}", lowBound=0, upBound=max_units, cat=LpInteger) for _, row in df.iterrows()}

    actual_value = lpSum([units[symbol] * df.loc[df['symbol'] == symbol, 'price'].values[0] for symbol in df['symbol']])
    prob += investment - actual_value  # Objective: minimize leftover cash

    prob += actual_value <= investment  # Constraint: don't exceed budget

    prob.solve()

    st.write(f"**Status:** {LpStatus[prob.status]}")

    results = []
    total_invested = 0
    for _, row in df.iterrows():
        symbol = row['symbol']
        price = row['price']
        count = int(units[symbol].value())
        cost = count * price
        results.append({
            "symbol": symbol,
            "price": round(price, 2),
            "units": count,
            "cost": round(cost, 2),
            "planned_weight": row['target_allocation'],
        })
        total_invested += cost

    results_df = pd.DataFrame(results)
    results_df["actual_weight"] = results_df["cost"] / total_invested

    st.write("### Allocation Results")
    st.dataframe(results_df[["symbol", "units", "price", "cost", "planned_weight", "actual_weight"]])

    st.write(f"**Total Invested:** ${round(total_invested, 2)}")
    st.write(f"**Leftover Cash:** ${round(investment - total_invested, 2)}")

    st.write("### Pie Chart of Actual Allocation")
    st.pyplot(results_df.set_index("symbol")["actual_weight"].plot.pie(autopct='%1.1f%%', figsize=(6, 6)).get_figure())
