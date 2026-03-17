import sys
import os
import pandas as pd
from fastapi.testclient import TestClient

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app

client = TestClient(app)

def test_large_dataset():
    print("Creating large dummy dataset...")
    # Create a DataFrame with 200 unique categories and 150 dates
    categories = [f"Category_{i}" for i in range(200)]
    dates = pd.date_range(start="2020-01-01", periods=150)
    
    data = []
    for c in categories:
        for d in dates[:2]: # just 2 dates per category to keep it reasonable size
            data.append({"Category_Col": c, "Date_Col": d, "Super_Total_Sales_Amount": 100, "Profit_Margin_Pct": 0.15})
            
    # Add some to date to make dates > 100
    for d in dates:
        data.append({"Category_Col": "Category_0", "Date_Col": d, "Super_Total_Sales_Amount": 50, "Profit_Margin_Pct": 0.1})

    df = pd.DataFrame(data)
    app.state.current_df = df
    
    print("Testing /analytics-data endpoint with large dataset...")
    r = client.get("/analytics-data")
    assert r.status_code == 200
    data = r.json()
    
    # Verify chart constraints
    charts = {c["id"]: c for c in data["charts"]}
    
    # Bar chart might have 10
    
    # Pie chart should have exactly 11 (10 top + 1 Other)
    pie_chart = charts.get("chart_2")
    if pie_chart:
        assert len(pie_chart["labels"]) <= 11, f"Pie chart has too many labels: {len(pie_chart['labels'])}"
        print("Pie chart limit verified.")
        
    line_chart = charts.get("chart_3")
    if line_chart:
        assert len(line_chart["labels"]) <= 100, f"Line chart has too many points: {len(line_chart['labels'])}"
        print("Line chart limit verified.")
        
    print("Testing AI chat endpoint with fuzzy matching...")
    
    # Test "Super_Total_Sales_Amount" with a fuzzy typo
    r = client.post("/ask", data={"question": "what is the total super sale amount?"})
    ans = r.json().get("answer", "")
    print(f"Q: what is the total super sale amount? -> A: {ans}")
    assert "Super_Total_Sales_Amount" in ans
    
    # Test "Profit_Margin_Pct"
    r = client.post("/ask", data={"question": "average profit margin"})
    ans = r.json().get("answer", "")
    print(f"Q: average profit margin -> A: {ans}")
    assert "Profit_Margin_Pct" in ans
    
    # Test column metadata
    r = client.post("/ask", data={"question": "how many rows in data"})
    ans = r.json().get("answer", "")
    print(f"Q: how many rows in data -> A: {ans}")
    assert "rows in the dataset" in ans

    print("\n--- ALL TESTS PASS ---")

if __name__ == "__main__":
    test_large_dataset()
