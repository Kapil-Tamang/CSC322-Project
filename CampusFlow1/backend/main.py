"""
CampusFlow / College0 Backend
Tech used: FastAPI + SQLite.
Run:
    cd backend
    python3 -m pip install -r requirements.txt
    python3 main.py
Then open:
    http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import hashlib
import secrets
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "campusflow.db")
TOKENS = {}
PROGRAM_QUOTA = 10

app = FastAPI(title="CampusFlow API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def rows(cur):
    return [dict(r) for r in cur.fetchall()]

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        name TEXT,
        password_hash TEXT,
        role TEXT,
        status TEXT DEFAULT 'active',
        must_change_password INTEGER DEFAULT 0,
        warnings INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        student_id TEXT UNIQUE,
        gpa REAL,
        semester_gpa REAL,
        completed_courses INTEGER,
        honor_roll INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS instructors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        department TEXT,
        assigned_courses TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS courses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        title TEXT,
        instructor_user_id INTEGER,
        schedule TEXT,
        capacity INTEGER,
        credits INTEGER,
        status TEXT DEFAULT 'active',
        cancelled INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS enrollments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_user_id INTEGER,
        course_id INTEGER,
        status TEXT,
        grade TEXT,
        FOREIGN KEY(student_user_id) REFERENCES users(id),
        FOREIGN KEY(course_id) REFERENCES courses(id)
    );

    CREATE TABLE IF NOT EXISTS reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_user_id INTEGER,
        course_id INTEGER,
        stars INTEGER,
        review_text TEXT,
        visible INTEGER DEFAULT 1,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS applications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT,
        requested_role TEXT,
        gpa REAL,
        statement TEXT,
        status TEXT DEFAULT 'pending',
        decision_reason TEXT DEFAULT '',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS complaints(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submitted_by INTEGER,
        target_username TEXT,
        complaint_type TEXT,
        description TEXT,
        status TEXT DEFAULT 'open',
        resolution TEXT DEFAULT '',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS semester(
        id INTEGER PRIMARY KEY CHECK(id=1),
        phase TEXT
    );

    CREATE TABLE IF NOT EXISTS knowledge_base(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT,
        answer TEXT
    );
    """)

    c.execute("INSERT OR IGNORE INTO semester(id, phase) VALUES(1, 'course registration period')")
    conn.commit()
    conn.close()

