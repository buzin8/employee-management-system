import csv, io, os, re, secrets, sqlite3
from flask import Flask, g, render_template, request, redirect, url_for, flash, Response, abort

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
DB = os.environ.get("EMS_DB_PATH") or (
    "/tmp/employees.db" if os.environ.get("VERCEL") else os.path.join(os.path.dirname(__file__), "employees.db")
)
PER_PAGE = 8
DEPARTMENTS = ["Engineering", "Design", "Operations", "Finance", "People", "Sales"]
SORTS = {"name": "name", "salary": "salary DESC", "joined": "join_date DESC", "department": "department, name"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  phone TEXT,
  department TEXT NOT NULL,
  designation TEXT NOT NULL,
  salary REAL NOT NULL CHECK (salary > 0),
  join_date TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_emp_dept ON employees(department);
"""

SEED = [
    ("Aarav Sen", "aarav.sen@gmail.com", "9830011111", "Engineering", "Backend Developer", 780000, "2024-02-12"),
    ("Riya Das", "riya.das@gmail.com", "9830022222", "Design", "UI Designer", 620000, "2023-08-01"),
    ("Kabir Roy", "kabir.roy@gmail.com", "9830033333", "Operations", "Network Administrator", 540000, "2022-11-20"),
    ("Meera Nair", "meera.nair@gmail.com", "9830044444", "Finance", "Accounts Analyst", 580000, "2023-04-17"),
    ("Sahil Khan", "sahil.khan@gmail.com", "9830055555", "Engineering", "Security Engineer", 910000, "2021-06-07"),
    ("Isha Paul", "isha.paul@gmail.com", "9830066666", "People", "HR Executive", 450000, "2024-07-15"),
]


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO employees (name,email,phone,department,designation,salary,join_date) VALUES (?,?,?,?,?,?,?)", SEED)
    conn.commit()
    conn.close()


def validate(form, emp_id=None):
    data = {k: form.get(k, "").strip() for k in ("name", "email", "phone", "department", "designation", "salary", "join_date")}
    errors = []
    if not data["name"]:
        errors.append("Enter the employee's name.")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", data["email"]):
        errors.append("Enter a valid email address.")
    if data["phone"] and not re.match(r"^[0-9+\-\s]{7,15}$", data["phone"]):
        errors.append("Phone can contain digits, +, - and spaces (7 to 15 characters).")
    if not data["department"]:
        errors.append("Choose a department.")
    if not data["designation"]:
        errors.append("Enter a designation.")
    try:
        if float(data["salary"]) <= 0:
            raise ValueError
    except ValueError:
        errors.append("Salary must be a number greater than 0.")
    if not data["join_date"]:
        errors.append("Choose a join date.")
    if data["email"] and not errors:
        row = db().execute("SELECT id FROM employees WHERE email=? AND id IS NOT ?", (data["email"], emp_id)).fetchone()
        if row:
            errors.append("Another employee already uses this email.")
    return data, errors


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    dept = request.args.get("dept", "")
    sort = request.args.get("sort", "name")
    page = max(int(request.args.get("page", 1) or 1), 1)
    where, args = [], []
    if q:
        where.append("(name LIKE ? OR email LIKE ? OR phone LIKE ? OR department LIKE ? OR designation LIKE ?)")
        args += [f"%{q}%"] * 5
    if dept:
        where.append("department = ?")
        args.append(dept)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    total_found = db().execute(f"SELECT COUNT(*) FROM employees {clause}", args).fetchone()[0]
    pages = max((total_found + PER_PAGE - 1) // PER_PAGE, 1)
    page = min(page, pages)
    rows = db().execute(
        f"SELECT * FROM employees {clause} ORDER BY {SORTS.get(sort, 'name')} LIMIT ? OFFSET ?",
        args + [PER_PAGE, (page - 1) * PER_PAGE]).fetchall()
    stats = db().execute("SELECT COUNT(*) c, COALESCE(AVG(salary),0) a, COALESCE(SUM(salary),0) s, COALESCE(MAX(salary),0) m, COUNT(DISTINCT department) d, COALESCE(SUM(join_date >= date('now','start of year')),0) n FROM employees").fetchone()
    top = db().execute("SELECT name, designation, salary FROM employees ORDER BY salary DESC LIMIT 4").fetchall()
    by_dept = db().execute("SELECT department, COUNT(*) c FROM employees GROUP BY department ORDER BY c DESC").fetchall()
    return render_template("index.html", rows=rows, q=q, dept=dept, sort=sort, page=page, pages=pages,
                           found=total_found, total=stats["c"], avg=stats["a"], stats=stats, top=top, by_dept=by_dept, departments=DEPARTMENTS)


@app.route("/add", methods=["GET", "POST"])
def add():
    data = {}
    if request.method == "POST":
        data, errors = validate(request.form)
        if not errors:
            db().execute("INSERT INTO employees (name,email,phone,department,designation,salary,join_date) VALUES (:name,:email,:phone,:department,:designation,:salary,:join_date)", data)
            db().commit()
            flash(f"Added {data['name']}.")
            return redirect(url_for("index"))
        for e in errors:
            flash(e, "error")
    return render_template("form.html", e=data, departments=DEPARTMENTS, mode="Add")


@app.route("/edit/<int:emp_id>", methods=["GET", "POST"])
def edit(emp_id):
    emp = db().execute("SELECT * FROM employees WHERE id=?", (emp_id,)).fetchone()
    if not emp:
        abort(404)
    data = dict(emp)
    if request.method == "POST":
        data, errors = validate(request.form, emp_id)
        if not errors:
            data["id"] = emp_id
            db().execute("UPDATE employees SET name=:name,email=:email,phone=:phone,department=:department,designation=:designation,salary=:salary,join_date=:join_date,updated_at=CURRENT_TIMESTAMP WHERE id=:id", data)
            db().commit()
            flash(f"Saved changes for {data['name']}.")
            return redirect(url_for("index"))
        for e in errors:
            flash(e, "error")
    return render_template("form.html", e=data, departments=DEPARTMENTS, mode="Edit")


@app.route("/delete/<int:emp_id>", methods=["POST"])
def delete(emp_id):
    db().execute("DELETE FROM employees WHERE id=?", (emp_id,))
    db().commit()
    flash("Employee deleted.")
    return redirect(url_for("index"))


@app.route("/export.csv")
def export():
    rows = db().execute("SELECT id,name,email,phone,department,designation,salary,join_date FROM employees ORDER BY name").fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(rows[0].keys() if rows else ["id", "name", "email", "phone", "department", "designation", "salary", "join_date"])
    w.writerows([tuple(r) for r in rows])
    return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=employees.csv"})


init_db()
if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
