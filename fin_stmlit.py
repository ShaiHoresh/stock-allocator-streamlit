import streamlit as st
import pandas as pd
import yfinance as yf
from pulp import LpProblem, LpVariable, lpSum, LpMinimize, LpMaximize, LpInteger, LpContinuous
import matplotlib.pyplot as plt

st.set_page_config(page_title="Stock Allocation Optimizer", layout="wide")
st.title("📊 Stock Allocation Optimizer")

st.markdown("""
Upload a CSV file with your target allocations **OR** enter them manually:
- CSV Format: `symbol,target_allocation`
- Target allocations should sum to ~1.0
""")

manual_entry = st.checkbox("Enter allocations manually instead of uploading a CSV")

# Load input data
df_alloc = None
if manual_entry:
    num_stocks = st.number_input("Number of stocks", min_value=1, max_value=20, value=5)
    symbols = []
    allocations = []
    for i in range(int(num_stocks)):
        cols = st.columns([2, 1])
        symbol = cols[0].text_input(f"Symbol {i+1}", key=f"sym_{i}")
        allocation = cols[1].number_input(f"Weight {i+1}", min_value=0.0, max_value=1.0, step=0.01, key=f"alloc_{i}")
        symbols.append(symbol.upper().strip())
        allocations.append(allocation)

    if sum(allocations) > 0:
        df_alloc = pd.DataFrame({"symbol": symbols, "target_allocation": allocations})
        df_alloc["target_allocation"] /= df_alloc["target_allocation"].sum()
    else:
        st.stop()
else:
    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    if uploaded_file:
        df_alloc = pd.read_csv(uploaded_file)
        df_alloc.columns = df_alloc.columns.str.strip().str.lower()  # מנקה רווחים ומקטין לאותיות קטנות
        required_cols = {"symbol", "target_allocation"}
        if not required_cols.issubset(df_alloc.columns):
            st.error(f"CSV must contain the columns: {required_cols}")
            st.stop()

        df_alloc["symbol"] = df_alloc["symbol"].str.upper().str.strip()
        df_alloc["target_allocation"] = df_alloc["target_allocation"] / df_alloc["target_allocation"].sum()

#    if uploaded_file:
#        df_alloc = pd.read_csv(uploaded_file)
#        df_alloc["symbol"] = df_alloc["symbol"].str.upper().str.strip()
#        df_alloc["target_allocation"] = df_alloc["target_allocation"] / df_alloc["target_allocation"].sum()
    else:
        st.stop()

# Editable table before processing
df_alloc = st.data_editor(df_alloc, num_rows="dynamic")

# Get investment amount
investment = st.number_input("Total investment amount ($)", min_value=100.0, step=100.0)

# Optimization mode
mode = st.selectbox("Optimization strategy", ["Minimize deviation from target allocation", "Maximize money usage"])

# Fetch current prices
@st.cache_data(ttl=3600)
def get_prices(symbols):
    data = yf.download(symbols, period="1d", interval="1m", progress=False)
    if len(symbols) == 1:
        return {symbols[0]: data['Close'].iloc[-1]}
    return {s: data['Close'][s].dropna().iloc[-1] for s in symbols if s in data['Close']}

symbols = df_alloc['symbol'].tolist()
prices = get_prices(symbols)
df_alloc['price'] = df_alloc['symbol'].map(prices)

if df_alloc['price'].isnull().any():
    st.error("Failed to fetch prices for some symbols.")
    st.dataframe(df_alloc)
    st.stop()

# Optimization model
model = LpProblem("StockAllocation", LpMinimize if mode == "Minimize deviation from target allocation" else LpMaximize)
quantities = {s: LpVariable(f"qty_{s}", lowBound=0, cat=LpInteger) for s in symbols}

if mode == "Minimize deviation from target allocation":
    target_values = {s: df_alloc.loc[df_alloc['symbol'] == s, 'target_allocation'].values[0] * investment for s in symbols}
    deviation_vars = {s: LpVariable(f"dev_{s}", lowBound=0, cat=LpContinuous) for s in symbols}

    for s in symbols:
        actual_cost = quantities[s] * prices[s]
        model += actual_cost - target_values[s] <= deviation_vars[s]
        model += target_values[s] - actual_cost <= deviation_vars[s]

    model += lpSum(deviation_vars.values())
    model += lpSum([quantities[s] * prices[s] for s in symbols]) <= investment
    model += lpSum([quantities[s] * prices[s] for s in symbols]) >= investment - 100

else:
    # Maximize use of funds
    model += lpSum([quantities[s] * prices[s] for s in symbols])
    model += lpSum([quantities[s] * prices[s] for s in symbols]) <= investment

model.solve()

# Output results
df_alloc['quantity'] = df_alloc['symbol'].map(lambda s: int(quantities[s].value()))
df_alloc['total_cost'] = df_alloc['quantity'] * df_alloc['price']
df_alloc['final_allocation'] = df_alloc['total_cost'] / df_alloc['total_cost'].sum()

st.subheader("📋 Purchase Plan")
st.dataframe(df_alloc[['symbol', 'price', 'quantity', 'total_cost', 'target_allocation', 'final_allocation']])

# Chart
df_alloc_plot = df_alloc.dropna(subset=["final_allocation"])
if not df_alloc_plot.empty:
    fig, ax = plt.subplots()
    ax.pie(df_alloc_plot['final_allocation'], labels=df_alloc_plot['symbol'], autopct='%1.1f%%')
    ax.set_title("Final Allocation")
    st.pyplot(fig)
else:
    st.warning("No valid allocations to plot.")


# Unused funds
used = df_alloc['total_cost'].sum()
remaining = investment - used
st.info(f"Used: ${used:.2f}, Remaining: ${remaining:.2f}")