def seed():
    conn = db()
    c = conn.cursor()
    existing = c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    if existing:
        conn.close()
        return

    def add_user(username, name, password, role, warnings=0, status="active"):
        c.execute(
            "INSERT INTO users(username,name,password_hash,role,warnings,status) VALUES(?,?,?,?,?,?)",
            (username, name, hash_password(password), role, warnings, status)
        )
        return c.lastrowid

    registrar = add_user("registrar", "Registrar Admin", "registrar123", "registrar")
    inst1 = add_user("prof_chen", "Prof. Chen", "pass123", "instructor")
    inst2 = add_user("prof_rahman", "Prof. Rahman", "pass123", "instructor")

    c.execute("INSERT INTO instructors(user_id, department, assigned_courses) VALUES(?,?,?)", (inst1, "Computer Science", "CS301,CS330"))
    c.execute("INSERT INTO instructors(user_id, department, assigned_courses) VALUES(?,?,?)", (inst2, "Mathematics", "MATH201"))

    student_data = [
        ("S1001", "Jane Smith", 3.72, 3.82, 6, 0),
        ("S1002", "Alex Turner", 3.91, 3.95, 8, 0),
        ("S1003", "Mia Chen", 2.15, 2.10, 4, 1),
        ("S1004", "Ryan Park", 1.85, 1.90, 3, 2),
        ("S1005", "Leo Sanchez", 3.40, 3.35, 5, 0),
        ("S1006", "Sophia Wong", 3.10, 3.20, 5, 0),
        ("S1007", "Noah Patel", 2.60, 2.70, 3, 0),
        ("S1008", "Emma Davis", 3.80, 3.88, 7, 0),
        ("S1009", "Omar Ali", 2.05, 2.05, 4, 1),
        ("S1010", "Ava Brown", 3.55, 3.60, 6, 0),
    ]

    for sid, name, gpa, sem_gpa, completed, warnings in student_data:
        uid = add_user(sid, name, "pass123", "student", warnings=warnings)
        honor = 1 if sem_gpa > 3.75 or gpa > 3.5 else 0
        c.execute(
            "INSERT INTO students(user_id,student_id,gpa,semester_gpa,completed_courses,honor_roll) VALUES(?,?,?,?,?,?)",
            (uid, sid, gpa, sem_gpa, completed, honor)
        )

    courses = [
        ("CS301", "Data Structures", inst1, "Mon/Wed 10:00-11:15", 4, 3),
        ("CS330", "Database Systems", inst1, "Tue/Thu 3:00-4:15", 3, 3),
        ("MATH201", "Calculus II", inst2, "Tue/Thu 1:00-2:15", 3, 3),
        ("ENG102", "Technical Writing", inst2, "Fri 9:00-11:45", 5, 3),
        ("AI210", "AI for Campus Systems", inst1, "Mon/Wed 2:00-3:15", 3, 3),
    ]
    for code, title, instructor, schedule, capacity, credits in courses:
        c.execute(
            "INSERT INTO courses(code,title,instructor_user_id,schedule,capacity,credits) VALUES(?,?,?,?,?,?)",
            (code, title, instructor, schedule, capacity, credits)
        )

    # Enrollments and grades
    course_ids = {r["code"]: r["id"] for r in c.execute("SELECT id,code FROM courses")}
    student_ids = {r["username"]: r["id"] for r in c.execute("SELECT id,username FROM users WHERE role='student'")}
    enroll_seed = [
        ("S1001", "CS301", "enrolled", ""),
        ("S1001", "MATH201", "enrolled", ""),
        ("S1001", "ENG102", "enrolled", ""),
        ("S1002", "CS301", "enrolled", "A"),
        ("S1002", "CS330", "enrolled", "A"),
        ("S1003", "MATH201", "enrolled", "C"),
        ("S1004", "CS330", "waitlist", ""),
        ("S1005", "AI210", "enrolled", ""),
        ("S1006", "AI210", "enrolled", ""),
        ("S1007", "ENG102", "enrolled", ""),
    ]
    for student, course, status, grade in enroll_seed:
        c.execute(
            "INSERT INTO enrollments(student_user_id,course_id,status,grade) VALUES(?,?,?,?)",
            (student_ids[student], course_ids[course], status, grade)
        )

    reviews = [
        ("S1002", "CS301", 5, "Excellent professor and useful class.", 1),
        ("S1003", "MATH201", 2, "The class was difficult but fair.", 1),
        ("S1001", "ENG102", 4, "Helpful writing practice.", 1),
    ]
    for student, course, stars, text, visible in reviews:
        c.execute(
            "INSERT INTO reviews(student_user_id,course_id,stars,review_text,visible,created_at) VALUES(?,?,?,?,?,?)",
            (student_ids[student], course_ids[course], stars, text, visible, datetime.now().isoformat())
        )

    c.execute("INSERT INTO applications(name,username,requested_role,gpa,statement,status,created_at) VALUES(?,?,?,?,?,?,?)",
              ("Jordan Lee", "S1011", "student", 3.4, "I want to join CampusFlow.", "pending", datetime.now().isoformat()))
    c.execute("INSERT INTO applications(name,username,requested_role,gpa,statement,status,created_at) VALUES(?,?,?,?,?,?,?)",
              ("Taylor Kim", "prof_kim", "instructor", 0, "Database instructor applicant.", "pending", datetime.now().isoformat()))

    kb = [
        ("register", "Students can register for 2 to 4 courses during the course registration period if there is no time conflict and the class is not full."),
        ("graduation", "Students may apply for graduation after completing 8 classes. The registrar verifies all required courses before approval."),
        ("complaint", "Students and instructors can file complaints. The registrar investigates and may issue warnings or dismiss the complaint."),
        ("review", "Students enrolled in a class may rate it 1 to 5 stars. Taboo words are filtered, and severe violations are hidden."),
        ("semester", "The semester has four phases: class set-up, course registration, class running, and grading."),
        ("honor", "Students with semester GPA above 3.75 or overall GPA above 3.5 are labeled honor roll."),
        ("warning", "Students who receive 3 warnings are suspended for one semester and must pay a fine.")
    ]
    for k, a in kb:
        c.execute("INSERT INTO knowledge_base(keyword,answer) VALUES(?,?)", (k, a))

    conn.commit()
    conn.close()

def current_user(authorization: str | None):
    if not authorization:
        raise HTTPException(401, "Missing authorization token")
    token = authorization.replace("Bearer ", "")
    uid = TOKENS.get(token)
    if not uid:
        raise HTTPException(401, "Invalid token")
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(401, "User not found")
    return dict(user)

def require_role(user, roles):
    if user["role"] not in roles:
        raise HTTPException(403, "You do not have permission for this action")

def get_phase():
    conn = db()
    phase = conn.execute("SELECT phase FROM semester WHERE id=1").fetchone()["phase"]
    conn.close()
    return phase

