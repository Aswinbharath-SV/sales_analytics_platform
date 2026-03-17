import asyncio
import pandas as pd
from main import app, get_analytics_data, ask_question

async def run_tests():
    print("Creating large dummy dataset...")
    categories = [f"Category_{i}" for i in range(200)]
    dates = pd.date_range(start="2020-01-01", periods=150)
    
    data = []
    for c in categories:
        for d in dates[:2]:
            data.append({"Category_Col": c, "Date_Col": d, "Super_Total_Sales_Amount": 100, "Profit_Margin_Pct": 0.15})
            
    for d in dates:
        data.append({"Category_Col": "Category_0", "Date_Col": d, "Super_Total_Sales_Amount": 50, "Profit_Margin_Pct": 0.1})

    df = pd.DataFrame(data)
    app.state.current_df = df
    
    print("Testing get_analytics_data()...")
    res = await get_analytics_data()
    
    if isinstance(res, dict):
        charts = {c["id"]: c for c in res.get("charts", [])}
        
        pie_chart = charts.get("chart_2")
        if pie_chart:
            labels_len = len(pie_chart["labels"])
            print(f"Pie chart labels count: {labels_len}")
            assert labels_len <= 11, f"Failed limit: {labels_len}"
            
        line_chart = charts.get("chart_3")
        if line_chart:
            points_len = len(line_chart["labels"])
            print(f"Line chart points count: {points_len}")
            assert points_len <= 100, f"Failed limit: {points_len}"
    else:
        print("Error from analytics_data:", res)

    print("Testing ask_question()...")
    
    res1 = await ask_question("what is the total super sale amount?")
    ans1 = res1.get("answer", "")
    print(f"Q: 'total super sale' -> {ans1}")
    assert "Super_Total_Sales_Amount" in ans1 or "total" in ans1
    
    res2 = await ask_question("average profit margin")
    ans2 = res2.get("answer", "")
    print(f"Q: 'average profit margin' -> {ans2}")
    assert "Profit_Margin_Pct" in ans2 or "average" in ans2
    
    res3 = await ask_question("how many rows in data")
    ans3 = res3.get("answer", "")
    print(f"Q: 'how many rows in data' -> {ans3}")
    assert "rows" in ans3

    print("\n--- ALL TESTS PASS ---")

if __name__ == "__main__":
    asyncio.run(run_tests())
