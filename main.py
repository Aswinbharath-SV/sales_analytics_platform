import os
import io
import json
import hashlib
import pandas as pd
import sqlite3
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# --- Load environment variables ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "super-secret-key")  # you can override in Render
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- FastAPI app ---
app = FastAPI(title="Radiance Sales Analytics")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# --- Directories ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "frontend", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "frontend", "templates")
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_DATA_PATH = os.path.join(DATA_DIR, "sales_dataset.csv")
DB_PATH = os.path.join(BASE_DIR, "users.db")

# --- Init DB ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, name TEXT)''')
    conn.commit()
    conn.close()
init_db()

# --- Create folders ---
for folder in [STATIC_DIR, os.path.join(STATIC_DIR,"css"), os.path.join(STATIC_DIR,"js"), TEMPLATES_DIR, DATA_DIR]:
    os.makedirs(folder, exist_ok=True)

# --- Mount static ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- Global dataset ---
app.state.current_df = None
if os.path.exists(DEFAULT_DATA_PATH):
    try:
        app.state.current_df = pd.read_csv(DEFAULT_DATA_PATH)
    except Exception as e:
        print("Error loading default data:", e)

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/dashboard", 303)
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/dashboard", 303)
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", 303)
    response = templates.TemplateResponse("dashboard.html", {"request": request})
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", 303)
    response = templates.TemplateResponse("analytics.html", {"request": request})
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

# --- API: Register/Login ---
@app.post("/api/register")
async def api_register(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", (email, hashed_pw, name))
        conn.commit(); conn.close()
        request.session["user"] = email
        return RedirectResponse("/dashboard", 303)
    except sqlite3.IntegrityError:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email already registered"})

@app.post("/api/login")
async def api_login(request: Request, email: str = Form(...), password: str = Form(...)):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hashed_pw))
    user = c.fetchone(); conn.close()
    if user:
        request.session["user"] = email
        return RedirectResponse("/dashboard", 303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password"})

@app.get("/logout")
async def logout_user(request: Request):
    request.session.clear()
    return RedirectResponse("/", 303)

# --- API: Upload / Load Sample ---
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        return JSONResponse({"error":"Only CSV allowed"}, 400)
    try:
        df = pd.read_csv(io.StringIO((await file.read()).decode("utf-8")))
        app.state.current_df = df
        return {"message":"Uploaded successfully","filename":file.filename,"rows":len(df)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

@app.post("/load-sample")
async def load_sample():
    if os.path.exists(DEFAULT_DATA_PATH):
        app.state.current_df = pd.read_csv(DEFAULT_DATA_PATH)
        return {"message":"Sample data loaded","filename":"sales_dataset.csv","rows":len(app.state.current_df)}
    return JSONResponse({"error":"Sample data not found"},404)

# --- API: Analytics ---
@app.get("/analytics-data")
async def get_analytics_data():
    df = app.state.current_df
    if df is None or df.empty:
        return JSONResponse({"error":"No data available"},404)
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object','category']).columns.tolist()
    metrics = {"total_rows": len(df), "total_columns": len(df.columns)}
    for col in numeric_cols:
        metrics[f"total_{col.lower()}"] = float(df[col].sum())
        metrics[f"avg_{col.lower()}"] = float(df[col].mean())
        metrics[f"max_{col.lower()}"] = float(df[col].max())
        metrics[f"min_{col.lower()}"] = float(df[col].min())
    charts = []
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = next((c for c in numeric_cols if "sale" in c.lower() or "revenue" in c.lower()), numeric_cols[0])
        grouped = df.groupby(cat_col)[num_col].sum().reset_index().sort_values(num_col,ascending=False).head(10)
        charts.append({"id":"chart_1","type":"bar","title":f"Total {num_col} by {cat_col}","labels":grouped[cat_col].tolist(),"values":grouped[num_col].tolist()})
        pie_col = categorical_cols[1] if len(categorical_cols)>1 else categorical_cols[0]
        pie_grouped = df.groupby(pie_col).size().reset_index(name='count').sort_values("count",ascending=False)
        if len(pie_grouped)>10:
            top10 = pie_grouped.head(10)
            other = pd.DataFrame({pie_col:["Other"],"count":[pie_grouped['count'][10:].sum()]})
            pie_grouped = pd.concat([top10,other],ignore_index=True)
        charts.append({"id":"chart_2","type":"pie","title":f"Distribution by {pie_col}","labels":pie_grouped[pie_col].tolist(),"values":[int(x) for x in pie_grouped['count'].tolist()]})
        date_col = next((c for c in df.columns if "date" in c.lower() or "time" in c.lower()), None)
        if date_col:
            time_grouped = df.groupby(date_col)[num_col].sum().reset_index().sort_values(date_col)
            if len(time_grouped)>100:
                time_grouped = time_grouped.tail(100)
            charts.append({"id":"chart_3","type":"line","title":f"{num_col} Trend over Time","labels":time_grouped[date_col].tolist(),"values":time_grouped[num_col].tolist()})
    return {"metrics":metrics,"charts":charts}

# --- API: Ask AI ---
@app.post("/ask")
async def ask_question(question: str = Form(...)):
    df = app.state.current_df
    if df is None or df.empty:
        return {"answer":"No data loaded."}
    if not GEMINI_API_KEY:
        return {"answer":"Gemini API key missing."}
    columns_info = {col:str(df[col].dtype) for col in df.columns}
    prompt = f"""
    You are an AI assistant. User asks: {question}
    DataFrame columns: {columns_info}
    Return JSON: {{'column':'Exact_Column_Name','operation':'sum/mean/max/min/count/unique_count'}}
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        res = model.generate_content(prompt)
        action = json.loads(res.text.strip().replace("```",""))
        col = action.get("column")
        op = action.get("operation")
        if col=="ROW_COUNT": return {"answer": f"{len(df):,} rows in dataset"}
        if col not in df.columns: return {"answer": f"Column '{col}' not in dataset"}
        val = None
        if op=="sum": val=df[col].sum()
        elif op=="mean": val=df[col].mean()
        elif op=="max": val=df[col].max()
        elif op=="min": val=df[col].min()
        elif op=="count": val=df[col].count()
        elif op=="unique_count": val=df[col].nunique()
        else: return {"answer": f"Unsupported operation {op}"}
        if isinstance(val,(int,float)):
            return {"answer": f"{op} of {col} is {val:,.2f}"}
        return {"answer": f"{op} of {col} is {val}"}
    except Exception as e:
        return {"answer": f"AI error: {e}"}

# --- Run server ---
if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))