def course_average(course_id):
    conn = db()
    r = conn.execute("SELECT AVG(stars) AS avg_rating, COUNT(*) AS count_reviews FROM reviews WHERE course_id=? AND visible=1", (course_id,)).fetchone()
    conn.close()
    return round(r["avg_rating"] or 0, 2), r["count_reviews"]

def grade_points(letter):
    return {"A":4.0, "A-":3.7, "B+":3.3, "B":3.0, "B-":2.7, "C":2.0, "D":1.0, "F":0.0}.get(letter, None)

class LoginIn(BaseModel):
    username: str
    password: str

class ApplicationIn(BaseModel):
    name: str
    username: str
    requested_role: str
    gpa: float = 0
    statement: str = ""

class DecisionIn(BaseModel):
    decision: str
    reason: str = ""

class CourseIn(BaseModel):
    code: str
    title: str
    instructor_username: str
    schedule: str
    capacity: int = 3
    credits: int = 3

class EnrollIn(BaseModel):
    course_id: int

class ReviewIn(BaseModel):
    course_id: int
    stars: int
    review_text: str

class GradeIn(BaseModel):
    enrollment_id: int
    grade: str

class ComplaintIn(BaseModel):
    target_username: str
    complaint_type: str
    description: str

class ComplaintDecisionIn(BaseModel):
    complaint_id: int
    action: str
    resolution: str = ""

class PhaseIn(BaseModel):
    phase: str

class ChatIn(BaseModel):
    question: str

@app.on_event("startup")
def startup():
    init_db()
    seed()

@app.get("/")
def root():
    return {"app": "CampusFlow API", "version": "2.0.0", "docs": "/docs", "frontend": "http://127.0.0.1:5173"}

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/auth/login")
def login(data: LoginIn):
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (data.username,)).fetchone()
    conn.close()
    if not user or user["password_hash"] != hash_password(data.password):
        raise HTTPException(401, "Login failed")
    if user["status"] in ("suspended", "terminated", "closed"):
        raise HTTPException(403, f"Account is {user['status']}")
    token = secrets.token_hex(16)
    TOKENS[token] = user["id"]
    return {"token": token, "user": {k:user[k] for k in user.keys() if k != "password_hash"}}

@app.get("/api/me")
def me(authorization: str | None = Header(None)):
    return current_user(authorization)

@app.get("/api/public/overview")
def public_overview():
    conn = db()
    total_students = conn.execute("SELECT COUNT(*) AS n FROM students").fetchone()["n"]
    total_courses = conn.execute("SELECT COUNT(*) AS n FROM courses").fetchone()["n"]
    phase = conn.execute("SELECT phase FROM semester WHERE id=1").fetchone()["phase"]
    conn.close()
    return {
        "program": "CampusFlow / College0 Graduate Program",
        "introduction": "An AI-enabled online college program management system for registrars, instructors, students, and visitors.",
        "semester_phase": phase,
        "total_students": total_students,
        "total_courses": total_courses,
        "creative_feature": "Smart academic risk dashboard with AI assistant and automatic rule checks."
    }

@app.get("/api/public/courses")
def public_courses():
    conn = db()
    course_rows = rows(conn.execute("""
        SELECT c.*, u.name AS instructor_name
        FROM courses c LEFT JOIN users u ON c.instructor_user_id = u.id
    """))
    conn.close()
    for c in course_rows:
        avg, count = course_average(c["id"])
        c["avg_rating"] = avg
        c["review_count"] = count
    return course_rows

@app.get("/api/public/top-students")
def top_students():
    conn = db()
    result = rows(conn.execute("""
        SELECT users.name, students.student_id, students.gpa, students.semester_gpa, students.completed_courses, students.honor_roll
        FROM students JOIN users ON students.user_id=users.id
        ORDER BY students.gpa DESC LIMIT 5
    """))
    conn.close()
    return result

@app.get("/api/applications")
def list_applications(authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["registrar"])
    conn = db()
    result = rows(conn.execute("SELECT * FROM applications ORDER BY id DESC"))
    conn.close()
    return result

