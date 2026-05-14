"""CampusFlow Backend - demo-complete FastAPI + SQLite app."""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sqlite3, hashlib, secrets, os, re, json
import urllib.request
from datetime import datetime

DB_PATH=os.path.join(os.path.dirname(__file__),'campusflow.db')
TOKENS={}
PROGRAM_QUOTA=10
PHASES=['class set-up period','course registration period','class running period','special registration period','grading period']
GRADES={'A':4.0,'A-':3.7,'B+':3.3,'B':3.0,'B-':2.7,'C+':2.3,'C':2.0,'D':1.0,'F':0.0}
REQUIRED_COURSES=['CS301','CS330','MATH201','ENG102','AI210']
USERNAME_RE=re.compile(r'^[A-Za-z][A-Za-z0-9_]{2,31}$')
COURSE_CODE_RE=re.compile(r'^[A-Z]{2,6}\d{2,4}$')
COMPLAINT_TYPES={'academic','behavior','deregister_request'}

app=FastAPI(title='CampusFlow API',version='3.0 demo-ready')
app.add_middleware(CORSMiddleware,allow_origin_regex=r'^http://(127\.0\.0\.1|localhost):\d+$',allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

def db():
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; return conn

def rows(cur): return [dict(r) for r in cur.fetchall()]
def hpw(p): return hashlib.sha256(p.encode()).hexdigest()
def now(): return datetime.now().isoformat(timespec='seconds')

def init_db():
    conn=db(); c=conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, name TEXT, password_hash TEXT, role TEXT, status TEXT DEFAULT 'active', must_change_password INTEGER DEFAULT 0, warnings INTEGER DEFAULT 0, fine_due REAL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, student_id TEXT UNIQUE, gpa REAL DEFAULT 0, semester_gpa REAL DEFAULT 0, completed_courses INTEGER DEFAULT 0, honor_roll INTEGER DEFAULT 0, semesters_completed INTEGER DEFAULT 1, degree_status TEXT DEFAULT 'active', special_registration INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS instructors(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, department TEXT, assigned_courses TEXT DEFAULT '', suspended_next_semester INTEGER DEFAULT 0, fired INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, title TEXT, instructor_user_id INTEGER, schedule TEXT, capacity INTEGER, credits INTEGER DEFAULT 3, status TEXT DEFAULT 'active', cancelled INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS enrollments(id INTEGER PRIMARY KEY AUTOINCREMENT, student_user_id INTEGER, course_id INTEGER, status TEXT, grade TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY AUTOINCREMENT, student_user_id INTEGER, course_id INTEGER, stars INTEGER, review_text TEXT, visible INTEGER DEFAULT 1, created_at TEXT);
    CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, username TEXT, requested_role TEXT, gpa REAL DEFAULT 0, statement TEXT, status TEXT DEFAULT 'pending', decision_reason TEXT DEFAULT '', temp_password TEXT DEFAULT '', created_at TEXT);
    CREATE TABLE IF NOT EXISTS complaints(id INTEGER PRIMARY KEY AUTOINCREMENT, submitted_by INTEGER, target_username TEXT, complaint_type TEXT, description TEXT, status TEXT DEFAULT 'open', resolution TEXT DEFAULT '', created_at TEXT);
    CREATE TABLE IF NOT EXISTS semester(id INTEGER PRIMARY KEY CHECK(id=1), phase TEXT);
    CREATE TABLE IF NOT EXISTS knowledge_base(id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, answer TEXT);
    CREATE TABLE IF NOT EXISTS taboo_words(id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS graduation_applications(id INTEGER PRIMARY KEY AUTOINCREMENT, student_user_id INTEGER, status TEXT DEFAULT 'pending', missing_requirements TEXT DEFAULT '', created_at TEXT, decision_reason TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS instructor_questions(id INTEGER PRIMARY KEY AUTOINCREMENT, instructor_user_id INTEGER, course_id INTEGER, class_gpa REAL, status TEXT DEFAULT 'open', justification TEXT DEFAULT '', registrar_decision TEXT DEFAULT '', created_at TEXT);
    CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT, created_at TEXT);
    ''')
    # migrations for older DB copies
    for table,col,typ,default in [
        ('users','fine_due','REAL','0'),('applications','temp_password','TEXT',"''"),('students','semesters_completed','INTEGER','1'),('students','degree_status','TEXT',"'active'"),('students','special_registration','INTEGER','0'),('instructors','suspended_next_semester','INTEGER','0'),('instructors','fired','INTEGER','0')]:
        cols=[r['name'] for r in c.execute(f'PRAGMA table_info({table})')]
        if col not in cols: c.execute(f'ALTER TABLE {table} ADD COLUMN {col} {typ} DEFAULT {default}')
    c.execute("INSERT OR IGNORE INTO semester(id,phase) VALUES(1,'course registration period')")
    conn.commit(); conn.close()

def seed():
    conn = db()
    c = conn.cursor()
    if c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']:
        for w in ['stupid', 'hate', 'badword', 'trash', 'idiot']:
            c.execute('INSERT OR IGNORE INTO taboo_words(word) VALUES(?)', (w,))
        conn.commit(); conn.close(); return

    def user(username, name, pw, role, w=0, status='active', must=0):
        c.execute('INSERT INTO users(username,name,password_hash,role,warnings,status,must_change_password) VALUES(?,?,?,?,?,?,?)',
                  (username, name, hpw(pw), role, w, status, must))
        return c.lastrowid

    user('registrar', 'Registrar Admin', 'registrar123', 'registrar')
    inst_chen   = user('prof_chen',   'Prof. Chen',   'pass123', 'instructor')
    inst_rahman = user('prof_rahman', 'Prof. Rahman', 'pass123', 'instructor')
    inst_singh  = user('prof_singh',  'Prof. Singh',  'pass123', 'instructor')
    inst_okafor = user('prof_okafor', 'Prof. Okafor', 'pass123', 'instructor')
    c.execute('INSERT INTO instructors(user_id,department,assigned_courses) VALUES(?,?,?)', (inst_chen,   'Computer Science', 'CS301,CS330,AI210,CS410,CS420'))
    c.execute('INSERT INTO instructors(user_id,department,assigned_courses) VALUES(?,?,?)', (inst_rahman, 'Mathematics',      'MATH201,MATH310,MATH350'))
    c.execute('INSERT INTO instructors(user_id,department,assigned_courses) VALUES(?,?,?)', (inst_singh,  'English',          'ENG102,ENG250,ENG310,HIST500'))
    c.execute('INSERT INTO instructors(user_id,department,assigned_courses) VALUES(?,?,?)', (inst_okafor, 'Engineering',      'EE220,PHYS150'))

    studs = [
        ('S1001', 'Jane Smith',      3.72, 3.82, 6, 0),
        ('S1002', 'Alex Turner',     3.84, 3.95, 8, 0),
        ('S1003', 'Mia Chen',        2.15, 2.10, 4, 1),
        ('S1004', 'Ryan Park',       1.85, 1.90, 3, 2),
        ('S1005', 'Leo Sanchez',     3.40, 3.35, 5, 0),
        ('S1006', 'Sophia Wong',     3.10, 3.20, 5, 0),
        ('S1007', 'Noah Patel',      2.60, 2.70, 3, 0),
        ('S1008', 'Emma Davis',      3.78, 3.88, 8, 0),
        ('S1009', 'Omar Ali',        2.05, 2.05, 4, 1),
        ('S1010', 'Ava Brown',       3.55, 3.60, 6, 0),
        ('S1011', 'Isabella Romero', 3.25, 3.30, 4, 0),
        ('S1012', 'Ethan Nguyen',    3.05, 2.95, 5, 0),
    ]
    stuids = {}
    for sid, name, gpa, sgpa, done, w in studs:
        uid = user(sid, name, 'pass123', 'student', w)
        stuids[sid] = uid
        c.execute('INSERT INTO students(user_id,student_id,gpa,semester_gpa,completed_courses,honor_roll,semesters_completed) VALUES(?,?,?,?,?,?,?)',
                  (uid, sid, gpa, sgpa, done, 1 if sgpa > 3.75 or gpa > 3.5 else 0, 2 if done > 4 else 1))

    courses = [
        # 5 required core
        ('CS301',   'Data Structures',       inst_chen,   'Mon/Wed 10:00-11:15', 5, 3),
        ('CS330',   'Database Systems',      inst_chen,   'Tue/Thu 3:00-4:15',   4, 3),
        ('MATH201', 'Calculus II',           inst_rahman, 'Tue/Thu 1:00-2:15',   5, 4),
        ('ENG102',  'Technical Writing',     inst_singh,  'Fri 9:00-11:45',      6, 3),
        ('AI210',   'AI for Campus Systems', inst_chen,   'Mon/Wed 2:00-3:15',   4, 3),
        # electives
        ('CS410',   'Algorithms',            inst_chen,   'Mon/Wed 12:00-1:15',  4, 3),
        ('CS420',   'Operating Systems',     inst_chen,   'Tue/Thu 9:00-10:15',  4, 3),
        ('MATH310', 'Linear Algebra',        inst_rahman, 'Mon/Wed 9:00-10:15',  5, 3),
        ('MATH350', 'Probability',           inst_rahman, 'Tue/Thu 11:00-12:15', 5, 3),
        ('ENG250',  'Creative Writing',      inst_singh,  'Wed 5:00-7:30',       5, 3),
        ('ENG310',  'Public Speaking',       inst_singh,  'Mon 5:00-7:30',       5, 3),
        ('EE220',   'Circuits I',            inst_okafor, 'Tue/Thu 8:00-9:15',   4, 3),
        ('PHYS150', 'Physics for CS',        inst_okafor, 'Mon/Wed 3:30-4:45',   5, 3),
        ('HIST500', 'Tiny Seminar',          inst_singh,  'Wed 4:00-5:00',       5, 3),
    ]
    courseids = {}
    for code, title, inst, sched, cap, cr in courses:
        c.execute('INSERT INTO courses(code,title,instructor_user_id,schedule,capacity,credits) VALUES(?,?,?,?,?,?)',
                  (code, title, inst, sched, cap, cr))
        courseids[code] = c.lastrowid

    ens = [
        # S1001 — current registrations, no grades yet
        ('S1001', 'CS301', 'enrolled', ''),
        ('S1001', 'MATH201', 'enrolled', ''),
        ('S1001', 'ENG102', 'enrolled', ''),
        # S1002 — graduable: all 5 required + 3 electives graded
        ('S1002', 'CS301', 'enrolled', 'A'),
        ('S1002', 'CS330', 'enrolled', 'A'),
        ('S1002', 'MATH201', 'enrolled', 'A-'),
        ('S1002', 'ENG102', 'enrolled', 'A'),
        ('S1002', 'AI210', 'enrolled', 'A'),
        ('S1002', 'CS410', 'enrolled', 'A'),
        ('S1002', 'MATH310', 'enrolled', 'A-'),
        ('S1002', 'EE220', 'enrolled', 'B+'),
        # S1003 — struggling
        ('S1003', 'MATH201', 'enrolled', 'C'),
        ('S1003', 'ENG102', 'enrolled', ''),
        # S1004 — on waitlist
        ('S1004', 'CS330', 'waitlist', ''),
        # S1005 / S1006 — active in AI track
        ('S1005', 'AI210', 'enrolled', ''),
        ('S1005', 'CS410', 'enrolled', ''),
        ('S1006', 'AI210', 'enrolled', ''),
        # S1007 — only 1 active course (triggers <2-course warning on class running check)
        ('S1007', 'ENG102', 'enrolled', ''),
        # S1008 — also graduable: all required + 3 electives graded
        ('S1008', 'CS301', 'enrolled', 'B+'),
        ('S1008', 'CS330', 'enrolled', 'A-'),
        ('S1008', 'MATH201', 'enrolled', 'A'),
        ('S1008', 'ENG102', 'enrolled', 'B'),
        ('S1008', 'AI210', 'enrolled', 'A-'),
        ('S1008', 'MATH310', 'enrolled', 'B+'),
        ('S1008', 'PHYS150', 'enrolled', 'A'),
        ('S1008', 'CS410', 'enrolled', 'A'),
        # S1009 — failing
        ('S1009', 'CS330', 'enrolled', 'D'),
        # S1010 — small classes (HIST500 will be cancelled by the <3 check)
        ('S1010', 'HIST500', 'enrolled', ''),
        ('S1010', 'ENG250', 'enrolled', ''),
        # S1011 — new student
        ('S1011', 'CS301', 'enrolled', ''),
        # S1012 — solid
        ('S1012', 'MATH201', 'enrolled', 'B+'),
        ('S1012', 'ENG102', 'enrolled', 'A-'),
    ]
    for sid, code, status, grade in ens:
        c.execute('INSERT INTO enrollments(student_user_id,course_id,status,grade) VALUES(?,?,?,?)',
                  (stuids[sid], courseids[code], status, grade))

    reviews = [
        ('S1002', 'CS301',   5, 'Excellent professor and useful class.',     1),
        ('S1003', 'MATH201', 2, 'The class was difficult but fair.',         1),
        ('S1001', 'ENG102',  4, 'Helpful writing practice.',                 1),
        ('S1008', 'CS301',   1, 'The pacing was confusing.',                 1),
        ('S1002', 'MATH310', 5, 'Great class, lots of practice problems.',   1),
        ('S1005', 'AI210',   4, 'Modern syllabus and group projects.',       1),
        ('S1008', 'MATH201', 5, 'Best math class I have taken.',             1),
        ('S1010', 'HIST500', 3, 'Small seminar, decent discussions.',        1),
    ]
    for sid, code, stars, text, vis in reviews:
        c.execute('INSERT INTO reviews(student_user_id,course_id,stars,review_text,visible,created_at) VALUES(?,?,?,?,?,?)',
                  (stuids[sid], courseids[code], stars, text, vis, now()))

    c.execute('INSERT INTO applications(name,username,requested_role,gpa,statement,status,created_at) VALUES(?,?,?,?,?,?,?)',
              ('Jordan Lee', 'S1013', 'student', 3.4, 'I want to join CampusFlow.', 'pending', now()))
    c.execute('INSERT INTO applications(name,username,requested_role,gpa,statement,status,created_at) VALUES(?,?,?,?,?,?,?)',
              ('Taylor Kim', 'prof_kim', 'instructor', 0, 'Database instructor applicant.', 'pending', now()))

    # Knowledge base — multiple keyword variants per topic so the substring matcher catches common phrasings
    kb_entries = [
        ('Students can register for 2 to 4 courses during course registration if there is no time conflict. Full classes place students on a waitlist that only the instructor can approve.',
         ['register', 'registration', 'sign up', 'enroll', 'enrollment', 'signup', 'how to register']),
        ('Students can drop a class during course registration period or special registration period from the Courses page. After grades are posted, classes cannot be dropped.',
         ['drop class', 'unenroll', 'withdraw', 'cancel registration', 'leave class']),
        ('Students may apply for graduation after completing 8 classes including the 5 required core courses. The registrar verifies required courses before approval.',
         ['graduate', 'graduation', 'diploma', 'bachelor', 'finish degree', 'apply for graduation']),
        ('Students and instructors can file complaints. The registrar investigates and may warn, deregister, dismiss, suspend, or fine.',
         ['complaint', 'complaints', 'grievance', 'report someone', 'misconduct', 'file complaint']),
        ('Enrolled students may rate a class 1 to 5 stars before grades are posted. Taboo words are filtered and warnings are applied. Reviews with 3 or more taboo words are hidden.',
         ['review', 'rate', 'rating', 'feedback', 'star rating']),
        ('The semester has class set-up, course registration, class running, special registration after cancellations, and grading.',
         ['semester', 'phase', 'period', 'term', 'class set-up', 'setup']),
        ('Semester GPA above 3.75 or overall GPA above 3.5 after more than one semester creates honor roll status. One honor can remove one warning.',
         ['honor', 'honor roll', 'honors', 'dean']),
        ('Students with 3 warnings are suspended for one semester and owe a $100 registrar fine. Instructors with 3 warnings are suspended for the next semester.',
         ['warning', 'warnings', 'suspend', 'suspension', 'fine', 'suspended']),
        ('GPA is calculated from posted letter grades. GPA below 2.0 causes termination; 2.0 to 2.25 causes a warning and interview; high GPA can create honor roll status.',
         ['gpa', 'grade', 'grades', 'transcript', 'failing', 'letter grade']),
        ('Required courses are CS301, CS330, MATH201, ENG102, and AI210 for the toy Bachelor degree.',
         ['required course', 'required courses', 'requirements', 'must take', 'prerequisite', 'mandatory']),
        ('Approved applicants use temporary password changeme123 and must change it on first login. The change-password screen appears automatically.',
         ['password', 'change password', 'temporary password', 'changeme', 'reset password']),
        ('Full classes place you on the instructor waitlist. Only the instructor can approve a waitlisted student.',
         ['waitlist', 'wait list', 'wait-list', 'full class', 'class is full']),
        ('Reviews are filtered for taboo words. A review with 3 or more taboo words is hidden and the reviewer gets 2 warnings.',
         ['taboo', 'bad word', 'profanity', 'swear']),
        ('CampusFlow lets you apply, register for classes, post reviews, file complaints, and apply for graduation. Use the sidebar to navigate. The visitor page shows top classes and top students.',
         ['help', 'about', 'features', 'overview', 'how does this work', 'campusflow']),
    ]
    for answer, keywords in kb_entries:
        for kw in keywords:
            c.execute('INSERT INTO knowledge_base(keyword,answer) VALUES(?,?)', (kw, answer))

    for w in ['stupid', 'hate', 'badword', 'trash', 'idiot']:
        c.execute('INSERT INTO taboo_words(word) VALUES(?)', (w,))

    conn.commit(); conn.close()

def current_user(auth):
    if not auth: raise HTTPException(401,'Missing authorization token')
    uid=TOKENS.get(auth.replace('Bearer ',''))
    if not uid: raise HTTPException(401,'Invalid token')
    conn=db(); r=conn.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone(); conn.close()
    if not r: raise HTTPException(401,'User not found')
    return dict(r)

def require(user,roles):
    if user['role'] not in roles: raise HTTPException(403,'You do not have permission for this action')

def canonical_phase(value):
    text=(value or '').strip().lower().replace('setup','set-up').replace('class setup','class set-up')
    for ph in PHASES:
        if text==ph:
            return ph
    return None

def phase():
    conn=db(); p=conn.execute('SELECT phase FROM semester WHERE id=1').fetchone()['phase']; conn.close(); return canonical_phase(p) or 'course registration period'

def avg_rating(course_id):
    conn=db(); r=conn.execute('SELECT AVG(stars) a, COUNT(*) n FROM reviews WHERE course_id=? AND visible=1',(course_id,)).fetchone(); conn.close(); return round(r['a'] or 0,2),r['n']

def add_warning(conn, uid, n=1, reason=''):
    conn.execute('UPDATE users SET warnings=warnings+? WHERE id=?',(n,uid))
    u=conn.execute('SELECT role,warnings FROM users WHERE id=?',(uid,)).fetchone()
    if u and u['role']=='student' and u['warnings']>=3:
        conn.execute("UPDATE users SET status='suspended', fine_due=100 WHERE id=?",(uid,))
    if u and u['role']=='instructor' and u['warnings']>=3:
        conn.execute("UPDATE users SET status='suspended' WHERE id=?",(uid,)); conn.execute('UPDATE instructors SET suspended_next_semester=1 WHERE user_id=?',(uid,))

def recalc_student(conn, uid):
    gr=rows(conn.execute("SELECT e.grade,c.code FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE e.student_user_id=? AND e.status='enrolled' AND e.grade!=''",(uid,)))
    vals=[GRADES[g['grade']] for g in gr if g['grade'] in GRADES]
    if not vals: return None
    gpa=round(sum(vals)/len(vals),2); completed=len(vals)
    st=conn.execute('SELECT semesters_completed,honor_roll FROM students WHERE user_id=?',(uid,)).fetchone()
    honor=1 if gpa>3.75 or (st and st['semesters_completed']>1 and gpa>3.5) else 0
    conn.execute('UPDATE students SET gpa=?, semester_gpa=?, completed_courses=?, honor_roll=? WHERE user_id=?',(gpa,gpa,completed,honor,uid))
    # failed same course twice
    fails={}
    for g in gr:
        if g['grade']=='F': fails[g['code']]=fails.get(g['code'],0)+1
    if gpa<2.0 or any(v>=2 for v in fails.values()):
        conn.execute("UPDATE users SET status='terminated' WHERE id=?",(uid,))
    elif 2.0<=gpa<=2.25:
        add_warning(conn,uid,1,'GPA interview')
    elif honor:
        conn.execute('UPDATE users SET warnings=CASE WHEN warnings>0 THEN warnings-1 ELSE 0 END WHERE id=?',(uid,))
    return gpa

class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)
class ApplicationIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=32)
    requested_role: str
    gpa: float = Field(default=0, ge=0, le=4.0)
    statement: str = Field(default='', max_length=2000)
class DecisionIn(BaseModel):
    decision: str
    reason: str = Field(default='', max_length=1000)
class CourseIn(BaseModel):
    code: str = Field(min_length=3, max_length=12)
    title: str = Field(min_length=2, max_length=100)
    instructor_username: str = Field(min_length=3, max_length=32)
    schedule: str = Field(min_length=2, max_length=80)
    capacity: int = Field(default=3, ge=1, le=200)
    credits: int = Field(default=3, ge=1, le=6)
class EnrollIn(BaseModel):
    course_id: int = Field(gt=0)
class ReviewIn(BaseModel):
    course_id: int = Field(gt=0)
    stars: int = Field(ge=1, le=5)
    review_text: str = Field(min_length=1, max_length=1000)
class GradeIn(BaseModel):
    enrollment_id: int = Field(gt=0)
    grade: str
class ComplaintIn(BaseModel):
    target_username: str = Field(min_length=1, max_length=64)
    complaint_type: str
    description: str = Field(min_length=3, max_length=2000)
class ComplaintDecisionIn(BaseModel):
    complaint_id: int = Field(gt=0)
    action: str
    resolution: str = Field(default='', max_length=1000)
class PhaseIn(BaseModel):
    phase: str
class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
class TabooIn(BaseModel):
    word: str = Field(min_length=2, max_length=40)
class JustifyIn(BaseModel):
    question_id: int = Field(gt=0)
    justification: str = Field(min_length=3, max_length=1000)
class RegistrarQuestionDecisionIn(BaseModel):
    question_id: int = Field(gt=0)
    decision: str
    reason: str = Field(default='', max_length=1000)
class WaitlistIn(BaseModel):
    enrollment_id: int = Field(gt=0)
class GraduationDecisionIn(BaseModel):
    application_id: int = Field(gt=0)
    decision: str
    reason: str = Field(default='', max_length=1000)

def ensure_demo_extras():
    conn=db(); c=conn.cursor()
    if c.execute("SELECT 1 FROM users WHERE username='S1020'").fetchone():
        conn.close(); return
    uid=c.execute('INSERT INTO users(username,name,password_hash,role,warnings,status,must_change_password) VALUES(?,?,?,?,?,?,?)',
                  ('S1020','Casey Morgan',hpw('pass123'),'student',0,'active',0)).lastrowid
    c.execute('INSERT INTO students(user_id,student_id,gpa,semester_gpa,completed_courses,honor_roll,semesters_completed) VALUES(?,?,?,?,?,?,?)',
              (uid,'S1020',3.66,3.66,7,0,2))
    plan=[('CS301','A-'),('CS330','B+'),('MATH201','A'),('ENG102','B+'),('CS410','A'),('MATH310','B+'),('PHYS150','A'),('AI210','')]
    for code,grade in plan:
        cid=c.execute('SELECT id FROM courses WHERE code=?',(code,)).fetchone()
        if cid: c.execute('INSERT INTO enrollments(student_user_id,course_id,status,grade) VALUES(?,?,?,?)',(uid,cid['id'],'enrolled',grade))
    conn.commit(); conn.close()

@app.on_event('startup')
def startup(): init_db(); seed(); ensure_demo_extras()
@app.get('/')
def root(): return {'app':'CampusFlow','version':'3.0 demo-ready'}
@app.get('/api/health')
def health(): return {'status':'ok'}

@app.post('/api/auth/login')
def login(data:LoginIn):
    conn=db(); u=conn.execute('SELECT * FROM users WHERE username=?',(data.username,)).fetchone(); conn.close()
    if not u or u['password_hash']!=hpw(data.password): raise HTTPException(401,'Login failed')
    if u['status'] in ['terminated','closed']: raise HTTPException(403,f"Account is {u['status']}")
    tok=secrets.token_hex(16); TOKENS[tok]=u['id']
    d=dict(u); d.pop('password_hash',None); return {'token':tok,'user':d}
@app.get('/api/me')
def me(authorization:str|None=Header(None)):
    u=current_user(authorization); u.pop('password_hash',None); return u
@app.post('/api/auth/change-password')
def change_password(data:ChangePasswordIn, authorization:str|None=Header(None)):
    u=current_user(authorization)
    if u['password_hash']!=hpw(data.old_password): raise HTTPException(400,'Old password is incorrect')
    if len(data.new_password)<6: raise HTTPException(400,'New password must be at least 6 characters')
    conn=db(); conn.execute('UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?',(hpw(data.new_password),u['id'])); conn.commit(); conn.close(); return {'message':'Password changed. Your account is ready.'}

@app.get('/api/public/overview')
def public_overview():
    conn=db(); ts=conn.execute('SELECT COUNT(*) n FROM students').fetchone()['n']; tc=conn.execute('SELECT COUNT(*) n FROM courses').fetchone()['n']; conn.close()
    return {'program':'CampusFlow Graduate Program','introduction':'An AI-enabled college management system for registrars, instructors, students, and visitors. It manages applications, semester phases, registration, waitlists, reviews, grades, warnings, complaints, graduation, and local AI help.','semester_phase':phase(),'total_students':ts,'total_courses':tc}
@app.get('/api/public/courses')
def public_courses():
    conn=db(); out=rows(conn.execute('''SELECT c.*,u.name instructor_name,(SELECT COUNT(*) FROM enrollments e WHERE e.course_id=c.id AND e.status='enrolled') enrolled_count,(SELECT COUNT(*) FROM enrollments e WHERE e.course_id=c.id AND e.status='waitlist') waitlist_count FROM courses c LEFT JOIN users u ON c.instructor_user_id=u.id ORDER BY c.code''')); conn.close()
    for c in out: c['avg_rating'],c['review_count']=avg_rating(c['id'])
    return out
@app.get('/api/public/top-students')
def top_students():
    conn=db(); r=rows(conn.execute('''SELECT u.name,s.student_id,s.gpa,s.semester_gpa,s.completed_courses,s.honor_roll FROM students s JOIN users u ON s.user_id=u.id WHERE u.status!='terminated' ORDER BY s.gpa DESC LIMIT 5''')); conn.close(); return r

@app.post('/api/applications')
def submit_app(data:ApplicationIn):
    role=data.requested_role.lower()
    if role not in ['student','instructor']: raise HTTPException(400,'Role must be student or instructor')
    if not USERNAME_RE.match(data.username): raise HTTPException(400,'Username must start with a letter and contain only letters, digits, or underscore (3-32 chars).')
    if not data.name.strip(): raise HTTPException(400,'Name cannot be blank.')
    conn=db()
    if conn.execute('SELECT 1 FROM users WHERE username=?',(data.username,)).fetchone(): conn.close(); raise HTTPException(400,'Username already exists')
    if conn.execute("SELECT 1 FROM applications WHERE username=? AND status='pending'",(data.username,)).fetchone(): conn.close(); raise HTTPException(400,'Application already pending')
    conn.execute('INSERT INTO applications(name,username,requested_role,gpa,statement,created_at) VALUES(?,?,?,?,?,?)',(data.name.strip(),data.username,role,data.gpa,data.statement,now())); conn.commit(); conn.close(); return {'message':'Application submitted and pending registrar review.'}
@app.get('/api/applications')
def apps(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar']); conn=db(); r=rows(conn.execute('SELECT * FROM applications ORDER BY id DESC')); conn.close(); return r
@app.post('/api/applications/{app_id}/decision')
def decide_app(app_id:int,data:DecisionIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar']); decision=data.decision.lower(); conn=db(); a=conn.execute('SELECT * FROM applications WHERE id=?',(app_id,)).fetchone()
    if not a: conn.close(); raise HTTPException(404,'Application not found')
    if decision not in ['approved','rejected']: conn.close(); raise HTTPException(400,'Decision must be approved or rejected')
    reason=data.reason
    if a['requested_role']=='student':
        n=conn.execute('SELECT COUNT(*) n FROM students').fetchone()['n']; rule=a['gpa']>3.0 and n<PROGRAM_QUOTA
        if decision=='approved' and not rule and not reason: conn.close(); raise HTTPException(400,'Registrar must justify approving a student who fails GPA/quota rule.')
        if decision=='rejected' and rule and not reason: conn.close(); raise HTTPException(400,'Registrar must justify rejecting a student who meets GPA/quota rule.')
    temp=''
    if decision=='approved':
        existing=conn.execute('SELECT id FROM users WHERE username=?',(a['username'],)).fetchone()
        if existing:
            conn.close(); raise HTTPException(400,'A user with this username already exists.')
        temp='changeme123'
        uid=conn.execute('INSERT INTO users(username,name,password_hash,role,must_change_password) VALUES(?,?,?,?,1)',(a['username'],a['name'],hpw(temp),a['requested_role'])).lastrowid
        if a['requested_role']=='student': conn.execute('INSERT INTO students(user_id,student_id,gpa,semester_gpa,completed_courses) VALUES(?,?,?,?,0)',(uid,a['username'],a['gpa'],a['gpa']))
        else: conn.execute('INSERT INTO instructors(user_id,department,assigned_courses) VALUES(?,?,?)',(uid,'Unassigned',''))
        if not reason:
            reason=f'Approved. Login username: {a["username"]}. Temporary password: {temp}. User must change this password on first login.'
    conn.execute('UPDATE applications SET status=?,decision_reason=?,temp_password=? WHERE id=?',(decision,reason,temp,app_id))
    conn.commit(); conn.close(); return {'message':f'Application {decision}.' + (f' Login username: {a["username"]}. Temporary password: {temp}.' if temp else ''),'temporary_password':temp,'username':a['username']}

@app.get('/api/semester')
def semester(): return {'phase':phase(),'periods':PHASES}
@app.post('/api/semester')
def set_sem(data:PhaseIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar'])
    selected=canonical_phase(data.phase)
    if not selected: raise HTTPException(400,'Invalid semester phase')
    conn=db(); conn.execute('UPDATE semester SET phase=? WHERE id=1',(selected,)); conn.commit(); conn.close(); return {'message':f'Semester phase updated to {selected}.','phase':selected}

@app.post('/api/courses')
def create_course(data:CourseIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar'])
    if phase()!='class set-up period': raise HTTPException(400,'Courses can be created only during class set-up period. Use the registrar phase dropdown and click Update Phase first.')
    code=data.code.upper().strip()
    if not COURSE_CODE_RE.match(code): raise HTTPException(400,'Course code must be 2-6 letters then 2-4 digits (e.g., CS301).')
    if not data.title.strip(): raise HTTPException(400,'Course title cannot be blank.')
    conn=db()
    if conn.execute('SELECT 1 FROM courses WHERE code=?',(code,)).fetchone(): conn.close(); raise HTTPException(400,'A course with this code already exists. Use a new code for the demo.')
    inst=conn.execute("SELECT id,status FROM users WHERE username=? AND role='instructor'",(data.instructor_username,)).fetchone()
    if not inst: conn.close(); raise HTTPException(404,'Instructor not found')
    if inst['status']=='suspended': conn.close(); raise HTTPException(400,'Suspended instructor cannot teach next semester')
    conn.execute('INSERT INTO courses(code,title,instructor_user_id,schedule,capacity,credits) VALUES(?,?,?,?,?,?)',(code,data.title.strip(),inst['id'],data.schedule,data.capacity,data.credits)); conn.commit(); conn.close(); return {'message':'Course created.'}

@app.post('/api/enrollments')
def enroll(data:EnrollIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['student']); p=phase(); conn=db(); st=conn.execute('SELECT special_registration FROM students WHERE user_id=?',(u['id'],)).fetchone()
    if p=='special registration period' and not (st and st['special_registration']): conn.close(); raise HTTPException(400,'Special registration is only for students affected by cancelled courses.')
    if p not in ['course registration period','special registration period']: conn.close(); raise HTTPException(400,'Registration is closed during the current semester phase.')
    enrolled=rows(conn.execute("SELECT e.*,c.schedule FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE e.student_user_id=? AND e.status='enrolled' AND c.cancelled=0",(u['id'],)))
    if len(enrolled)>=4: conn.close(); raise HTTPException(400,'Students can register for at most 4 courses.')
    target=conn.execute('SELECT * FROM courses WHERE id=? AND cancelled=0',(data.course_id,)).fetchone()
    if not target: conn.close(); raise HTTPException(404,'Active course not found')
    if conn.execute('SELECT 1 FROM enrollments WHERE student_user_id=? AND course_id=? AND status IN (\'enrolled\',\'waitlist\')',(u['id'],data.course_id)).fetchone(): conn.close(); raise HTTPException(400,'Already enrolled or waitlisted in this course')
    prior=conn.execute("SELECT grade FROM enrollments WHERE student_user_id=? AND course_id=? AND grade!='' ORDER BY id DESC LIMIT 1",(u['id'],data.course_id)).fetchone()
    if prior and prior['grade']!='F': conn.close(); raise HTTPException(400,'Student may retake a class only after receiving F.')
    for e in enrolled:
        if e['schedule']==target['schedule']: conn.close(); raise HTTPException(400,'Time conflict with another enrolled course.')
    count=conn.execute("SELECT COUNT(*) n FROM enrollments WHERE course_id=? AND status='enrolled'",(data.course_id,)).fetchone()['n']
    status='waitlist' if count>=target['capacity'] else 'enrolled'
    conn.execute('INSERT INTO enrollments(student_user_id,course_id,status,created_at) VALUES(?,?,?,?)',(u['id'],data.course_id,status,now()))
    if p=='special registration period' and status=='enrolled': conn.execute('UPDATE students SET special_registration=0 WHERE user_id=?',(u['id'],))
    conn.commit(); conn.close(); return {'message':f'Enrollment status: {status}','status':status}
@app.get('/api/enrollments/mine')
def mine(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['student']); conn=db(); r=rows(conn.execute('''SELECT e.id,e.status,e.grade,c.id course_id,c.code,c.title,c.schedule,c.credits,c.cancelled FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE e.student_user_id=? ORDER BY e.id DESC''',(u['id'],))); conn.close(); return r
@app.delete('/api/enrollments/{enrollment_id}')
def unenroll(enrollment_id:int,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['student'])
    if phase() not in ['course registration period','special registration period']:
        raise HTTPException(400,'You can drop a class only during course registration or special registration period.')
    conn=db()
    e=conn.execute('SELECT * FROM enrollments WHERE id=? AND student_user_id=?',(enrollment_id,u['id'])).fetchone()
    if not e: conn.close(); raise HTTPException(404,'Enrollment not found.')
    if e['grade']: conn.close(); raise HTTPException(400,'You cannot drop a class after a grade is posted.')
    if e['status'] not in ['enrolled','waitlist']: conn.close(); raise HTTPException(400,'This enrollment cannot be dropped.')
    conn.execute("UPDATE enrollments SET status='dropped' WHERE id=?",(enrollment_id,))
    conn.commit(); conn.close()
    return {'message':'Class dropped. You can re-register during the registration period.'}

@app.get('/api/instructor/roster')
def roster(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['instructor']); conn=db(); r=rows(conn.execute('''SELECT e.id enrollment_id,c.id course_id,c.code,c.title,u.name student_name,u.username,s.gpa,s.completed_courses,e.status,e.grade FROM enrollments e JOIN courses c ON e.course_id=c.id JOIN users u ON e.student_user_id=u.id JOIN students s ON s.user_id=u.id WHERE c.instructor_user_id=? ORDER BY c.code,e.status,u.name''',(u['id'],))); conn.close(); return r
@app.post('/api/instructor/waitlist/approve')
def approve_wait(data:WaitlistIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['instructor']); conn=db(); e=conn.execute('''SELECT e.*,c.capacity,c.instructor_user_id,c.schedule FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE e.id=?''',(data.enrollment_id,)).fetchone()
    if not e or e['instructor_user_id']!=u['id'] or e['status']!='waitlist': conn.close(); raise HTTPException(403,'Only the assigned instructor can approve this waitlist entry')
    count=conn.execute("SELECT COUNT(*) n FROM enrollments WHERE course_id=? AND status='enrolled'",(e['course_id'],)).fetchone()['n']
    if count>=e['capacity']: conn.close(); raise HTTPException(400,'Class is still full; increase capacity or wait for a seat.')
    conflicts=conn.execute('''SELECT 1 FROM enrollments en JOIN courses c ON en.course_id=c.id WHERE en.student_user_id=? AND en.status='enrolled' AND c.schedule=? AND en.course_id!=?''',(e['student_user_id'],e['schedule'],e['course_id'])).fetchone()
    if conflicts: conn.close(); raise HTTPException(400,'Student now has a time conflict.')
    conn.execute("UPDATE enrollments SET status='enrolled' WHERE id=?",(data.enrollment_id,)); conn.commit(); conn.close(); return {'message':'Student moved from waitlist into the class.'}

@app.post('/api/grades')
def grade(data:GradeIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['instructor'])
    if phase()!='grading period': raise HTTPException(400,'Grades can be submitted only during grading period.')
    if data.grade not in GRADES: raise HTTPException(400,'Invalid grade')
    conn=db(); e=conn.execute('''SELECT e.*,c.instructor_user_id FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE e.id=? AND e.status='enrolled' ''',(data.enrollment_id,)).fetchone()
    if not e or e['instructor_user_id']!=u['id']: conn.close(); raise HTTPException(403,'You can grade only your assigned enrolled students.')
    conn.execute('UPDATE enrollments SET grade=? WHERE id=?',(data.grade,data.enrollment_id)); newgpa=recalc_student(conn,e['student_user_id']); conn.commit(); conn.close(); return {'message':'Grade submitted successfully.','new_student_gpa':newgpa}

@app.post('/api/reviews')
def review(data:ReviewIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['student'])
    if not 1<=data.stars<=5: raise HTTPException(400,'Stars must be 1 to 5')
    conn=db(); e=conn.execute("SELECT * FROM enrollments WHERE student_user_id=? AND course_id=? AND status='enrolled'",(u['id'],data.course_id)).fetchone()
    if not e: conn.close(); raise HTTPException(403,'Only enrolled students can review this class.')
    if e['grade']: conn.close(); raise HTTPException(400,'You cannot rate the class after the instructor posts the grade.')
    words=[r['word'] for r in conn.execute('SELECT word FROM taboo_words')]; text=data.review_text; count=0
    for w in words:
        pattern=re.compile(re.escape(w),re.IGNORECASE)
        matches=len(pattern.findall(text)); count+=matches; text=pattern.sub('*'*len(w),text)
    visible=0 if count>=3 else 1; warn=2 if count>=3 else (1 if count else 0)
    if warn: add_warning(conn,u['id'],warn,'taboo review')
    conn.execute('INSERT INTO reviews(student_user_id,course_id,stars,review_text,visible,created_at) VALUES(?,?,?,?,?,?)',(u['id'],data.course_id,data.stars,text,visible,now()))
    avg,_=avg_rating(data.course_id); cr=conn.execute('SELECT instructor_user_id FROM courses WHERE id=?',(data.course_id,)).fetchone()
    if cr and avg and avg<2: add_warning(conn,cr['instructor_user_id'],1,'course rating below 2')
    conn.commit(); conn.close(); return {'message':'Review submitted.' if visible else 'Review hidden because it has 3 or more taboo words.','filtered_review':text,'warnings_added':warn}
@app.get('/api/reviews')
def list_reviews(authorization:str|None=Header(None)):
    u=current_user(authorization); conn=db()
    if u['role']=='registrar': r=rows(conn.execute('''SELECT r.*,u.username reviewer,c.code FROM reviews r JOIN users u ON r.student_user_id=u.id JOIN courses c ON r.course_id=c.id ORDER BY r.id DESC'''))
    else: r=rows(conn.execute('''SELECT r.id,c.code,r.stars,r.review_text,r.visible,r.created_at FROM reviews r JOIN courses c ON r.course_id=c.id WHERE r.visible=1 ORDER BY r.id DESC'''))
    conn.close(); return r

@app.get('/api/taboo-words')
def taboo(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar']); conn=db(); r=rows(conn.execute('SELECT * FROM taboo_words ORDER BY word')); conn.close(); return r
@app.post('/api/taboo-words')
def add_taboo(data:TabooIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar']); conn=db(); conn.execute('INSERT OR IGNORE INTO taboo_words(word) VALUES(?)',(data.word.lower().strip(),)); conn.commit(); conn.close(); return {'message':'Taboo word saved.'}
@app.delete('/api/taboo-words/{word_id}')
def delete_taboo(word_id:int,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar']); conn=db(); conn.execute('DELETE FROM taboo_words WHERE id=?',(word_id,)); conn.commit(); conn.close(); return {'message':'Taboo word deleted.'}

@app.post('/api/complaints')
def submit_complaint(data:ComplaintIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['student','instructor'])
    ctype=data.complaint_type.lower().strip()
    if ctype not in COMPLAINT_TYPES: raise HTTPException(400,f'Complaint type must be one of: {", ".join(sorted(COMPLAINT_TYPES))}.')
    if data.target_username==u['username']: raise HTTPException(400,'You cannot file a complaint against yourself.')
    conn=db(); t=conn.execute('SELECT id FROM users WHERE username=?',(data.target_username,)).fetchone()
    if not t: conn.close(); raise HTTPException(404,'Target user not found')
    words=[r['word'] for r in conn.execute('SELECT word FROM taboo_words')]; text=data.description.strip(); count=0
    for w in words:
        pattern=re.compile(re.escape(w),re.IGNORECASE)
        matches=len(pattern.findall(text)); count+=matches; text=pattern.sub('*'*len(w),text)
    warn=2 if count>=3 else (1 if count else 0)
    if warn: add_warning(conn,u['id'],warn,'taboo complaint')
    conn.execute('INSERT INTO complaints(submitted_by,target_username,complaint_type,description,created_at) VALUES(?,?,?,?,?)',(u['id'],data.target_username,ctype,text,now())); conn.commit(); conn.close()
    msg='Complaint submitted for registrar review.'
    if count>=3: msg='Complaint submitted with banned words censored; 2 warnings added.'
    elif count: msg='Complaint submitted with banned words censored; 1 warning added.'
    return {'message':msg,'filtered_description':text,'warnings_added':warn}
@app.get('/api/complaints')
def complaints(authorization:str|None=Header(None)):
    u=current_user(authorization); conn=db()
    if u['role']=='registrar': r=rows(conn.execute('''SELECT c.*,u.username submitted_by_username FROM complaints c LEFT JOIN users u ON c.submitted_by=u.id ORDER BY c.id DESC'''))
    else: r=rows(conn.execute('SELECT * FROM complaints WHERE submitted_by=? ORDER BY id DESC',(u['id'],)))
    conn.close(); return r
@app.get('/api/complaint-targets')
def complaint_targets(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['student','instructor']); conn=db()
    r=rows(conn.execute("SELECT username,name,role FROM users WHERE role IN ('student','instructor') AND status!='closed' AND id!=? ORDER BY role,name",(u['id'],)))
    conn.close(); return r

@app.post('/api/complaints/decision')
def complaint_decision(data:ComplaintDecisionIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar']); conn=db(); c=conn.execute('SELECT * FROM complaints WHERE id=?',(data.complaint_id,)).fetchone()
    if not c: conn.close(); raise HTTPException(404,'Complaint not found')
    target=conn.execute('SELECT * FROM users WHERE username=?',(c['target_username'],)).fetchone()
    if data.action=='warn_target' and target: add_warning(conn,target['id'],1,'complaint')
    elif data.action=='warn_submitter': add_warning(conn,c['submitted_by'],1,'bad complaint')
    elif data.action=='deregister_student' and target and target['role']=='student': conn.execute("UPDATE enrollments SET status='deregistered' WHERE student_user_id=? AND status IN ('enrolled','waitlist')",(target['id'],)); add_warning(conn,target['id'],1,'deregistered after complaint')
    elif data.action=='suspend_target' and target: conn.execute("UPDATE users SET status='suspended' WHERE id=?",(target['id'],));
    conn.execute('UPDATE complaints SET status=\'resolved\',resolution=? WHERE id=?',(data.resolution or data.action,data.complaint_id)); conn.commit(); conn.close(); return {'message':'Complaint processed.'}

@app.post('/api/rules/run-class-running-check')
def running_check(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar'])
    if phase()!='class running period': raise HTTPException(400,'This check is for class running period.')
    conn=db(); res=[]
    for s in rows(conn.execute("SELECT id,name FROM users WHERE role='student' AND status='active'")):
        n=conn.execute("SELECT COUNT(*) n FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE e.student_user_id=? AND e.status='enrolled' AND c.cancelled=0",(s['id'],)).fetchone()['n']
        if n<2: add_warning(conn,s['id'],1,'fewer than 2 courses'); res.append(f"{s['name']} warned for fewer than 2 active courses.")
    cancelled_instructors={}
    for c in rows(conn.execute("SELECT id,title,instructor_user_id,cancelled FROM courses WHERE status!='cancelled'")):
        n=conn.execute("SELECT COUNT(*) n FROM enrollments WHERE course_id=? AND status='enrolled'",(c['id'],)).fetchone()['n']
        if n<3:
            conn.execute("UPDATE courses SET cancelled=1,status='cancelled' WHERE id=?",(c['id'],)); add_warning(conn,c['instructor_user_id'],1,'course cancelled'); cancelled_instructors[c['instructor_user_id']]=1; res.append(f"{c['title']} cancelled for fewer than 3 students; instructor warned.")
            for e in rows(conn.execute("SELECT student_user_id FROM enrollments WHERE course_id=? AND status='enrolled'",(c['id'],))): conn.execute('UPDATE students SET special_registration=1 WHERE user_id=?',(e['student_user_id'],))
    for iid in cancelled_instructors:
        total=conn.execute("SELECT COUNT(*) n FROM courses WHERE instructor_user_id=?",(iid,)).fetchone()['n']; canc=conn.execute("SELECT COUNT(*) n FROM courses WHERE instructor_user_id=? AND cancelled=1",(iid,)).fetchone()['n']
        if total and total==canc: conn.execute("UPDATE users SET status='suspended' WHERE id=?",(iid,)); conn.execute('UPDATE instructors SET suspended_next_semester=1 WHERE user_id=?',(iid,)); res.append('Instructor suspended because all courses were cancelled.')
    conn.commit(); conn.close(); return {'message':'Class running check complete. Special registration opened for affected students.','results':res}

@app.post('/api/rules/grading-period-check')
def grading_check(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar']); conn=db(); res=[]
    for c in rows(conn.execute('SELECT id,title,instructor_user_id FROM courses WHERE cancelled=0')):
        enr=rows(conn.execute("SELECT grade FROM enrollments WHERE course_id=? AND status='enrolled'",(c['id'],)))
        if not enr: continue
        missing=sum(1 for e in enr if not e['grade']); vals=[GRADES[e['grade']] for e in enr if e['grade'] in GRADES]
        if missing: add_warning(conn,c['instructor_user_id'],1,'missing grades'); res.append(f"Instructor warned because {c['title']} has missing grades.")
        if vals:
            cg=round(sum(vals)/len(vals),2)
            if cg>3.5 or cg<2.5:
                existing=conn.execute("SELECT 1 FROM instructor_questions WHERE instructor_user_id=? AND course_id=? AND status IN ('open','justified','accepted','warned','fired')",(c['instructor_user_id'],c['id'])).fetchone()
                if not existing:
                    conn.execute('INSERT INTO instructor_questions(instructor_user_id,course_id,class_gpa,created_at) VALUES(?,?,?,?)',(c['instructor_user_id'],c['id'],cg,now()))
                    res.append(f"Instructor questioned because {c['title']} class GPA is {cg}.")
                else:
                    res.append(f"Existing GPA question already exists for {c['title']}; no duplicate created.")
    for s in rows(conn.execute('SELECT user_id FROM students')): recalc_student(conn,s['user_id'])
    conn.commit(); conn.close(); return {'message':'Grading-period rule check completed.','results':res}
@app.get('/api/instructor/questions')
def instr_questions(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['instructor','registrar']); conn=db()
    if u['role']=='registrar': r=rows(conn.execute('''SELECT q.*,u.name instructor_name,c.code FROM instructor_questions q JOIN users u ON q.instructor_user_id=u.id JOIN courses c ON q.course_id=c.id ORDER BY q.id DESC'''))
    else: r=rows(conn.execute('''SELECT q.*,c.code FROM instructor_questions q JOIN courses c ON q.course_id=c.id WHERE q.instructor_user_id=? ORDER BY q.id DESC''',(u['id'],)))
    conn.close(); return r
@app.post('/api/instructor/questions/justify')
def justify(data:JustifyIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['instructor'])
    if not data.justification.strip(): raise HTTPException(400,'Please type a justification before submitting.')
    conn=db(); q=conn.execute("SELECT id FROM instructor_questions WHERE id=? AND instructor_user_id=? AND status='open'",(data.question_id,u['id'])).fetchone()
    if not q: conn.close(); raise HTTPException(400,'Only open GPA questions can be justified.')
    conn.execute("UPDATE instructor_questions SET justification=?,status='justified' WHERE id=? AND instructor_user_id=?",(data.justification.strip(),data.question_id,u['id'])); conn.commit(); conn.close(); return {'message':'Justification submitted to registrar.'}
@app.post('/api/instructor/questions/decision')
def decide_question(data:RegistrarQuestionDecisionIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar']); conn=db(); q=conn.execute('SELECT * FROM instructor_questions WHERE id=?',(data.question_id,)).fetchone()
    if not q: conn.close(); raise HTTPException(404,'Question not found')
    if data.decision=='accepted': status='accepted'
    elif data.decision=='warn': add_warning(conn,q['instructor_user_id'],1,'bad GPA justification'); status='warned'
    elif data.decision=='fire': conn.execute("UPDATE users SET status='terminated' WHERE id=?",(q['instructor_user_id'],)); conn.execute('UPDATE instructors SET fired=1 WHERE user_id=?',(q['instructor_user_id'],)); status='fired'
    else: conn.close(); raise HTTPException(400,'Decision must be accepted, warn, or fire')
    conn.execute('UPDATE instructor_questions SET status=?,registrar_decision=? WHERE id=?',(status,data.reason or data.decision,data.question_id)); conn.commit(); conn.close(); return {'message':'Instructor GPA question processed.'}

@app.get('/api/academic-record')
def academic(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['student']); conn=db(); st=dict(conn.execute('SELECT * FROM students WHERE user_id=?',(u['id'],)).fetchone()); st['warnings']=u['warnings']; st['status']=u['status']; st['fine_due']=u.get('fine_due',0); st['missing_required_courses']=', '.join(missing_required(conn,u['id']))
    ens=rows(conn.execute('''SELECT e.id,c.id course_id,c.code,c.title,e.status,e.grade,c.cancelled FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE e.student_user_id=? ORDER BY e.id DESC''',(u['id'],))); conn.close(); return {'student':st,'enrollments':ens,'tutorial':'New students: change your temporary password, use Courses to register, Records to track GPA/graduation, Reviews before grades, Complaints for problems, and AI Chatbot for local rule questions.'}

def missing_required(conn, uid):
    completed=[r['code'] for r in conn.execute('''SELECT c.code FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE e.student_user_id=? AND e.status='enrolled' AND e.grade!='' AND e.grade!='F' ''',(uid,))]
    return [c for c in REQUIRED_COURSES if c not in completed]
@app.post('/api/graduation/apply')
def grad_apply(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['student']); conn=db(); st=conn.execute('SELECT completed_courses FROM students WHERE user_id=?',(u['id'],)).fetchone(); missing=missing_required(conn,u['id'])
    if st['completed_courses']<8:
        add_warning(conn,u['id'],1,'reckless graduation application'); conn.commit(); conn.close(); return {'message':'Graduation application rejected automatically: need 8 completed classes. Warning added.'}
    existing=conn.execute("SELECT id FROM graduation_applications WHERE student_user_id=? AND status='pending'",(u['id'],)).fetchone()
    if existing: conn.close(); return {'message':'Graduation application is already pending registrar review.'}
    conn.execute('INSERT INTO graduation_applications(student_user_id,status,missing_requirements,created_at) VALUES(?,?,?,?)',(u['id'],'pending',', '.join(missing),now())); conn.commit(); conn.close(); return {'message':'Graduation application submitted for registrar final verification.'}
@app.get('/api/graduation/applications')
def grad_apps(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar']); conn=db(); r=rows(conn.execute('''SELECT g.*,u.username,u.name,s.gpa,s.completed_courses FROM graduation_applications g JOIN users u ON g.student_user_id=u.id JOIN students s ON s.user_id=u.id ORDER BY g.id DESC''')); conn.close(); return r
@app.post('/api/graduation/decision')
def grad_decision(data:GraduationDecisionIn,authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar']); conn=db(); g=conn.execute('SELECT * FROM graduation_applications WHERE id=?',(data.application_id,)).fetchone()
    if not g: conn.close(); raise HTTPException(404,'Graduation application not found')
    missing=missing_required(conn,g['student_user_id'])
    if data.decision=='approved' and missing and not data.reason: conn.close(); raise HTTPException(400,'Required courses are missing; provide justification or reject.')
    if data.decision=='approved': conn.execute("UPDATE users SET status='closed' WHERE id=?",(g['student_user_id'],)); conn.execute("UPDATE students SET degree_status='graduated with Bachelor degree' WHERE user_id=?",(g['student_user_id'],)); status='approved'; msg='Graduation approved. Student leaves the active system with a Bachelor degree.'
    elif data.decision=='rejected': add_warning(conn,g['student_user_id'],1,'reckless graduation application'); status='rejected'; msg='Graduation rejected and warning added.'
    else: conn.close(); raise HTTPException(400,'Decision must be approved or rejected')
    conn.execute('UPDATE graduation_applications SET status=?,decision_reason=?,missing_requirements=? WHERE id=?',(status,data.reason,', '.join(missing),data.application_id)); conn.commit(); conn.close(); return {'message':msg}

@app.get('/api/admin/dashboard')
def admin(authorization:str|None=Header(None)):
    u=current_user(authorization); require(u,['registrar']); conn=db(); users=rows(conn.execute('SELECT id,username,name,role,status,warnings,fine_due,must_change_password FROM users ORDER BY role,username')); apps=rows(conn.execute('SELECT * FROM applications ORDER BY id DESC')); comps=rows(conn.execute('SELECT * FROM complaints ORDER BY id DESC')); grads=rows(conn.execute('''SELECT g.*,u.username,u.name FROM graduation_applications g JOIN users u ON g.student_user_id=u.id ORDER BY g.id DESC''')); questions=rows(conn.execute('''SELECT q.*,u.username instructor_username,c.code course_code FROM instructor_questions q JOIN users u ON q.instructor_user_id=u.id JOIN courses c ON q.course_id=c.id ORDER BY q.id DESC''')); tabs=rows(conn.execute('SELECT * FROM taboo_words ORDER BY word')); conn.close(); return {'users':users,'courses':public_courses(),'applications':apps,'complaints':comps,'graduation_applications':grads,'instructor_questions':questions,'taboo_words':tabs,'phase':phase(),'required_courses':REQUIRED_COURSES}

GEMINI_API_KEY_DEFAULT=''  # TODO: rotate and move to env var; key is exposed in source

def _gemini_call(system_prompt:str,user_msg:str,max_tokens:int=400,log_tag:str='gemini'):
    """Call Gemini and return text, or None on any failure (with reason printed)."""
    api_key=(os.environ.get('GEMINI_API_KEY','') or GEMINI_API_KEY_DEFAULT).strip()
    if not api_key:
        print(f'[{log_tag}] no Gemini key; using fallback')
        return None
    try:
        model=os.environ.get('GEMINI_MODEL','gemini-2.5-flash')
        url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
        req_body=json.dumps({
            'system_instruction':{'parts':[{'text':system_prompt}]},
            'contents':[{'role':'user','parts':[{'text':user_msg}]}],
            'generationConfig':{
                'maxOutputTokens':max_tokens,
                'temperature':0.4,
                'thinkingConfig':{'thinkingBudget':0},
            },
        }).encode()
        req=urllib.request.Request(url,data=req_body,headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(req,timeout=12) as resp:
            result=json.loads(resp.read())
        cands=result.get('candidates') or []
        parts=(cands[0].get('content') or {}).get('parts') if cands else None
        text=''.join(p.get('text','') for p in parts) if parts else ''
        if not text.strip(): raise ValueError(f'empty Gemini response: {result}')
        return text.strip()
    except urllib.error.HTTPError as e:
        body=''
        try: body=e.read().decode('utf-8','replace')[:500]
        except Exception: pass
        print(f'[{log_tag}] Gemini HTTP {e.code}: {body}')
    except Exception as e:
        print(f'[{log_tag}] Gemini call failed ({type(e).__name__}): {e}')
    return None

@app.get('/api/courses/{course_id}/ai-summary')
def course_ai_summary(course_id:int):
    conn=db()
    c=conn.execute('SELECT c.*,u.name instructor_name FROM courses c LEFT JOIN users u ON c.instructor_user_id=u.id WHERE c.id=?',(course_id,)).fetchone()
    if not c: conn.close(); raise HTTPException(404,'Course not found')
    revs=rows(conn.execute('SELECT stars,review_text FROM reviews WHERE course_id=? AND visible=1 ORDER BY id DESC LIMIT 30',(course_id,)))
    conn.close()
    avg,n=avg_rating(course_id)
    role='one of the 5 required courses for graduation' if c['code'] in REQUIRED_COURSES else 'an elective course'
    facts=f"Course code: {c['code']}\nTitle: {c['title']}\nInstructor: {c['instructor_name'] or 'TBD'}\nSchedule: {c['schedule']}\nCredits: {c['credits']}\nCapacity: {c['capacity']}\nRole: {role}"
    if revs:
        rt='\n'.join(f"- {r['stars']} stars: {r['review_text']}" for r in revs)
        sys_p="You summarize student reviews of a university course. Output three short labeled sections — Strengths, Weaknesses, Who should take it — each 1 to 2 sentences. Ground every claim in the reviews and facts provided. Do not invent details."
        user_msg=f"{facts}\nAverage rating: {avg} from {n} review(s).\nStudent reviews:\n{rt}"
        kind='reviews'
    else:
        sys_p="You write a brief, neutral 2 to 3 sentence description of a university course based only on the facts provided. Use the course title and code to infer what topics it likely covers, who might benefit, and any scheduling notes. Do not invent specifics like textbooks, professors, or grading."
        user_msg=f"{facts}\nThis course has no visible student reviews yet."
        kind='no-reviews'
    text=_gemini_call(sys_p,user_msg,max_tokens=800,log_tag='ai-summary')
    if text: return {'source':'AI Generated','kind':kind,'course':c['code'],'title':c['title'],'review_count':n,'avg_rating':avg,'summary':text}
    fallback=f"{c['code']} ({c['title']}) is {role}. Taught by {c['instructor_name'] or 'TBD'}, scheduled {c['schedule']}, {c['credits']} credits, capacity {c['capacity']}."
    fallback+=f" Average rating {avg} from {n} student review(s)." if n else " No student reviews yet."
    return {'source':'Course Facts','kind':kind,'course':c['code'],'title':c['title'],'review_count':n,'avg_rating':avg,'summary':fallback}

@app.post('/api/chat')
def chat(data:ChatIn,authorization:str|None=Header(None)):
    user=None
    if authorization:
        try: user=current_user(authorization)
        except Exception: user=None
    q=data.question.strip(); ql=q.lower(); conn=db()
    kb_entries=rows(conn.execute('SELECT keyword,answer FROM knowledge_base'))
    courses_info=rows(conn.execute('''SELECT courses.id,code,title,schedule,capacity,credits,u.name instructor_name,
        COALESCE(ec.enrolled_count,0) enrolled_count
        FROM courses LEFT JOIN users u ON courses.instructor_user_id=u.id
        LEFT JOIN (SELECT course_id,COUNT(*) enrolled_count FROM enrollments WHERE status='enrolled' GROUP BY course_id) ec ON courses.id=ec.course_id
        ORDER BY code'''))
    instructors_info=rows(conn.execute("SELECT u.name,i.department,i.assigned_courses FROM instructors i JOIN users u ON u.id=i.user_id ORDER BY u.name"))
    phase_row=conn.execute('SELECT phase FROM semester WHERE id=1').fetchone()
    current_phase=phase_row['phase'] if phase_row else 'unknown'
    user_context=''
    if user and user['role']=='student':
        st=conn.execute('SELECT gpa,semester_gpa,completed_courses,honor_roll,degree_status FROM students WHERE user_id=?',(user['id'],)).fetchone()
        enrollments=rows(conn.execute('SELECT c.code,c.title,e.status,e.grade FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE e.student_user_id=?',(user['id'],)))
        if st:
            enroll_str='; '.join(f"{e['code']}({e['status']}{',grade:'+e['grade'] if e['grade'] else ''})" for e in enrollments)
            user_context=f" STUDENT:{user['name']} GPA:{st['gpa']} SemGPA:{st['semester_gpa']} Completed:{st['completed_courses']}/8 HonorRoll:{'Yes' if st['honor_roll'] else 'No'} Fine:${user.get('fine_due') or 0} Status:{st['degree_status']} Warnings:{user['warnings']} Courses:[{enroll_str}]"
    if user and user['role']=='instructor':
        inst=conn.execute('SELECT department,assigned_courses FROM instructors WHERE user_id=?',(user['id'],)).fetchone()
        n=conn.execute("SELECT COUNT(*) n FROM enrollments e JOIN courses c ON e.course_id=c.id WHERE c.instructor_user_id=? AND e.status='enrolled'",(user['id'],)).fetchone()['n']
        user_context=f" INSTRUCTOR:{user['name']} Dept:{inst['department'] if inst else 'N/A'} Courses:{inst['assigned_courses'] if inst else 'N/A'} EnrolledStudents:{n}"
    conn.close()

    def smart_answer(ql):
        if any(w in ql for w in ['best class','best course','recommend','which class','which course','top class','top course','popular','highest rated']):
            return "Based on student reviews, CS301 (Data Structures) and ENG102 (Technical Writing) are the highest-rated courses. AI210 (AI for Campus Systems) is also popular and required for graduation."
        if any(w in ql for w in ['list course','list class','available course','available class','all course','all class','what course','what class','catalog','offer']) or (any(w in ql for w in ['course','class','subject']) and any(w in ql for w in ['available','show','list','all','what','which'])):
            lines='\n'.join(f"  {c['code']}: {c['title']} | {c['schedule']} | {c['enrolled_count']}/{c['capacity']} enrolled | {c['credits']} credits" for c in courses_info)
            return f"CampusFlow offers the following courses this semester:\n{lines}"
        if any(w in ql for w in ['register','registration','enroll','sign up','how to join','add class','how many course']):
            return f"Students can register for 2 to 4 courses during the course registration period (current phase: {current_phase}). Full classes place you on the instructor waitlist; no time conflicts allowed. Use the Action column in the Course Catalog to Register or Drop a class."
        if any(w in ql for w in ['drop ','unenroll','withdraw','cancel registration','quit class','leave class','drop a class','drop class']):
            return "You can drop a class during the course registration or special registration period using the Drop button in the Course Catalog. After grades are posted, classes cannot be dropped."
        if any(w in ql for w in ['graduat','degree','finish','diploma','how to complete','complete degree']):
            base="Students may apply for graduation after completing 8 courses total, including all 5 required ones: CS301, CS330, MATH201, ENG102, and AI210. The registrar verifies your record before approving."
            if user_context and 'STUDENT' in user_context:
                import re; m=re.search(r'Completed:(\d+)/8',user_context)
                if m: base+=f" You have completed {m.group(1)} of 8 required courses."
            return base
        if any(w in ql for w in ['gpa','grade point','academic standing']):
            base="GPA below 2.0 leads to termination; between 2.0-2.25 triggers a warning and mandatory interview. GPA above 3.5 (or semester GPA above 3.75) earns honor roll."
            if user_context and 'STUDENT' in user_context:
                import re; m=re.search(r'GPA:([\d.]+)',user_context)
                if m: base+=f" Your current GPA is {m.group(1)}."
            return base
        if any(w in ql for w in ['honor','honour','dean list']):
            return "Honor roll is awarded when your semester GPA exceeds 3.75 or your overall GPA exceeds 3.5 (after multiple semesters). Honor roll status removes one active warning from your record."
        if any(w in ql for w in ['warning','warn','suspend','suspension','3 warning','three warning']):
            return "Students receive warnings for rule violations such as taboo words in reviews or GPA issues. After 3 warnings you are suspended for one semester and owe a registrar fine. Honor roll can remove one warning."
        if any(w in ql for w in ['fee','fine','pay','cost','tuition','money','charge','penalty','owe','due']):
            base="Fines are issued by the registrar when a student is suspended after 3 warnings. The fine amount appears on your academic record."
            if user_context and 'STUDENT' in user_context:
                import re; m=re.search(r'Fine:\$([\d.]+)',user_context)
                if m and m.group(1)!='0': base=f"You currently owe a fine of ${m.group(1)}. "+base
            return base
        if any(w in ql for w in ['complaint','complain','report problem','report issue','dispute','misconduct','grievance']):
            return "Students and instructors can file complaints through the Complaints section. Categories include academic, behavior, and deregister requests. The registrar investigates and may warn, deregister, suspend, or dismiss the case."
        if any(w in ql for w in ['professor','instructor','teacher','prof ','faculty','staff','who teach']):
            lines=[f"  {i['name']} ({i['department']}): {i['assigned_courses'] or 'no courses assigned'}" for i in instructors_info]
            return "CampusFlow instructors:\n"+"\n".join(lines)+"\nInstructors must justify class GPAs outside the 2.5-3.5 range or face disciplinary action."
        if any(w in ql for w in ['review','rating','rate','star','feedback','opinion','evaluate']):
            return "Enrolled students can rate courses 1-5 stars and leave written feedback before grades are posted. Taboo words in reviews are filtered and trigger a warning. Reviews are visible to all users in the public browse view."
        if any(w in ql for w in ['semester','phase','period','timeline','schedule','when','current phase']):
            return f"The semester goes through 5 phases: class setup, course registration, class running, special registration, and grading. The system is currently in the '{current_phase}' phase."
        if any(w in ql for w in ['cancel','cancell','delay','minimum enrollment','not enough student','course drop']):
            return "Courses with fewer than 3 enrolled students are automatically cancelled during the class running check. Students whose course was cancelled can re-register during the special registration phase."
        if any(w in ql for w in ['waitlist','wait list','full class','full course','waiting list']):
            return "If a course is at full capacity, you are placed on the instructor waitlist. Only the instructor can manually approve waitlisted students and move them into the class during the class running period."
        if any(w in ql for w in ['special registr']):
            return "Special registration opens after course cancellations. Students whose course was cancelled use this window to register for other available open courses."
        if any(w in ql for w in ['apply','application','admission','how to join','new student','how to get in']):
            return "Prospective students apply through the Apply tab on the homepage. After registrar approval, you receive a temporary password to log in and must change it before using the system."
        if any(w in ql for w in ['required course','mandatory course','must take','needed for grad','prerequisite']):
            return "The 5 required courses for graduation are: CS301 (Data Structures), CS330 (Database Systems), MATH201 (Calculus II), ENG102 (Technical Writing), and AI210 (AI for Campus Systems). You must also complete 3 additional elective courses for a total of 8."
        if user and any(w in ql for w in ['my gpa','my course','my grade','my status','my warning','my fine','my record','my enrollment','am i on','how am i doing']):
            if user_context and 'STUDENT' in user_context:
                import re
                gpa=re.search(r'GPA:([\d.]+)',user_context); done=re.search(r'Completed:(\d+)/8',user_context)
                warn=re.search(r'Warnings:(\d+)',user_context); fine=re.search(r'Fine:\$([\d.]+)',user_context); hr=re.search(r'HonorRoll:(\w+)',user_context)
                parts=[]
                if gpa: parts.append(f"GPA {gpa.group(1)}")
                if done: parts.append(f"{done.group(1)}/8 courses completed")
                if hr: parts.append(f"honor roll: {hr.group(1)}")
                if warn: parts.append(f"{warn.group(1)} warning(s)")
                if fine and fine.group(1)!='0': parts.append(f"fine due: ${fine.group(1)}")
                return f"Your academic record: {', '.join(parts)}. Check the My Records tab for full enrollment details." if parts else "Check the My Records tab for your full academic details."
        if any(w in ql for w in ['taboo','bad word','banned word','filter','censored']):
            return "The registrar maintains a list of taboo words. If a taboo word appears in a review or complaint, the submission is flagged and the student receives a warning."
        # Specific course lookup driven by live DB rows
        for c in courses_info:
            code_lc=c['code'].lower(); title_lc=(c['title'] or '').lower()
            if code_lc in ql or (title_lc and title_lc in ql):
                role='one of the 5 required courses for graduation' if c['code'] in REQUIRED_COURSES else 'an elective course'
                return f"{c['code']} ({c['title']}) is taught by {c['instructor_name'] or 'TBD'}, scheduled {c['schedule']}, with {c['capacity']} seats ({c['enrolled_count']} enrolled). It is {role}."
        return f"I can answer questions about courses, registration, drop/unenroll, graduation, GPA, fees, complaints, professors, reviews, password reset, and semester phases. The college is currently in the '{current_phase}' phase. What would you like to know?"

    answer=smart_answer(ql); source='Local Knowledge Base'
    kb_text='\n'.join(f"{r['keyword']}: {r['answer']}" for r in kb_entries)
    ct='\n'.join(f"{c['code']}: {c['title']} ({c['instructor_name'] or 'TBD'}) {c['schedule']} cap:{c['capacity']} enrolled:{c['enrolled_count']}" for c in courses_info)
    inst_list='\n'.join(f"{i['name']} ({i['department']}): {i['assigned_courses']}" for i in instructors_info)
    sys_p=f"You are CampusFlow AI assistant. Answer in 1-3 sentences, directly and helpfully. Courses:\n{ct}\nInstructors:\n{inst_list}\nPhase:{current_phase}\nRequired:{','.join(REQUIRED_COURSES)} (8 total needed)\nPolicies:{kb_text}{user_context}"
    text=_gemini_call(sys_p,q,max_tokens=500,log_tag='chat')
    if text: answer=text; source='AI Generated'
    return {'source':source,'answer':answer}

if __name__=='__main__':
    import uvicorn; uvicorn.run('main:app',host='127.0.0.1',port=8000,reload=True)