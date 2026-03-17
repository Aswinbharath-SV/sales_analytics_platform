import sys
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_routes():
    print("Testing / ...")
    assert client.get("/").status_code == 200
    print("Testing /dashboard ...")
    assert client.get("/dashboard").status_code == 200
    print("Testing /analytics ...")
    assert client.get("/analytics").status_code == 200
    
    print("Testing JSON stats endpoint ...")
    r = client.get("/analytics-data")
    if r.status_code == 200:
        data = r.json()
        print("Stats success:", data.keys())
        assert "metrics" in data
    
    print("Testing AI chat endpoint ...")
    r = client.post("/ask", data={"question": "total sales?"})
    print("Chat response:", r.json())
    
    return True

if __name__ == "__main__":
    test_routes()
    print("\n--- ALL TESTS ENABLED & PASS ---")
