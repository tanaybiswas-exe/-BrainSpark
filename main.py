from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import jwt
import bcrypt
from datetime import datetime, timedelta

# CONFIGURATIONS
SECRET_KEY = "SUPER_SECRET_BRAIN_SPARK_KEY_AI_TOKEN" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 

app = FastAPI(title="BrainSpark AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- DATABASE SETUP ---
def get_db():
    conn = sqlite3.connect("brain_spark.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            institute TEXT NOT NULL,
            department TEXT NOT NULL,
            year_semester TEXT NOT NULL,
            phone TEXT NOT NULL,
            skills TEXT DEFAULT '',
            github_url TEXT DEFAULT '',
            linkedin_url TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            tech_stack TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            details TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- HELPERS ---
def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise HTTPException(status_code=401)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user is None: raise HTTPException(status_code=401)
    return user

# --- SCHEMAS ---
class RegisterSchema(BaseModel):
    username: str; password: str; name: str; institute: str
    department: str; year_semester: str; phone: str

class LoginSchema(BaseModel):
    username: str; password: str

class UpdateProfileSchema(BaseModel):
    name: str; institute: str; department: str
    year_semester: str; phone: str; skills: str = ""; github_url: str = ""; linkedin_url: str = ""

class GenerateIdeasSchema(BaseModel):
    description: str
    skills: Optional[str] = ""
    tech_stack: Optional[str] = ""

class SaveProjectSchema(BaseModel):
    title: str
    description: str
    tech_stack: str

class ForgotPasswordSchema(BaseModel):
    username: str
    phone: str
    new_password: str

class MentorQuery(BaseModel):
    project_id: int
    message: str

# --- ROUTES ---

@app.post("/register")
async def register(user: RegisterSchema):
    conn = get_db()
    try:
        hashed_pw = get_password_hash(user.password)
        conn.execute("INSERT INTO users (username, password, name, institute, department, year_semester, phone) VALUES (?,?,?,?,?,?,?)",
                     (user.username, hashed_pw, user.name, user.institute, user.department, user.year_semester, user.phone))
        conn.commit()
        return {"message": "User created successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    except Exception as e:
        print("🔴 Registration Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/login")
async def login(form: LoginSchema):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (form.username,)).fetchone()
    conn.close()
    if not user or not verify_password(form.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user['username']})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/profile")
async def get_profile(user = Depends(get_current_user)):
    user_dict = dict(user)
    conn = get_db()
    total_p = conn.execute("SELECT COUNT(*) FROM projects WHERE user_id = ?", (user['id'],)).fetchone()[0]
    done_m = conn.execute("""
        SELECT COUNT(*) FROM milestones m 
        JOIN projects p ON m.project_id = p.id 
        WHERE p.user_id = ? AND m.completed = 1
    """, (user['id'],)).fetchone()[0]
    conn.close()
    
    user_dict["stats"] = {
        "total_projects": total_p,
        "completed_milestones": done_m
    }
    return user_dict

@app.put("/update-profile")
async def update_profile(data: UpdateProfileSchema, user = Depends(get_current_user)):
    conn = get_db()
    conn.execute("UPDATE users SET name=?, institute=?, department=?, year_semester=?, phone=?, skills=?, github_url=?, linkedin_url=? WHERE id=?",
                 (data.name, data.institute, data.department, data.year_semester, data.phone, data.skills, data.github_url, data.linkedin_url, user['id']))
    conn.commit()
    conn.close()
    return {"message": "Profile updated"}

@app.post("/generate-ideas")
async def generate_ideas(data: GenerateIdeasSchema, user = Depends(get_current_user)):
    desc = data.description.lower()
    tech = data.tech_stack if data.tech_stack else "Python, FastAPI, SQLite"
    
    title1 = f"AI-Powered {data.description.title()} Control Suite"
    title2 = f"Next-Gen {data.description.title()} Optimization Network"
    
    ideas = [
        {
            "title": title1,
            "description": f"An advanced intelligent system tailored for {data.description}. Features a real-time responsive analytics core and secure state tracking matrix.",
            "tech_stack": tech,
            "features": "• Real-Time Stream Monitoring Matrix Dashboard\n• Responsive Data Visualizer Mockups with State Optimization\n• Secure End-to-End Cryptographic Tokens Validation Access"
        },
        {
            "title": title2,
            "description": f"Cloud-integrated ecosystem specialized in optimizing operations for {data.description} using automated edge triggers and multi-tenant telemetry dashboards.",
            "tech_stack": f"{tech}, TailwindCSS",
            "features": "• Automated Pipeline Workflow & Trigger Logs\n• Highly Scalable Distributed Event Hub Broker\n• Native Light/Dark UI Glassmorphic Console Theme"
        }
    ]
    return ideas

@app.post("/save-project")
async def save_project(project: SaveProjectSchema, user = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO projects (user_id, title, description, tech_stack) VALUES (?, ?, ?, ?)",
            (user['id'], project.title, project.description, project.tech_stack)
        )
        project_id = cursor.lastrowid
        
        milestones = [
            ("Phase 1: Environment & Schema Initialisation", "• Setup base virtual environment\n• Initialize SQLite database configuration matrices\n• Run backend structural route checks"),
            ("Phase 2: Core Engine Architecture & Logic", "• Build primary API validation endpoints\n• Connect state models with front-end services\n• Execute pipeline verification tests"),
            ("Phase 3: Frontend Interface & Deployment Ready", "• Inject custom CSS layout structures\n• Connect real-time fetch requests to endpoints\n• Compile final production builds")
        ]
        
        for title, details in milestones:
            cursor.execute(
                "INSERT INTO milestones (project_id, title, details, completed) VALUES (?, ?, ?, 0)",
                (project_id, title, details)
            )
            
        conn.commit()
        return {"message": "Project and milestones tracked successfully", "project_id": project_id}
    except Exception as e:
        print("🔴 Save Project Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/saved-projects")
async def saved_projects(user = Depends(get_current_user)):
    conn = get_db()
    projects = conn.execute("SELECT * FROM projects WHERE user_id = ?", (user['id'],)).fetchall()
    
    result = []
    for p in projects:
        p_dict = dict(p)
        milestones = conn.execute("SELECT * FROM milestones WHERE project_id = ?", (p['id'],)).fetchall()
        p_dict["milestones"] = [dict(m) for m in milestones]
        result.append(p_dict)
        
    conn.close()
    return result

@app.post("/milestones/{milestone_id}/toggle")
async def toggle_milestone(milestone_id: int, user = Depends(get_current_user)):
    conn = get_db()
    milestone = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,)).fetchone()
    if not milestone:
        conn.close()
        raise HTTPException(status_code=404, detail="Milestone not found")
        
    new_status = 1 if milestone['completed'] == 0 else 0
    conn.execute("UPDATE milestones SET completed = ? WHERE id = ?", (new_status, milestone_id))
    conn.commit()
    conn.close()
    return {"message": "Milestone status toggled successfully"}

