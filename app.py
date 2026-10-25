"""Chai Circuit - café sales dashboard (Streamlit + Plotly).

Run:  pip install -r requirements.txt
      streamlit run app.py
"""
import itertools

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Chai Circuit", page_icon="☕", layout="wide")

CITIES = ["Pune", "Mumbai", "Bengaluru", "Delhi", "Hyderabad"]
CATS = ["Chai", "Coffee", "Snacks", "Bakery", "Cold drinks"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# orange, green, magenta, mustard, violet (no blue)
COLORS = ["#f26b38", "#7bb661", "#d6336c", "#e9b72b", "#7048e8"]
HEAT = [[0, "#fff4c4"], [0.4, "#ffc45a"], [0.7, "#f26b38"], [1, "#d6336c"]]

st.markdown(
    """
    <style>
    .banner{background:#3b0f45;color:#fff;padding:18px 24px;border-radius:12px;
            border-bottom:6px solid #e9b72b;margin-bottom:12px}
    .banner h1{font-family:Georgia,serif;margin:0;font-size:30px;color:#fff}
    .banner p{margin:2px 0 0;color:#cdb7d8}
    [data-testid="stMetric"]{border:2px solid rgba(150,120,170,.35);
            border-left:10px solid var(--c);padding:12px 16px;
            background:rgba(150,120,170,.08);border-radius:14px}
    [data-testid="stHorizontalBlock"]{gap:1.5rem}
    [data-testid="stPlotlyChart"]{border:2px solid rgba(150,120,170,.35);
            border-top:7px solid #d6336c;border-radius:14px;padding:14px;
            background:rgba(150,120,170,.06);margin:14px 0 22px 0}
    [data-testid="stColumn"]:nth-of-type(1) [data-testid="stPlotlyChart"]{border-top-color:#f26b38}
    [data-testid="stColumn"]:nth-of-type(2) [data-testid="stPlotlyChart"]{border-top-color:#7048e8}
    [data-testid="stExpander"]{border:2px solid rgba(150,120,170,.35);
            border-radius:14px;padding:4px 8px;margin-top:8px}
    [data-testid="stDataFrame"]{border:2px solid rgba(150,120,170,.35);
            border-radius:10px;padding:6px}
    .block-container{padding-top:2rem;padding-bottom:3rem}
    </style>
    <div class="banner"><h1>Chai Circuit – café sales dashboard</h1>
    <p>Sample data for 5 cities and 5 menu categories.</p></div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def make_data() -> pd.DataFrame:
    """Generate synthetic sales data with a fixed seed."""
    rng = np.random.default_rng(7)
    city_w = dict(zip(CITIES, [1, 1.5, 1.3, 1.2, 0.9]))
    cat_w = dict(zip(CATS, [1.4, 1.2, 1, 0.8, 0.9]))
    price = dict(zip(CATS, [40, 95, 70, 85, 110]))
    season = [0.9, 0.9, 0.95, 1.05, 1.15, 1.1, 0.95, 0.95, 1, 1.05, 1.15, 1.3]
    rows = []
    for year, (mi, month), city, cat in itertools.product(
        [2025, 2026], enumerate(MONTHS), CITIES, CATS
    ):
        growth = 1.12 if year == 2026 else 1.0
        orders = round(900 * city_w[city] * cat_w[cat] * season[mi] * growth
                       * rng.uniform(0.85, 1.15))
        revenue = orders * price[cat] * rng.uniform(0.92, 1.08)
        rows.append((year, month, city, cat, orders, revenue))
    df = pd.DataFrame(rows, columns=["Year", "Month", "City", "Category", "Orders", "Revenue"])
    df["Month"] = pd.Categorical(df["Month"], MONTHS, ordered=True)
    return df


df = make_data()

# ---------- filters ----------
with st.sidebar:
    st.header("Filters")
    year = st.selectbox("Year", [2026, 2025])
    cities = st.multiselect("City", CITIES, default=CITIES)
    cats = st.multiselect("Category", CATS, default=CATS)


def pick(y):
    return df[(df.Year == y) & df.City.isin(cities) & df.Category.isin(cats)]


cur, prev = pick(year), pick(year - 1)
if cur.empty:
    st.warning("Nothing matches these filters. Select at least one city and one category.")
    st.stop()

# ---------- KPIs ----------
rev, orders = cur.Revenue.sum(), cur.Orders.sum()
growth = (rev - prev.Revenue.sum()) / prev.Revenue.sum() * 100 if not prev.empty else None
by_month = cur.groupby("Month", observed=True).Revenue.sum()
by_cat = cur.groupby("Category").Revenue.sum()


def lakh(v):
    return f"₹{v / 1e7:.2f} Cr" if v >= 1e7 else f"₹{v / 1e5:.1f} L"


k = st.columns(5)
k[0].metric("Revenue", lakh(rev), f"{growth:.1f}% vs {year - 1}" if growth is not None else None)
k[1].metric("Orders", f"{orders:,}")
k[2].metric("Average order", f"₹{rev / orders:.0f}")
k[3].metric("Best month", by_month.idxmax(), lakh(by_month.max()), delta_color="off")
k[4].metric("Top category", by_cat.idxmax(), lakh(by_cat.max()), delta_color="off")
for col, c in zip(k, COLORS):  # colour each KPI's left border
    col.markdown(f"<style>div[data-testid='stColumn']:nth-of-type({k.index(col) + 1}) "
                 f"[data-testid='stMetric']{{--c:{c}}}</style>", unsafe_allow_html=True)

# ---------- row 1: trend + city share ----------
c1, c2 = st.columns([7, 5])

trend = go.Figure()
trend.add_bar(x=MONTHS, y=by_month.reindex(MONTHS).values, name=str(year),
              marker_color=[COLORS[i % 5] for i in range(12)])
if not prev.empty:
    p = prev.groupby("Month", observed=True).Revenue.sum().reindex(MONTHS)
    trend.add_scatter(x=MONTHS, y=p.values, name=str(year - 1),
                      line=dict(color="#d6336c", dash="dash"))
trend.update_layout(title="Revenue by month", legend=dict(orientation="h", y=-0.15),
                    margin=dict(t=50, b=10), yaxis_title="Revenue (₹)")
c1.plotly_chart(trend, use_container_width=True)

share = cur.groupby("City").Revenue.sum().reindex(CITIES).dropna().reset_index()
pie = px.pie(share, names="City", values="Revenue", hole=0.55, title="Share by city",
             color="City", color_discrete_map=dict(zip(CITIES, COLORS)))
pie.update_layout(legend=dict(orientation="h", y=-0.15), margin=dict(t=50, b=10))
c2.plotly_chart(pie, use_container_width=True)

# ---------- row 2: category bar + scatter ----------
c3, c4 = st.columns(2)

cat_df = by_cat.reindex(CATS).dropna().reset_index()
bar = px.bar(cat_df, x="Revenue", y="Category", orientation="h", color="Category",
             color_discrete_map=dict(zip(CATS, COLORS[::-1])), title="Revenue by category")
bar.update_layout(showlegend=False, margin=dict(t=50, b=10))
c3.plotly_chart(bar, use_container_width=True)

pair = cur.groupby(["City", "Category"], as_index=False).agg(Orders=("Orders", "sum"),
                                                            Revenue=("Revenue", "sum"))
pair["Avg order (₹)"] = pair.Revenue / pair.Orders
sc = px.scatter(pair, x="Orders", y="Avg order (₹)", color="City", hover_name="Category",
                color_discrete_map=dict(zip(CITIES, COLORS)),
                title="Orders vs average order value")
sc.update_traces(marker=dict(size=13, line=dict(width=1, color="white")))
sc.update_layout(legend=dict(orientation="h", y=-0.2), margin=dict(t=50, b=10))
c4.plotly_chart(sc, use_container_width=True)

# ---------- heatmap ----------
heat = (cur.pivot_table(index="City", columns="Category", values="Revenue", aggfunc="sum")
        .reindex(index=[c for c in CITIES if c in cities],
                 columns=[c for c in CATS if c in cats]) / 1e5)
hm = px.imshow(heat, text_auto=".1f", color_continuous_scale=HEAT, aspect="auto",
               title="City × category heatmap (₹ lakh)")
hm.update_layout(margin=dict(t=50, b=10), coloraxis_showscale=False)
st.plotly_chart(hm, use_container_width=True)

with st.expander("View filtered data"):
    st.dataframe(cur, use_container_width=True, hide_index=True)
    st.download_button("Download CSV", cur.to_csv(index=False), "cafe_sales.csv", "text/csv")

st.caption("Data is synthetic and generated with a fixed seed. Built with Streamlit and Plotly (open source).")