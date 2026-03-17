import asyncio
import pandas as pd
import time
from main import app, ask_question

async def run_tests():
    print("Creating dummy dataset...")
    df = pd.DataFrame({"Super_Total_Sales_Amount": [100, 200, 300], "Profit_Margin_Pct": [0.15, 0.2, 0.25]})
    app.state.current_df = df
    
    print("Testing ask_question() speed...")
    
    start = time.time()
    res1 = await ask_question("what is the total super sale amount?")
    end = time.time()
    ans1 = res1.get("answer", "")
    print(f"Q: 'total super sale' -> {ans1} (Took {end-start:.2f}s)")
    
    start = time.time()
    res2 = await ask_question("average profit margin")
    end = time.time()
    ans2 = res2.get("answer", "")
    print(f"Q: 'average profit margin' -> {ans2} (Took {end-start:.2f}s)")
    
if __name__ == "__main__":
    asyncio.run(run_tests())
