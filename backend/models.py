from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()


# ─────────────────────────────────────────────
#  ENUMS (stored as strings for portability)
# ─────────────────────────────────────────────
class Role:
    ADMIN = "admin"
    FACULTY = "faculty"
    STUDENT = "student"


class SubmissionStatus:
    PENDING = "pending"
    COMPILING = "compiling"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


class WriteUpStatus:
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"


# ─────────────────────────────────────────────
#  ASSOCIATION TABLES
# ─────────────────────────────────────────────
lab_students = db.Table(
    "lab_students",
    db.Column("lab_id", db.Integer, db.ForeignKey("labs.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("enrolled_at", db.DateTime, default=lambda: datetime.now(timezone.utc)),
)


# ─────────────────────────────────────────────
#  USER
# ─────────────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.STUDENT)

    # Student-specific fields
    roll_number = db.Column(db.String(30), unique=True, nullable=True)
    department = db.Column(db.String(100), nullable=True)
    semester = db.Column(db.Integer, nullable=True)
    section = db.Column(db.String(10), nullable=True)
    academic_year = db.Column(db.String(20), nullable=True)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    labs_created = db.relationship("Lab", back_populates="faculty", lazy="dynamic")
    labs_enrolled = db.relationship("Lab", secondary=lab_students, back_populates="students", lazy="dynamic")
    submissions = db.relationship("Submission", back_populates="student", lazy="dynamic")
    error_logs = db.relationship("ErrorLog", back_populates="student", lazy="dynamic")
    chat_messages = db.relationship("ChatMessage", back_populates="user", lazy="dynamic")
    notifications = db.relationship("Notification", back_populates="user", lazy="dynamic")
    performance_snapshots = db.relationship("PerformanceSnapshot", back_populates="student", lazy="dynamic")

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "roll_number": self.roll_number,
            "department": self.department,
            "semester": self.semester,
            "section": self.section,
            "academic_year": self.academic_year,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


# ─────────────────────────────────────────────
#  LAB
# ─────────────────────────────────────────────
class Lab(db.Model):
    __tablename__ = "labs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    semester = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(10), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    faculty_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Relationships
    faculty = db.relationship("User", back_populates="labs_created")
    students = db.relationship("User", secondary=lab_students, back_populates="labs_enrolled", lazy="dynamic")
    manuals = db.relationship("LabManual", back_populates="lab", lazy="dynamic", cascade="all, delete-orphan")
    programs = db.relationship("Program", back_populates="lab", lazy="dynamic", cascade="all, delete-orphan")
    writeups = db.relationship("WriteUp", back_populates="lab", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "subject": self.subject,
            "description": self.description,
            "semester": self.semester,
            "section": self.section,
            "academic_year": self.academic_year,
            "is_active": self.is_active,
            "faculty": self.faculty.to_dict() if self.faculty else None,
            "student_count": self.students.count(),
            "program_count": self.programs.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────────────────────────
#  LAB MANUAL
# ─────────────────────────────────────────────
class LabManual(db.Model):
    __tablename__ = "lab_manuals"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    original_name = db.Column(db.String(300), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default="uploaded")  # uploaded | processing | processed | failed
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    lab_id = db.Column(db.Integer, db.ForeignKey("labs.id"), nullable=False)
    lab = db.relationship("Lab", back_populates="manuals")

    def to_dict(self):
        return {
            "id": self.id,
            "original_name": self.original_name,
            "status": self.status,
            "lab_id": self.lab_id,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


# ─────────────────────────────────────────────
#  PROGRAM (from lab manual or manually added)
# ─────────────────────────────────────────────
class Program(db.Model):
    __tablename__ = "programs"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    objective = db.Column(db.Text, nullable=True)
    sample_input = db.Column(db.Text, nullable=True)
    sample_output = db.Column(db.Text, nullable=True)
    reference_solution = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), default="medium")  # easy | medium | hard
    prerequisites = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    lab_id = db.Column(db.Integer, db.ForeignKey("labs.id"), nullable=False)
    manual_id = db.Column(db.Integer, db.ForeignKey("lab_manuals.id"), nullable=True)

    lab = db.relationship("Lab", back_populates="programs")
    test_cases = db.relationship("TestCase", back_populates="program", lazy="dynamic", cascade="all, delete-orphan")
    submissions = db.relationship("Submission", back_populates="program", lazy="dynamic")
    writeups = db.relationship("WriteUp", back_populates="program", lazy="dynamic")

    def to_dict(self, include_solution=False):
        data = {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "description": self.description,
            "objective": self.objective,
            "sample_input": self.sample_input,
            "sample_output": self.sample_output,
            "difficulty": self.difficulty,
            "prerequisites": self.prerequisites,
            "lab_id": self.lab_id,
            "test_case_count": self.test_cases.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_solution:
            data["reference_solution"] = self.reference_solution
        return data


# ─────────────────────────────────────────────
#  TEST CASE
# ─────────────────────────────────────────────
class TestCase(db.Model):
    __tablename__ = "test_cases"

    id = db.Column(db.Integer, primary_key=True)
    input_data = db.Column(db.Text, nullable=True)
    expected_output = db.Column(db.Text, nullable=False)
    is_hidden = db.Column(db.Boolean, default=True)
    marks = db.Column(db.Float, default=1.0)
    description = db.Column(db.String(200), nullable=True)

    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    program = db.relationship("Program", back_populates="test_cases")

    def to_dict(self, reveal=False):
        data = {
            "id": self.id,
            "is_hidden": self.is_hidden,
            "marks": self.marks,
            "description": self.description,
            "program_id": self.program_id,
        }
        if not self.is_hidden or reveal:
            data["input_data"] = self.input_data
            data["expected_output"] = self.expected_output
        return data


# ─────────────────────────────────────────────
#  WRITE-UP
# ─────────────────────────────────────────────
class WriteUp(db.Model):
    __tablename__ = "writeups"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=20)
    total_marks = db.Column(db.Float, nullable=False, default=10.0)
    status = db.Column(db.String(20), default=WriteUpStatus.DRAFT)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    enable_monitoring = db.Column(db.Boolean, default=True)
    auto_submit = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    lab_id = db.Column(db.Integer, db.ForeignKey("labs.id"), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)

    lab = db.relationship("Lab", back_populates="writeups")
    program = db.relationship("Program", back_populates="writeups")
    submissions = db.relationship("Submission", back_populates="writeup", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "total_marks": self.total_marks,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "enable_monitoring": self.enable_monitoring,
            "auto_submit": self.auto_submit,
            "lab_id": self.lab_id,
            "program_id": self.program_id,
            "submission_count": self.submissions.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────────────────────────
#  SUBMISSION
# ─────────────────────────────────────────────
class Submission(db.Model):
    __tablename__ = "submissions"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(20), default="c")
    status = db.Column(db.String(20), default=SubmissionStatus.PENDING)

    # Scoring breakdown
    compilation_score = db.Column(db.Float, default=0.0)
    output_score = db.Column(db.Float, default=0.0)
    logic_score = db.Column(db.Float, default=0.0)
    total_score = db.Column(db.Float, default=0.0)
    max_marks = db.Column(db.Float, default=10.0)

    # Compiler results
    compiler_output = db.Column(db.Text, nullable=True)
    program_output = db.Column(db.Text, nullable=True)
    execution_time_ms = db.Column(db.Float, nullable=True)
    memory_kb = db.Column(db.Float, nullable=True)

    # AI analysis
    ai_feedback = db.Column(db.Text, nullable=True)

    # Monitoring
    tab_switches = db.Column(db.Integer, default=0)
    window_blur_count = db.Column(db.Integer, default=0)
    flagged = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.String(300), nullable=True)

    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    graded_at = db.Column(db.DateTime, nullable=True)

    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    writeup_id = db.Column(db.Integer, db.ForeignKey("writeups.id"), nullable=True)

    student = db.relationship("User", back_populates="submissions")
    program = db.relationship("Program", back_populates="submissions")
    writeup = db.relationship("WriteUp", back_populates="submissions")
    test_results = db.relationship("TestResult", back_populates="submission", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "language": self.language,
            "status": self.status,
            "compilation_score": self.compilation_score,
            "output_score": self.output_score,
            "logic_score": self.logic_score,
            "total_score": self.total_score,
            "max_marks": self.max_marks,
            "compiler_output": self.compiler_output,
            "program_output": self.program_output,
            "execution_time_ms": self.execution_time_ms,
            "ai_feedback": self.ai_feedback,
            "tab_switches": self.tab_switches,
            "flagged": self.flagged,
            "student_id": self.student_id,
            "program_id": self.program_id,
            "writeup_id": self.writeup_id,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }


# ─────────────────────────────────────────────
#  TEST RESULT (per test case per submission)
# ─────────────────────────────────────────────
class TestResult(db.Model):
    __tablename__ = "test_results"

    id = db.Column(db.Integer, primary_key=True)
    passed = db.Column(db.Boolean, default=False)
    actual_output = db.Column(db.Text, nullable=True)
    expected_output = db.Column(db.Text, nullable=False)
    marks_awarded = db.Column(db.Float, default=0.0)
    execution_time_ms = db.Column(db.Float, nullable=True)

    submission_id = db.Column(db.Integer, db.ForeignKey("submissions.id"), nullable=False)
    test_case_id = db.Column(db.Integer, db.ForeignKey("test_cases.id"), nullable=False)

    submission = db.relationship("Submission", back_populates="test_results")
    test_case = db.relationship("TestCase")

    def to_dict(self):
        return {
            "id": self.id,
            "passed": self.passed,
            "actual_output": self.actual_output,
            "expected_output": self.expected_output,
            "marks_awarded": self.marks_awarded,
            "test_case_id": self.test_case_id,
        }


# ─────────────────────────────────────────────
#  ERROR LOG (compiler error + AI explanation)
# ─────────────────────────────────────────────
class ErrorLog(db.Model):
    __tablename__ = "error_logs"

    id = db.Column(db.Integer, primary_key=True)
    raw_error = db.Column(db.Text, nullable=False)
    error_type = db.Column(db.String(80), nullable=True)   # syntax | runtime | logic | linker
    error_line = db.Column(db.Integer, nullable=True)
    ai_explanation = db.Column(db.Text, nullable=True)
    ai_hint = db.Column(db.Text, nullable=True)
    ai_tip = db.Column(db.Text, nullable=True)
    code_snippet = db.Column(db.Text, nullable=True)
    logged_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=True)

    student = db.relationship("User", back_populates="error_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "raw_error": self.raw_error,
            "error_type": self.error_type,
            "error_line": self.error_line,
            "ai_explanation": self.ai_explanation,
            "ai_hint": self.ai_hint,
            "ai_tip": self.ai_tip,
            "logged_at": self.logged_at.isoformat() if self.logged_at else None,
        }


