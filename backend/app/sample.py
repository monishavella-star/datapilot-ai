"""Synthetic sample data: all transactions are fictional."""
from datetime import date, timedelta
import random
import pandas as pd


def sample_sales():
    rng = random.Random(42)
    regions = ["North", "South", "East", "West"]
    categories = {"Electronics": ["Headphones", "Keyboard", "Webcam"],
                  "Home": ["Desk lamp", "Storage box", "Coffee maker"],
                  "Fitness": ["Yoga mat", "Water bottle", "Dumbbells"],
                  "Books": ["Novel", "Workbook", "Journal"]}
    prices = {"Electronics": (1300, 3900), "Home": (550, 2200),
              "Fitness": (350, 1900), "Books": (190, 900)}
    out = []
    for i in range(960):
        d = date(2026, 1, 1) + timedelta(days=rng.randint(0, 180))
        category = rng.choice(list(categories))
        region = rng.choice(regions)
        product = rng.choice(categories[category])
        qty = rng.randint(1, 5)
        base = rng.randint(*prices[category])
        # Deliberate March slump creates an interesting, verifiable demo insight.
        factor = 0.60 if d.month == 3 else 1.0
        if region == "East" and d.month == 3:
            factor *= 0.77
        revenue = round(qty * base * factor, 2)
        cost_rate = rng.uniform(0.58, 0.84)
        out.append({"order_id": f"ORD-{10001+i}", "date": d.isoformat(),
                    "region": region, "category": category, "product": product,
                    "quantity": qty, "revenue": revenue,
                    "profit": round(revenue * (1 - cost_rate), 2)})
    return pd.DataFrame(out)