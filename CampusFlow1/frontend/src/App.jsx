import React, { useEffect, useMemo, useState } from 'react';
import { api, setToken } from './api.js';
import {
  GraduationCap,
  ShieldCheck,
  BookOpen,
  MessageCircle,
  Star,
  AlertTriangle,
  Sparkles,
  Users,
  BarChart3,
  FileText,
  LogOut
} from 'lucide-react';

const demoAccounts = [
  { role: 'Registrar', username: 'registrar', password: 'registrar123' },
  { role: 'Instructor', username: 'prof_chen', password: 'pass123' },
  { role: 'Student', username: 'S1001', password: 'pass123' },
];

function DataTable({ data }) {
  const rows = Array.isArray(data) ? data : [];
  const columns = rows[0] ? Object.keys(rows[0]) : [];

  if (!rows.length) {
    return <p className="muted">No records yet.</p>;
  }

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c.replaceAll('_', ' ')}</th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c}>{String(row[c] ?? '')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Metric({ label, value, icon }) {
  return (
    <div className="metric">
      <span className="muted">
        {icon} {label}
      </span>
      <strong>{value}</strong>
    </div>
  );
}

function Landing({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({
    username: '',
    password: '',
    name: '',
    requested_role: 'student',
    gpa: 3.2,
    statement: ''
  });
  const [msg, setMsg] = useState(null);

  async function login(username = form.username, password = form.password) {
    setMsg(null);

    try {
      const res = await api('/api/auth/login', {
        method: 'POST',
        body: { username, password },
        auth: false
      });

      setToken(res.token);
      onLogin(res.user);
    } catch (e) {
      setMsg({ type: 'error', text: e.message });
    }
  }

  async function apply() {
    setMsg(null);

    try {
      const res = await api('/api/applications', {
        method: 'POST',
        auth: false,
        body: {
          name: form.name,
          username: form.username,
          requested_role: form.requested_role,
          gpa: Number(form.gpa),
          statement: form.statement
        }
      });

      setMsg({ type: 'success', text: res.message });
    } catch (e) {
      setMsg({ type: 'error', text: e.message });
    }
  }

  return (
    <div className="hero">
      <div className="brand">
        <div className="logo-block">
          <img
            src="/campusflow-logo.png"
            alt="CampusFlow logo"
            className="logo-img"
          />
          <div className="logo-text">CampusFlow</div>
        </div>

        <div>
          <div className="tagline">
            Where rigor meets <span className="gold">curiosity.</span>
          </div>
        </div>
      </div>

      <div className="authpanel">
        <div className="card">
          <div className="tabs">
            <button
              className={mode === 'login' ? 'active' : ''}
              onClick={() => setMode('login')}
            >
              Sign in
            </button>

            <button
              className={mode === 'apply' ? 'active' : ''}
              onClick={() => setMode('apply')}
            >
              Apply
            </button>
          </div>

          <h1 className="section-title">
            {mode === 'login' ? 'Welcome back' : 'Apply to CampusFlow'}
          </h1>

          {msg && (
            <div className={msg.type === 'error' ? 'error' : 'success'}>
              {msg.text}
            </div>
          )}

          <div className="grid" style={{ marginTop: 18 }}>
            {mode === 'apply' && (
              <div className="field">
                <label>Full name</label>
                <input
                  value={form.name}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      name: e.target.value
                    })
                  }
                />
              </div>
            )}

            <div className="field">
              <label>Username or student ID</label>
              <input
                value={form.username}
                onChange={(e) =>
                  setForm({
                    ...form,
                    username: e.target.value
                  })
                }
              />
            </div>

            {mode === 'login' ? (
              <div className="field">
                <label>Password</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      password: e.target.value
                    })
                  }
                />
              </div>
            ) : (
              <>
                <div className="two grid">
                  <div className="field">
                    <label>Apply as</label>
                    <select
                      value={form.requested_role}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          requested_role: e.target.value
                        })
                      }
                    >
                      <option value="student">Student</option>
                      <option value="instructor">Instructor</option>
                    </select>
                  </div>

                  <div className="field">
                    <label>GPA Of Student</label>
                    <input
                      type="number"
                      step="0.1"
                      value={form.gpa}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          gpa: e.target.value
                        })
                      }
                    />
                  </div>
                </div>

                <div className="field">
                  <label>Statement</label>
                  <textarea
                    value={form.statement}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        statement: e.target.value
                      })
                    }
                  />
                </div>
              </>
            )}

            <button
              className="btn gold"
              onClick={mode === 'login' ? () => login() : apply}
            >
              {mode === 'login' ? 'Sign in' : 'Submit application'}
            </button>
          </div>

          <hr
            style={{
              border: 'none',
              borderTop: '1px solid #eadcc5',
              margin: '26px 0'
            }}
          />

          <p className="muted">
            <b>Demo accounts</b>
          </p>

          <div className="quick">
            {demoAccounts.map((a) => (
              <button
                key={a.username}
                onClick={() => login(a.username, a.password)}
              >
                {a.role}: {a.username} / {a.password}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Dashboard({ user, onLogout }) {
  const [page, setPage] = useState('home');
  const [overview, setOverview] = useState(null);
  const [courses, setCourses] = useState([]);
  const [topStudents, setTopStudents] = useState([]);
  const [record, setRecord] = useState(null);
  const [roster, setRoster] = useState([]);
  const [admin, setAdmin] = useState(null);
  const [apps, setApps] = useState([]);
  const [complaints, setComplaints] = useState([]);
  const [msg, setMsg] = useState(null);
  const [chatQ, setChatQ] = useState('');
  const [chatA, setChatA] = useState(null);

  const [courseForm, setCourseForm] = useState({
    code: 'BIO220',
    title: 'Bioinformatics',
    instructor_username: 'prof_chen',
    schedule: 'Thu 5:00-7:30',
    capacity: 3,
    credits: 3
  });

  const [review, setReview] = useState({
    course_id: 1,
    stars: 5,
    review_text: ''
  });

  const [complaint, setComplaint] = useState({
    target_username: 'prof_chen',
    complaint_type: 'academic',
    description: ''
  });

  const [grade, setGrade] = useState({
    enrollment_id: '',
    grade: 'A'
  });

  const [phase, setPhase] = useState('course registration period');

  async function load() {
    setMsg(null);

    const [o, c, t, s] = await Promise.all([
      api('/api/public/overview', { auth: false }),
      api('/api/public/courses', { auth: false }),
      api('/api/public/top-students', { auth: false }),
      api('/api/semester', { auth: false })
    ]);

    setOverview(o);
    setCourses(c);
    setTopStudents(t);
    setPhase(s.phase);

    if (user.role === 'student') {
      setRecord(await api('/api/academic-record'));
    }

    if (user.role === 'instructor') {
      setRoster(await api('/api/instructor/roster'));
    }

    if (user.role === 'registrar') {
      const d = await api('/api/admin/dashboard');
      setAdmin(d);
      setApps(d.applications || []);
      setComplaints(d.complaints || []);
    } else {
      try {
        setComplaints(await api('/api/complaints'));
      } catch {
        // ignore complaint load error for users without records
      }
    }
  }

  useEffect(() => {
    load();
  }, []);

  const highest = useMemo(
    () =>
      [...courses]
        .sort((a, b) => (b.avg_rating || 0) - (a.avg_rating || 0))
        .slice(0, 3),
    [courses]
  );

  const lowest = useMemo(
    () =>
      [...courses]
        .sort((a, b) => (a.avg_rating || 0) - (b.avg_rating || 0))
        .slice(0, 3),
    [courses]
  );

  function navItems() {
    const items = [
      {
        key: 'home',
        label: 'Overview',
        icon: <BarChart3 size={16} />
      },
      {
        key: 'courses',
        label: 'Courses',
        icon: <BookOpen size={16} />
      },
      {
        key: 'chat',
        label: 'AI Chatbot',
        icon: <MessageCircle size={16} />
      }
    ];

    if (user.role === 'student') {
      items.push(
        {
          key: 'student',
          label: 'My Records',
          icon: <GraduationCap size={16} />
        },
        {
          key: 'reviews',
          label: 'Reviews',
          icon: <Star size={16} />
        },
        {
          key: 'complaints',
          label: 'Complaints',
          icon: <AlertTriangle size={16} />
        }
      );
    }

    if (user.role === 'instructor') {
      items.push(
        {
          key: 'instructor',
          label: 'Roster & Grades',
          icon: <Users size={16} />
        },
        {
          key: 'complaints',
          label: 'Complaints',
          icon: <AlertTriangle size={16} />
        }
      );
    }

    if (user.role === 'registrar') {
      items.push(
        {
          key: 'registrar',
          label: 'Registrar Admin',
          icon: <ShieldCheck size={16} />
        },
        {
          key: 'applications',
          label: 'Applications',
          icon: <FileText size={16} />
        },
        {
          key: 'complaints',
          label: 'Complaints',
          icon: <AlertTriangle size={16} />
        }
      );
    }

    return items;
  }

  async function safe(action) {
    setMsg(null);

    try {
      const res = await action();
      setMsg({
        type: 'success',
        text: res?.message || 'Done.'
      });
      await load();
    } catch (e) {
      setMsg({
        type: 'error',
        text: e.message
      });
    }
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="side-logo-block">
          <img
            src="/campusflow-logo.png"
            alt="CampusFlow logo"
            className="side-logo-img"
          />
          <div className="side-logo-text">CampusFlow</div>
        </div>

        <p className="muted" style={{ color: '#cbd5e1' }}>
          Signed in as <b>{user.name}</b>
          <br />
          Role: {user.role}
        </p>

        {navItems().map((i) => (
          <button
            key={i.key}
            className={`navbtn ${page === i.key ? 'active' : ''}`}
            onClick={() => setPage(i.key)}
          >
            {i.icon} &nbsp; {i.label}
          </button>
        ))}

        <button className="navbtn" onClick={onLogout}>
          <LogOut size={16} /> &nbsp; Logout
        </button>
      </aside>

      <main className="main">
        <div className="topbar">
          <div className="title">
            <h1>
              {page === 'home'
                ? 'Program Overview'
                : page[0].toUpperCase() + page.slice(1)}
            </h1>

            <span className="badge">
              <Sparkles size={16} /> Phase: {phase}
            </span>
          </div>

          <button className="btn ghost" onClick={load}>
            Refresh
          </button>
        </div>

        {msg && (
          <div className={msg.type === 'error' ? 'error' : 'success'}>
            {msg.text}
          </div>
        )}

        {page === 'home' && (
          <>
            <div className="creative">
              <h2>Creative feature: Smart Risk Dashboard + AI Guide</h2>
              <p>
                The app highlights honor roll, warnings, suspended risk, course
                cancellations, and gives role-aware chatbot answers.
              </p>
            </div>

            <div className="four grid">
              <Metric
                label="Students"
                value={overview?.total_students ?? 0}
                icon="🎓"
              />
              <Metric
                label="Courses"
                value={overview?.total_courses ?? 0}
                icon="📚"
              />
              <Metric label="User role" value={user.role} icon="🔐" />
              <Metric label="System" value="React + FastAPI" icon="⚡" />
            </div>

            <section className="panel">
              <h2 className="section-title">Introduction</h2>
              <p>{overview?.introduction}</p>
            </section>

            <div className="two grid">
              <section className="panel">
                <h2 className="section-title">Highest Rated Classes</h2>
                <DataTable data={highest} />
              </section>

              <section className="panel">
                <h2 className="section-title">Lowest Rated Classes</h2>
                <DataTable data={lowest} />
              </section>
            </div>

            <section className="panel">
              <h2 className="section-title">Students With Highest GPA</h2>
              <DataTable data={topStudents} />
            </section>
          </>
        )}

        {page === 'courses' && (
          <section className="panel">
            <h2 className="section-title">Course Catalog</h2>
            <DataTable data={courses} />

            {user.role === 'student' && (
              <div className="actions" style={{ marginTop: 16 }}>
                {courses.map((c) => (
                  <button
                    className="btn gold"
                    key={c.id}
                    onClick={() =>
                      safe(() =>
                        api('/api/enrollments', {
                          method: 'POST',
                          body: {
                            course_id: c.id
                          }
                        })
                      )
                    }
                  >
                    Register {c.code}
                  </button>
                ))}
              </div>
            )}
          </section>
        )}

        {page === 'student' && (
          <>
            <section className="panel">
              <h2 className="section-title">Student Tutorial</h2>
              <p>{record?.tutorial}</p>
            </section>

            <section className="panel">
              <h2 className="section-title">Academic Record</h2>

              <DataTable data={record ? [record.student] : []} />

              <h3>My Enrollments</h3>
              <DataTable data={record?.enrollments || []} />

              <button
                className="btn gold"
                onClick={async () => {
                  try {
                    const res = await api('/api/graduation/apply', {
                      method: 'POST'
                    });

                    alert(res.message);

                    setMsg({
                      type: 'success',
                      text: res.message
                    });

                    await load();
                  } catch (e) {
                    alert(e.message);

                    setMsg({
                      type: 'error',
                      text: e.message
                    });
                  }
                }}
              >
                Apply for graduation
              </button>
            </section>
          </>
        )}

        {page === 'reviews' && (
          <section className="panel">
            <h2 className="section-title">Submit Course Review</h2>

            <div className="grid two">
              <div className="field">
                <label>Course</label>
                <select
                  value={review.course_id}
                  onChange={(e) =>
                    setReview({
                      ...review,
                      course_id: Number(e.target.value)
                    })
                  }
                >
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.code} - {c.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label>Stars</label>
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={review.stars}
                  onChange={(e) =>
                    setReview({
                      ...review,
                      stars: Number(e.target.value)
                    })
                  }
                />
              </div>
            </div>

            <div className="field">
              <label>Review</label>
              <textarea
                value={review.review_text}
                onChange={(e) =>
                  setReview({
                    ...review,
                    review_text: e.target.value
                  })
                }
              />
            </div>

            <button
              className="btn gold"
              onClick={() =>
                safe(() =>
                  api('/api/reviews', {
                    method: 'POST',
                    body: review
                  })
                )
              }
            >
              Submit review
            </button>

            <p className="muted">
              Try words like “stupid” once to see filtering, or 3 taboo words
              to see hidden-review logic.
            </p>
          </section>
        )}

        {page === 'complaints' && (
          <section className="panel">
            <h2 className="section-title">Complaints</h2>

            {user.role !== 'registrar' && (
              <>
                <div className="grid two">
                  <div className="field">
                    <label>Target username</label>
                    <input
                      value={complaint.target_username}
                      onChange={(e) =>
                        setComplaint({
                          ...complaint,
                          target_username: e.target.value
                        })
                      }
                    />
                  </div>

                  <div className="field">
                    <label>Complaint type</label>
                    <input
                      value={complaint.complaint_type}
                      onChange={(e) =>
                        setComplaint({
                          ...complaint,
                          complaint_type: e.target.value
                        })
                      }
                    />
                  </div>
                </div>

                <div className="field">
                  <label>Description</label>
                  <textarea
                    value={complaint.description}
                    onChange={(e) =>
                      setComplaint({
                        ...complaint,
                        description: e.target.value
                      })
                    }
                  />
                </div>

                <button
                  className="btn gold"
                  onClick={() =>
                    safe(() =>
                      api('/api/complaints', {
                        method: 'POST',
                        body: complaint
                      })
                    )
                  }
                >
                  Submit complaint
                </button>
              </>
            )}

            <DataTable data={complaints} />
          </section>
        )}

        {page === 'instructor' && (
          <section className="panel">
            <h2 className="section-title">Assigned Students and Grades</h2>

            <DataTable data={roster} />

            <div className="grid two">
              <div className="field">
                <label>Enrollment ID</label>
                <input
                  value={grade.enrollment_id}
                  onChange={(e) =>
                    setGrade({
                      ...grade,
                      enrollment_id: Number(e.target.value)
                    })
                  }
                />
              </div>

              <div className="field">
                <label>Grade</label>
                <select
                  value={grade.grade}
                  onChange={(e) =>
                    setGrade({
                      ...grade,
                      grade: e.target.value
                    })
                  }
                >
                  {['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'D', 'F'].map(
                    (g) => (
                      <option key={g}>{g}</option>
                    )
                  )}
                </select>
              </div>
            </div>

            <button
              className="btn gold"
              onClick={() =>
                safe(() =>
                  api('/api/grades', {
                    method: 'POST',
                    body: grade
                  })
                )
              }
            >
              Submit grade
            </button>

            <p className="muted">
              Grades work during grading period. Registrar can switch the phase.
            </p>
          </section>
        )}

        {page === 'registrar' && (
          <section className="panel">
            <h2 className="section-title">Registrar Control Center</h2>

            <div className="grid two">
              <div className="field">
                <label>Semester phase</label>
                <select
                  value={phase}
                  onChange={(e) => setPhase(e.target.value)}
                >
                  {[
                    'class set-up period',
                    'course registration period',
                    'class running period',
                    'grading period',
                    'special registration period'
                  ].map((p) => (
                    <option key={p}>{p}</option>
                  ))}
                </select>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'end',
                  gap: 10,
                  flexWrap: 'wrap'
                }}
              >
                <button
                  className="btn gold"
                  onClick={() =>
                    safe(() =>
                      api('/api/semester', {
                        method: 'POST',
                        body: { phase }
                      })
                    )
                  }
                >
                  Update phase
                </button>

                <button
                  className="btn ghost"
                  onClick={() =>
                    safe(() =>
                      api('/api/rules/run-class-running-check', {
                        method: 'POST'
                      })
                    )
                  }
                >
                  Run class-running checks
                </button>

                <button
                  className="btn ghost"
                  onClick={() =>
                    safe(() =>
                      api('/api/rules/grading-period-check', {
                        method: 'POST'
                      })
                    )
                  }
                >
                  Run grading-period checks
                </button>
              </div>
            </div>

            <h3>Create Course</h3>

            <div className="grid two">
              {Object.keys(courseForm).map((k) => (
                <div className="field" key={k}>
                  <label>{k.replaceAll('_', ' ')}</label>
                  <input
                    value={courseForm[k]}
                    onChange={(e) =>
                      setCourseForm({
                        ...courseForm,
                        [k]:
                          k === 'capacity' || k === 'credits'
                            ? Number(e.target.value)
                            : e.target.value
                      })
                    }
                  />
                </div>
              ))}
            </div>

            <button
              className="btn gold"
              onClick={() =>
                safe(() =>
                  api('/api/courses', {
                    method: 'POST',
                    body: courseForm
                  })
                )
              }
            >
              Create course
            </button>

            <h3>All Users</h3>
            <DataTable data={admin?.users || []} />
          </section>
        )}

        {page === 'applications' && (
          <section className="panel">
            <h2 className="section-title">Applications</h2>

            <DataTable data={apps} />

            <div className="quick">
              {apps
                .filter((a) => a.status === 'pending')
                .map((a) => (
                  <React.Fragment key={a.id}>
                    <button
                      onClick={() =>
                        safe(() =>
                          api(`/api/applications/${a.id}/decision`, {
                            method: 'POST',
                            body: {
                              decision: 'approved',
                              reason: 'Approved from registrar dashboard'
                            }
                          })
                        )
                      }
                    >
                      Approve #{a.id}
                    </button>

                    <button
                      onClick={() =>
                        safe(() =>
                          api(`/api/applications/${a.id}/decision`, {
                            method: 'POST',
                            body: {
                              decision: 'rejected',
                              reason: 'Registrar decision recorded.'
                            }
                          })
                        )
                      }
                    >
                      Reject #{a.id}
                    </button>
                  </React.Fragment>
                ))}
            </div>
          </section>
        )}

        {page === 'chat' && (
          <section className="panel">
            <h2 className="section-title">AI-enabled Local Knowledge Chat</h2>

            <div className="chatbox">
              <input
                className="field"
                style={{
                  padding: 14,
                  border: '1px solid #d3b980',
                  borderRadius: 12
                }}
                value={chatQ}
                onChange={(e) => setChatQ(e.target.value)}
                placeholder="Ask about registration, GPA, graduation, complaints, reviews..."
              />

              <button
                className="btn gold"
                onClick={async () =>
                  setChatA(
                    await api('/api/chat', {
                      method: 'POST',
                      body: {
                        question: chatQ
                      }
                    })
                  )
                }
              >
                Ask
              </button>
            </div>

            <div className="quick" style={{ marginTop: 12 }}>
              {[
                'How many courses can I register for?',
                'How does graduation work?',
                'What happens with 3 warnings?',
                'How do reviews work?'
              ].map((q) => (
                <button key={q} onClick={() => setChatQ(q)}>
                  {q}
                </button>
              ))}
            </div>

            {chatA && (
              <div className="notice" style={{ marginTop: 16 }}>
                <b>{chatA.source}</b>
                <p>{chatA.answer}</p>
              </div>
            )}
          </section>
        )}

        {page === 'complaints' && user.role === 'registrar' && (
          <section className="panel">
            <h2 className="section-title">Process Complaints</h2>

            <div className="quick">
              {complaints
                .filter((c) => c.status === 'open')
                .map((c) => (
                  <React.Fragment key={c.id}>
                    <button
                      onClick={() =>
                        safe(() =>
                          api('/api/complaints/decision', {
                            method: 'POST',
                            body: {
                              complaint_id: c.id,
                              action: 'warn_target',
                              resolution:
                                'Target warned after registrar review.'
                            }
                          })
                        )
                      }
                    >
                      Warn target #{c.id}
                    </button>

                    <button
                      onClick={() =>
                        safe(() =>
                          api('/api/complaints/decision', {
                            method: 'POST',
                            body: {
                              complaint_id: c.id,
                              action: 'dismiss',
                              resolution: 'Dismissed after review.'
                            }
                          })
                        )
                      }
                    >
                      Dismiss #{c.id}
                    </button>
                  </React.Fragment>
                ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);

  function logout() {
    setToken(null);
    setUser(null);
  }

  return user ? (
    <Dashboard user={user} onLogout={logout} />
  ) : (
    <Landing onLogin={setUser} />
  );
}