@app.delete("/projects/{project_id}")
async def delete_project(project_id: int, user = Depends(get_current_user)):
    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, user['id'])).fetchone()
    if not project:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")
        
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.execute("DELETE FROM milestones WHERE project_id = ?", (project_id,))
    conn.commit()
    conn.close()
    return {"message": "Project removed from ecosystem"}

@app.post("/chat-with-mentor")
async def chat_with_mentor(query: MentorQuery, current_user = Depends(get_current_user)):
    conn = get_db()
    project = conn.execute("SELECT title, tech_stack FROM projects WHERE id = ? AND user_id = ?", 
                           (query.project_id, current_user["id"])).fetchone()
    conn.close()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    reply = f"As your mentor, I see you are working on '{project['title']}' using {project['tech_stack']}. Regarding '{query.message}', I suggest reviewing the project structure and best practices."
    return {"reply": reply}

@app.get("/projects/{project_id}/directory-tree")
async def directory_tree(project_id: int, user = Depends(get_current_user)):
    tree = """.\n├── app/\n│   ├── core/\n│   │   ├── __init__.py\n│   │   └── security.py\n│   ├── database/\n│   │   ├── session.py\n│   │   └── models.py\n│   ├── endpoints/\n│   │   └── controller.py\n│   └── main.py\n├── tests/\n│   └── test_api.py\n├── requirements.txt\n└── README.md"""
    return {"tree": tree}

@app.get("/projects/{project_id}/proposal")
async def project_proposal(project_id: int, user = Depends(get_current_user)):
    proposal = """# System Architecture Blueprint Proposal\n\n## 1. Project Specifications\n- Target Scope: Academic Production Grade System\n- Architecture: Microservices Ready API Layout\n- Data Store: Optimized Relational Schema Engine\n\n## 2. Core Functional Requirements\n- Secure JWT Cryptographic Token Validation.\n- Real-time event log tracking framework.\n- Fluid UI/UX state management interface.\n"""
    return {"proposal": proposal}

@app.post("/forgot-password")
async def forgot_password(data: ForgotPasswordSchema):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND phone = ?", (data.username, data.phone)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found with these credentials")
    
    hashed_pw = get_password_hash(data.new_password)
    conn.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_pw, user['id']))
    conn.commit()
    conn.close()
    return {"message": "Password updated successfully"}