# ─────────────────────────────────────────────
#  CHAT MESSAGE
# ─────────────────────────────────────────────
class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)   # user | assistant
    content = db.Column(db.Text, nullable=False)
    session_id = db.Column(db.String(80), nullable=True)
    context_type = db.Column(db.String(40), nullable=True)  # error | concept | debugging | general
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=True)

    user = db.relationship("User", back_populates="chat_messages")

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "context_type": self.context_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────────────────────────
#  NOTIFICATION
# ─────────────────────────────────────────────
class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(40), nullable=False)  # alert | info | warning | success
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────────────────────────
#  PERFORMANCE SNAPSHOT (periodic EDM record)
# ─────────────────────────────────────────────
class PerformanceSnapshot(db.Model):
    __tablename__ = "performance_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    avg_score = db.Column(db.Float, default=0.0)
    total_submissions = db.Column(db.Integer, default=0)
    compile_success_rate = db.Column(db.Float, default=0.0)
    common_error_type = db.Column(db.String(80), nullable=True)
    error_count = db.Column(db.Integer, default=0)
    ai_assist_count = db.Column(db.Integer, default=0)
    risk_level = db.Column(db.String(20), default="low")  # low | medium | high
    snapshot_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey("labs.id"), nullable=True)

    student = db.relationship("User", back_populates="performance_snapshots")

    def to_dict(self):
        return {
            "id": self.id,
            "avg_score": self.avg_score,
            "total_submissions": self.total_submissions,
            "compile_success_rate": self.compile_success_rate,
            "common_error_type": self.common_error_type,
            "error_count": self.error_count,
            "ai_assist_count": self.ai_assist_count,
            "risk_level": self.risk_level,
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
        }