@app.post("/api/applications")
def submit_application(data: ApplicationIn):
    conn = db()
    if conn.execute("SELECT 1 FROM users WHERE username=?", (data.username,)).fetchone():
        conn.close()
        raise HTTPException(400, "Username already exists")
    if conn.execute("SELECT 1 FROM applications WHERE username=? AND status='pending'", (data.username,)).fetchone():
        conn.close()
        raise HTTPException(400, "Application already pending")
    conn.execute(
        "INSERT INTO applications(name,username,requested_role,gpa,statement,created_at) VALUES(?,?,?,?,?,?)",
        (data.name, data.username, data.requested_role.lower(), data.gpa, data.statement, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return {"message": "Application submitted and pending registrar review."}

@app.post("/api/applications/{app_id}/decision")
def decide_application(app_id: int, data: DecisionIn, authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["registrar"])
    conn = db()
    app_row = conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
    if not app_row:
        conn.close()
        raise HTTPException(404, "Application not found")

    decision = data.decision.lower()
    if decision not in ("approved", "rejected"):
        conn.close()
        raise HTTPException(400, "Decision must be approved or rejected")

    reason = data.reason
    if app_row["requested_role"] == "student":
        current_students = conn.execute("SELECT COUNT(*) AS n FROM students").fetchone()["n"]
        rule_accept = app_row["gpa"] > 3.0 and current_students < PROGRAM_QUOTA
        if decision == "rejected" and rule_accept and not reason:
            conn.close()
            raise HTTPException(400, "Registrar must justify rejecting a student who meets GPA/quota rule.")
        if decision == "approved" and not rule_accept and not reason:
            reason = "Rejected by rule: GPA must be > 3.0 and quota must not be reached."

    conn.execute("UPDATE applications SET status=?, decision_reason=? WHERE id=?", (decision, reason, app_id))

    if decision == "approved":
        uid = conn.execute(
            "INSERT INTO users(username,name,password_hash,role,must_change_password) VALUES(?,?,?,?,1)",
            (app_row["username"], app_row["name"], hash_password("changeme123"), app_row["requested_role"])
        ).lastrowid
        if app_row["requested_role"] == "student":
            student_id = app_row["username"]
            conn.execute("INSERT INTO students(user_id,student_id,gpa,semester_gpa,completed_courses) VALUES(?,?,?,?,0)",
                         (uid, student_id, app_row["gpa"], app_row["gpa"]))
        elif app_row["requested_role"] == "instructor":
            conn.execute("INSERT INTO instructors(user_id,department,assigned_courses) VALUES(?,?,?)", (uid, "Unassigned", ""))

    conn.commit()
    conn.close()
    return {"message": f"Application {decision}.", "temporary_password": "changeme123" if decision == "approved" else None}

@app.get("/api/semester")
def semester():
    return {"phase": get_phase(), "periods": ["class set-up period", "course registration period", "class running period", "grading period"]}

@app.post("/api/semester")
def set_semester(data: PhaseIn, authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["registrar"])
    if data.phase not in ["class set-up period", "course registration period", "class running period", "grading period", "special registration period"]:
        raise HTTPException(400, "Invalid semester phase")
    conn = db()
    conn.execute("UPDATE semester SET phase=? WHERE id=1", (data.phase,))
    conn.commit()
    conn.close()
    return {"message": "Semester phase updated.", "phase": data.phase}

@app.post("/api/courses")
def create_course(data: CourseIn, authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["registrar"])
    if get_phase() != "class set-up period":
        raise HTTPException(400, "Courses can be created only during class set-up period.")
    conn = db()
    inst = conn.execute("SELECT id FROM users WHERE username=? AND role='instructor'", (data.instructor_username,)).fetchone()
    if not inst:
        conn.close()
        raise HTTPException(404, "Instructor not found")
    conn.execute("INSERT INTO courses(code,title,instructor_user_id,schedule,capacity,credits) VALUES(?,?,?,?,?,?)",
                 (data.code, data.title, inst["id"], data.schedule, data.capacity, data.credits))
    conn.commit()
    conn.close()
    return {"message": "Course created."}

@app.post("/api/enrollments")
def enroll(data: EnrollIn, authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["student"])
    phase = get_phase()
    if phase not in ("course registration period", "special registration period"):
        raise HTTPException(400, "Registration is closed during the current semester phase.")
    conn = db()
    enrolled = rows(conn.execute("SELECT * FROM enrollments WHERE student_user_id=? AND status='enrolled'", (user["id"],)))
    if len(enrolled) >= 4:
        conn.close()
        raise HTTPException(400, "Students can register for at most 4 courses.")

    target = conn.execute("SELECT * FROM courses WHERE id=?", (data.course_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(404, "Course not found")

    # Retake rule: allow retake only if previous grade was F or no prior completed grade.
    prior = conn.execute("SELECT * FROM enrollments WHERE student_user_id=? AND course_id=? AND grade!=''", (user["id"], data.course_id)).fetchone()
    if prior and prior["grade"] != "F":
        conn.close()
        raise HTTPException(400, "Student may retake a class only if the previous grade was F.")

    for enr in enrolled:
        c = conn.execute("SELECT schedule FROM courses WHERE id=?", (enr["course_id"],)).fetchone()
        if c and c["schedule"] == target["schedule"]:
            conn.close()
            raise HTTPException(400, "Time conflict with another enrolled course.")

    count = conn.execute("SELECT COUNT(*) AS n FROM enrollments WHERE course_id=? AND status='enrolled'", (data.course_id,)).fetchone()["n"]
    status = "waitlist" if count >= target["capacity"] else "enrolled"
    conn.execute("INSERT INTO enrollments(student_user_id,course_id,status) VALUES(?,?,?)", (user["id"], data.course_id, status))
    conn.commit()
    conn.close()
    return {"message": f"Enrollment status: {status}", "status": status}

@app.get("/api/enrollments/mine")
def my_enrollments(authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["student"])
    conn = db()
    result = rows(conn.execute("""
        SELECT e.id, e.status, e.grade, c.code, c.title, c.schedule, c.credits
        FROM enrollments e JOIN courses c ON e.course_id=c.id
        WHERE e.student_user_id=?
    """, (user["id"],)))
    conn.close()
    return result

@app.get("/api/instructor/roster")
def instructor_roster(authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["instructor"])
    conn = db()
    result = rows(conn.execute("""
        SELECT e.id AS enrollment_id, c.code, c.title, u.name AS student_name, u.username, s.gpa, s.completed_courses, e.status, e.grade
        FROM enrollments e
        JOIN courses c ON e.course_id=c.id
        JOIN users u ON e.student_user_id=u.id
        JOIN students s ON s.user_id=u.id
        WHERE c.instructor_user_id=?
        ORDER BY c.code, u.name
    """, (user["id"],)))
    conn.close()
    return result

@app.post("/api/grades")
def submit_grade(data: GradeIn, authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["instructor"])
    if get_phase() != "grading period":
        raise HTTPException(400, "Grades can be submitted only during grading period.")
    if data.grade not in ["A", "A-", "B+", "B", "B-", "C", "D", "F"]:
        raise HTTPException(400, "Invalid grade")
    conn = db()
    enrollment = conn.execute("""
        SELECT e.*, c.instructor_user_id FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE e.id=?
    """, (data.enrollment_id,)).fetchone()
    if not enrollment or enrollment["instructor_user_id"] != user["id"]:
        conn.close()
        raise HTTPException(403, "You can grade only your assigned students.")
    conn.execute("UPDATE enrollments SET grade=? WHERE id=?", (data.grade, data.enrollment_id))
    conn.commit()
    conn.close()
    return {"message": "Grade submitted."}

@app.post("/api/reviews")
def submit_review(data: ReviewIn, authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["student"])
    if data.stars < 1 or data.stars > 5:
        raise HTTPException(400, "Stars must be 1 to 5.")

    conn = db()
    enrollment = conn.execute("SELECT * FROM enrollments WHERE student_user_id=? AND course_id=? AND status='enrolled'",
                              (user["id"], data.course_id)).fetchone()
    if not enrollment:
        conn.close()
        raise HTTPException(403, "Only students enrolled in the class can review it.")
    if enrollment["grade"]:
        conn.close()
        raise HTTPException(400, "You cannot review after the instructor posts the grade.")

    taboo_words = ["stupid", "hate", "badword", "trash", "idiot"]
    text = data.review_text
    count = 0
    for word in taboo_words:
        while word.lower() in text.lower():
            count += 1
            idx = text.lower().find(word.lower())
            text = text[:idx] + ("*" * len(word)) + text[idx+len(word):]

    visible = 0 if count >= 3 else 1
    warning_add = 2 if count >= 3 else (1 if count >= 1 else 0)
    if warning_add:
        conn.execute("UPDATE users SET warnings=warnings+? WHERE id=?", (warning_add, user["id"]))

    conn.execute("INSERT INTO reviews(student_user_id,course_id,stars,review_text,visible,created_at) VALUES(?,?,?,?,?,?)",
                 (user["id"], data.course_id, data.stars, text, visible, datetime.now().isoformat()))

    avg, _ = course_average(data.course_id)
    course = conn.execute("SELECT instructor_user_id FROM courses WHERE id=?", (data.course_id,)).fetchone()
    if avg and avg < 2 and course:
        conn.execute("UPDATE users SET warnings=warnings+1 WHERE id=?", (course["instructor_user_id"],))

    conn.commit()
    conn.close()
    return {"message": "Review submitted." if visible else "Review hidden because it has 3 or more taboo words.", "filtered_review": text, "warnings_added": warning_add}

@app.get("/api/complaints")
def list_complaints(authorization: str | None = Header(None)):
    user = current_user(authorization)
    conn = db()
    if user["role"] == "registrar":
        result = rows(conn.execute("SELECT * FROM complaints ORDER BY id DESC"))
    else:
        result = rows(conn.execute("SELECT * FROM complaints WHERE submitted_by=? ORDER BY id DESC", (user["id"],)))
    conn.close()
    return result

@app.post("/api/complaints")
def submit_complaint(data: ComplaintIn, authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["student", "instructor"])
    conn = db()
    target = conn.execute("SELECT * FROM users WHERE username=?", (data.target_username,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(404, "Target user not found")
    conn.execute("INSERT INTO complaints(submitted_by,target_username,complaint_type,description,created_at) VALUES(?,?,?,?,?)",
                 (user["id"], data.target_username, data.complaint_type, data.description, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return {"message": "Complaint submitted for registrar review."}

@app.post("/api/complaints/decision")
def decide_complaint(data: ComplaintDecisionIn, authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["registrar"])
    conn = db()
    complaint = conn.execute("SELECT * FROM complaints WHERE id=?", (data.complaint_id,)).fetchone()
    if not complaint:
        conn.close()
        raise HTTPException(404, "Complaint not found")

    if data.action == "warn_target":
        target = conn.execute("SELECT * FROM users WHERE username=?", (complaint["target_username"],)).fetchone()
        if target:
            conn.execute("UPDATE users SET warnings=warnings+1 WHERE id=?", (target["id"],))
            updated = conn.execute("SELECT warnings, role FROM users WHERE id=?", (target["id"],)).fetchone()
            if updated["role"] == "student" and updated["warnings"] >= 3:
                conn.execute("UPDATE users SET status='suspended' WHERE id=?", (target["id"],))
    elif data.action == "warn_submitter":
        conn.execute("UPDATE users SET warnings=warnings+1 WHERE id=?", (complaint["submitted_by"],))

    conn.execute("UPDATE complaints SET status='resolved', resolution=? WHERE id=?", (data.resolution or data.action, data.complaint_id))
    conn.commit()
    conn.close()
    return {"message": "Complaint processed."}

@app.post("/api/rules/run-class-running-check")
def class_running_check(authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["registrar"])
    if get_phase() != "class running period":
        raise HTTPException(400, "This check is for class running period.")

    conn = db()
    warnings = []
    for s in rows(conn.execute("SELECT u.id, u.name FROM users u WHERE u.role='student'")):
        count = conn.execute("SELECT COUNT(*) AS n FROM enrollments WHERE student_user_id=? AND status='enrolled'", (s["id"],)).fetchone()["n"]
        if count < 2:
            conn.execute("UPDATE users SET warnings=warnings+1 WHERE id=?", (s["id"],))
            warnings.append(f"{s['name']} warned for fewer than 2 courses.")
    for c in rows(conn.execute("SELECT id, title, instructor_user_id FROM courses")):
        count = conn.execute("SELECT COUNT(*) AS n FROM enrollments WHERE course_id=? AND status='enrolled'", (c["id"],)).fetchone()["n"]
        if count < 3:
            conn.execute("UPDATE courses SET cancelled=1, status='cancelled' WHERE id=?", (c["id"],))
            conn.execute("UPDATE users SET warnings=warnings+1 WHERE id=?", (c["instructor_user_id"],))
            warnings.append(f"{c['title']} cancelled for fewer than 3 students; instructor warned.")
    conn.commit()
    conn.close()
    return {"message": "Class running check complete.", "results": warnings}

@app.get("/api/academic-record")
def academic_record(authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["student"])
    conn = db()
    record = conn.execute("SELECT * FROM students WHERE user_id=?", (user["id"],)).fetchone()
    enrollments = rows(conn.execute("""
        SELECT c.code, c.title, e.status, e.grade FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE e.student_user_id=?
    """, (user["id"],)))
    conn.close()
    return {"student": dict(record), "enrollments": enrollments, "tutorial": "Use the dashboard to register for courses, view grades, submit reviews, file complaints, and apply for graduation."}

@app.post("/api/graduation/apply")
def apply_graduation(authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["student"])
    conn = db()
    st = conn.execute("SELECT * FROM students WHERE user_id=?", (user["id"],)).fetchone()
    if st["completed_courses"] >= 8:
        message = "Graduation request approved for registrar final verification. Student will receive Bachelor's degree after approval."
    else:
        conn.execute("UPDATE users SET warnings=warnings+1 WHERE id=?", (user["id"],))
        message = "Graduation request denied. Reckless graduation application warning added."
    conn.commit()
    conn.close()
    return {"message": message}

@app.get("/api/admin/dashboard")
def admin_dashboard(authorization: str | None = Header(None)):
    user = current_user(authorization)
    require_role(user, ["registrar"])
    conn = db()
    all_users = rows(conn.execute("SELECT id, username, name, role, status, warnings FROM users ORDER BY role, username"))
    all_courses = public_courses()
    apps = rows(conn.execute("SELECT * FROM applications ORDER BY id DESC"))
    complaints = rows(conn.execute("SELECT * FROM complaints ORDER BY id DESC"))
    conn.close()
    return {"users": all_users, "courses": all_courses, "applications": apps, "complaints": complaints, "phase": get_phase()}

@app.post("/api/chat")
def chat(data: ChatIn, authorization: str | None = Header(None)):
    user = None
    if authorization:
        try:
            user = current_user(authorization)
        except Exception:
            user = None

    q = data.question.lower()
    conn = db()
    answers = rows(conn.execute("SELECT keyword, answer FROM knowledge_base"))
    conn.close()

    for row in answers:
        if row["keyword"] in q:
            extra = ""
            if user and user["role"] == "student":
                extra = " Since you are a student, check your dashboard for your own schedule, GPA, and graduation status."
            elif user and user["role"] == "instructor":
                extra = " Since you are an instructor, use your roster page for students in your assigned classes."
            elif user and user["role"] == "registrar":
                extra = " Since you are registrar, you can manage this from the admin dashboard."
            return {"source": "local knowledge base", "answer": row["answer"] + extra}

    return {
        "source": "external LLM fallback simulation",
        "answer": "No exact local knowledge-base match was found. A real system would send this to an external LLM. Warning: this answer may contain hallucinations."
    }
# ============================================================
# Requirement 6: Grading Period, GPA Rules, Honor Roll,
# Graduation, Warnings, and Termination
# ============================================================

class GradeIn(BaseModel):
    enrollment_id: int
    grade: str


def grade_to_points(letter_grade):
    """
    Converts a letter grade into GPA points.
    """
    points = {
        "A": 4.0,
        "A-": 3.7,
        "B+": 3.3,
        "B": 3.0,
        "B-": 2.7,
        "C+": 2.3,
        "C": 2.0,
        "D": 1.0,
        "F": 0.0,
    }

    return points.get(letter_grade)


def recalculate_student_gpa(student_user_id):
    """
    Recalculates a student's GPA from all posted grades.
    This also updates honor roll, warning, and termination rules.
    """

    conn = db()

    graded_rows = conn.execute(
        """
        SELECT grade
        FROM enrollments
        WHERE student_user_id = ?
        AND grade IS NOT NULL
        AND grade != ''
        """,
        (student_user_id,),
    ).fetchall()

    grade_values = []

    for row in graded_rows:
        points = grade_to_points(row["grade"])

        if points is not None:
            grade_values.append(points)

    if len(grade_values) == 0:
        conn.close()
        return None

    new_gpa = round(sum(grade_values) / len(grade_values), 2)

    completed_courses = len(grade_values)

    honor_roll = 1 if new_gpa > 3.5 else 0

    conn.execute(
        """
        UPDATE students
        SET gpa = ?,
            semester_gpa = ?,
            completed_courses = ?,
            honor_roll = ?
        WHERE user_id = ?
        """,
        (new_gpa, new_gpa, completed_courses, honor_roll, student_user_id),
    )

    # GPA below 2.0 means automatic termination.
    if new_gpa < 2.0:
        conn.execute(
            """
            UPDATE users
            SET status = 'terminated'
            WHERE id = ?
            """,
            (student_user_id,),
        )

    # GPA between 2.0 and 2.25 means warning/interview required.
    elif 2.0 <= new_gpa <= 2.25:
        conn.execute(
            """
            UPDATE users
            SET warnings = warnings + 1
            WHERE id = ?
            """,
            (student_user_id,),
        )

    # Honor roll can remove one warning.
    elif honor_roll == 1:
        conn.execute(
            """
            UPDATE users
            SET warnings = CASE
                WHEN warnings > 0 THEN warnings - 1
                ELSE 0
            END
            WHERE id = ?
            """,
            (student_user_id,),
        )

    conn.commit()
    conn.close()

    return new_gpa


@app.post("/api/grades")
def submit_grade(data: GradeIn, authorization: str | None = Header(None)):
    """
    Instructor assigns a grade during the grading period.
    """

    user = current_user(authorization)
    require_role(user, ["instructor"])

    phase = get_phase()

    if phase != "grading period":
        raise HTTPException(
            status_code=400,
            detail="Grades can only be submitted during the grading period."
        )

    if data.grade not in ["A", "A-", "B+", "B", "B-", "C+", "C", "D", "F"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid grade. Use A, A-, B+, B, B-, C+, C, D, or F."
        )

    conn = db()

    enrollment = conn.execute(
        """
        SELECT e.id,
               e.student_user_id,
               e.course_id,
               c.instructor_user_id
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        WHERE e.id = ?
        """,
        (data.enrollment_id,),
    ).fetchone()

    if not enrollment:
        conn.close()
        raise HTTPException(status_code=404, detail="Enrollment not found.")

    if enrollment["instructor_user_id"] != user["id"]:
        conn.close()
        raise HTTPException(
            status_code=403,
            detail="You can only grade students in your own assigned classes."
        )

    conn.execute(
        """
        UPDATE enrollments
        SET grade = ?
        WHERE id = ?
        """,
        (data.grade, data.enrollment_id),
    )

    conn.commit()
    conn.close()

    new_gpa = recalculate_student_gpa(enrollment["student_user_id"])

    return {
        "message": "Grade submitted successfully.",
        "new_student_gpa": new_gpa
    }


@app.post("/api/rules/grading-period-check")
def grading_period_check(authorization: str | None = Header(None)):
    """
    Registrar runs grading-period checks after grading period ends.
    This checks:
    - instructors who did not assign all grades
    - class GPA above 3.5 or below 2.5
    - students below GPA rules
    """

    user = current_user(authorization)
    require_role(user, ["registrar"])

    conn = db()
    results = []

    courses = conn.execute(
        """
        SELECT id, title, instructor_user_id
        FROM courses
        """
    ).fetchall()

    for course in courses:
        enrollments = conn.execute(
            """
            SELECT grade
            FROM enrollments
            WHERE course_id = ?
            AND status = 'enrolled'
            """,
            (course["id"],),
        ).fetchall()

        if len(enrollments) == 0:
            continue

        missing_grades = 0
        grade_points_list = []

        for enrollment in enrollments:
            if enrollment["grade"] is None or enrollment["grade"] == "":
                missing_grades += 1
            else:
                points = grade_to_points(enrollment["grade"])

                if points is not None:
                    grade_points_list.append(points)

        if missing_grades > 0:
            conn.execute(
                """
                UPDATE users
                SET warnings = warnings + 1
                WHERE id = ?
                """,
                (course["instructor_user_id"],),
            )

            results.append(
                f"Instructor warned because {course['title']} has missing grades."
            )

        if len(grade_points_list) > 0:
            class_gpa = round(sum(grade_points_list) / len(grade_points_list), 2)

            if class_gpa > 3.5 or class_gpa < 2.5:
                conn.execute(
                    """
                    UPDATE users
                    SET warnings = warnings + 1
                    WHERE id = ?
                    """,
                    (course["instructor_user_id"],),
                )

                results.append(
                    f"Instructor questioned/warned because {course['title']} class GPA is {class_gpa}."
                )

    students = conn.execute(
        """
        SELECT users.id, users.name, students.gpa
        FROM students
        JOIN users ON students.user_id = users.id
        """
    ).fetchall()

    for student in students:
        if student["gpa"] < 2.0:
            conn.execute(
                """
                UPDATE users
                SET status = 'terminated'
                WHERE id = ?
                """,
                (student["id"],),
            )

            results.append(
                f"{student['name']} terminated because GPA is below 2.0."
            )

        elif 2.0 <= student["gpa"] <= 2.25:
            conn.execute(
                """
                UPDATE users
                SET warnings = warnings + 1
                WHERE id = ?
                """,
                (student["id"],),
            )

            results.append(
                f"{student['name']} warned and must interview with registrar."
            )

    conn.commit()
    conn.close()

    return {
        "message": "Grading-period rule check completed.",
        "results": results
    }


@app.post("/api/graduation/apply")
def apply_for_graduation(authorization: str | None = Header(None)):
    """
    Student applies for graduation.
    Students need 8 completed classes.
    If not, they receive a warning for reckless graduation application.
    """

    user = current_user(authorization)
    require_role(user, ["student"])

    conn = db()

    student = conn.execute(
        """
        SELECT completed_courses
        FROM students
        WHERE user_id = ?
        """,
        (user["id"],),
    ).fetchone()

    if not student:
        conn.close()
        raise HTTPException(status_code=404, detail="Student record not found.")

    if student["completed_courses"] >= 8:
        conn.close()

        return {
            "message": "Graduation application submitted. Registrar can verify required courses and approve graduation."
        }

    conn.execute(
        """
        UPDATE users
        SET warnings = warnings + 1
        WHERE id = ?
        """,
        (user["id"],),
    )

    conn.commit()
    conn.close()

    return {
        "message": "Graduation denied. You need 8 completed classes. Warning added for reckless graduation application."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
