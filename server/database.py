import sqlite3
from typing import List, Dict, Optional, Tuple


def create_database() -> sqlite3.Connection:
    """Create an in-memory SQLite database with sample data."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE employees (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        salary REAL NOT NULL,
        hire_date TEXT NOT NULL
    );
    ''')

    cursor.execute('''
    CREATE TABLE departments (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        budget REAL NOT NULL,
        manager_id INTEGER
    );
    ''')

    cursor.execute('''
    CREATE TABLE projects (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        budget REAL NOT NULL
    );
    ''')

    cursor.execute('''
    CREATE TABLE employee_projects (
        employee_id INTEGER,
        project_id INTEGER,
        role TEXT,
        PRIMARY KEY (employee_id, project_id)
    );
    ''')

    employees = [
        (1, 'Alice Johnson', 'Engineering', 75000.0, '2020-01-15'),
        (2, 'Bob Smith', 'Engineering', 70000.0, '2020-03-20'),
        (3, 'Charlie Brown', 'Sales', 60000.0, '2019-11-10'),
        (4, 'Diana Prince', 'Sales', 65000.0, '2021-05-05'),
        (5, 'Eve Wilson', 'HR', 55000.0, '2018-07-30'),
        (6, 'Frank Miller', 'Engineering', 80000.0, '2019-09-15'),
        (7, 'Grace Lee', 'Sales', 62000.0, '2022-01-20'),
        (8, 'Henry Davis', 'HR', 58000.0, '2020-12-01'),
        (9, 'Ivy Chen', 'Engineering', 72000.0, '2021-08-10'),
        (10, 'Jack Taylor', 'Sales', 63000.0, '2020-06-25'),
    ]
    cursor.executemany('INSERT INTO employees VALUES (?, ?, ?, ?, ?)', employees)

    departments = [
        (1, 'Engineering', 500000.0, 1),
        (2, 'Sales', 300000.0, 3),
        (3, 'HR', 150000.0, 5),
    ]
    cursor.executemany('INSERT INTO departments VALUES (?, ?, ?, ?)', departments)

    projects = [
        (1, 'Project Alpha', 'Engineering', '2023-01-01', '2023-06-30', 100000.0),
        (2, 'Project Beta', 'Sales', '2023-02-01', '2023-08-31', 80000.0),
        (3, 'Project Gamma', 'Engineering', '2023-03-01', '2023-09-30', 120000.0),
        (4, 'Project Delta', 'HR', '2023-04-01', '2023-10-31', 60000.0),
        (5, 'Project Epsilon', 'Sales', '2023-05-01', '2023-11-30', 90000.0),
    ]
    cursor.executemany('INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?)', projects)

    employee_projects = [
        (1, 1, 'Lead Developer'),
        (2, 1, 'Developer'),
        (6, 1, 'Senior Developer'),
        (9, 1, 'Developer'),
        (3, 2, 'Sales Manager'),
        (4, 2, 'Sales Rep'),
        (7, 2, 'Sales Rep'),
        (10, 2, 'Sales Rep'),
        (5, 4, 'HR Manager'),
        (8, 4, 'HR Specialist'),
    ]
    cursor.executemany('INSERT INTO employee_projects VALUES (?, ?, ?)', employee_projects)
    conn.commit()
    return conn


SCHEMA_STRING = """
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    salary REAL NOT NULL,
    hire_date TEXT NOT NULL
);

CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    budget REAL NOT NULL,
    manager_id INTEGER
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    budget REAL NOT NULL
);

CREATE TABLE employee_projects (
    employee_id INTEGER,
    project_id INTEGER,
    role TEXT,
    PRIMARY KEY (employee_id, project_id)
);
"""


def get_schema_string() -> str:
    return SCHEMA_STRING


def execute_query(conn: sqlite3.Connection, query: str) -> Tuple[List[Dict], Optional[str]]:
    """Execute a SQL query and return (rows_as_dicts, error_string_or_None)."""
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        result = [dict(zip(columns, row)) for row in rows]
        return result, None
    except sqlite3.Error as e:
        return [], str(e)


def rows_to_string(rows: List[Dict]) -> str:
    """Format query results as a readable table string."""
    if not rows:
        return "No results"
    columns = list(rows[0].keys())
    header = " | ".join(columns)
    separator = "-" * len(header)
    lines = [header, separator]
    for row in rows:
        line = " | ".join(str(row[col]) for col in columns)
        lines.append(line)
    return "\n".join(lines)