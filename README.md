# Online Judge (OJ) System

Online Judge (OJ) system built with **Python**, **FastAPI**, and **Jinja2** templates.

This project was developed as a university assignment and supports:

* User registration, login, and role‑based permissions (Student, Teacher, Admin)
* Problem creation, editing, deletion (Teachers/Admins)
* Code submission (Python) with asynchronous evaluation
* Multi‑testcase judging: `AC`, `WA`, `RE`, `TLE`, `SE`
* Detailed logs with role based visibility (hidden test cases hidden from students)
* Audit trails for sensitive actions
* Backup & restore (admin‑only)
* Code similarity detection (optional advanced feature)

---

## Requirements

* Requires Python 3.10 or higher.
* See `requirements.txt` for required python packages.

---

## Installation

1. **Clone the repository** (or extract the project folder).

    ```bash
    git clone https://github.com/ZaferDemirci/oj_project.git
    ```

2. **Create and activate a virtual environment** (recommended):

   ```
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

All settings are managed via environment variables (or a `.env` file).

* PowerShell

    ```powershell
    # Temporary variable (current session only)
    $env:MY_VAR = "some_value"

    # Remove with:
    Remove-Item Env:MY_VAR`
    # or
    $env:MY_VAR = $null


    # Permanent variable for current user
    [Environment]::SetEnvironmentVariable("MY_VAR", "some_value", "User")

    # Permanent variable for machine (all users)
    [Environment]::SetEnvironmentVariable("MY_VAR", "some_value", "Machine")
    
    # Remove with:
    [Environment]::SetEnvironmentVariable("MY_VAR", $null, "User")
    # or "Machine" for system-wide removal
    ```

* Bash
  
    ```bash
    # Temporary variable (current session only)
    export MY_VAR="some_value"

    # Remove with:
    unset MY_VAR
    ```

  * Add the export line to your shell startup file (e.g., ~/.bashrc, ~/.profile, ~/.bash_profile) and for machine use /etc/environment or /etc/profile (requires root).

Create a `.env` file in the project root (optional) with:

```env
SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

If no `.env` file is provided, the application uses default values (see below).

### Environment variables

| Variable          | Default                     | Description                                                                 |
|-------------------|-----------------------------|-----------------------------------------------------------------------------|
| `SECRET_KEY`      | `super-secret-dev-key-change-me` | **Required in production**, used for session signing. Generate a strong key. |
| `ADMIN_USERNAME`  | `admin`                     | Username for the initial admin account (created on first start).            |
| `ADMIN_PASSWORD`  | `admin123`                  | Password for the initial admin account. **Change it in production!**        |

---

## Running the Application

Start the FastAPI server (with auto‑reload for development):

```bash
uvicorn app.main:app --reload --reload-dir app
```

> ⚠️ The `--reload-dir app` flag prevents the server from restarting when temporary files are created inside temp/ during judging.

> For production, run without `--reload`:
>
> ```bash
> uvicorn app.main:app
> ```

Once running, open your browser at:

[http://localhost:8000](http://localhost:8000)

---

## Running Tests

Run the test suite with `pytest` (optionally with --verbose or -v):

```bash
pytest -v
```

All tests must pass for a successful build.

---

## Default Admin Account

On **first startup**, the system automatically creates an admin user:

* **Username:** `admin`
* **Password:** `admin123`

> **Important:** These are **development defaults**.

> Override them by setting the environment variables `ADMIN_USERNAME` and `ADMIN_PASSWORD` before starting the server.

---

## Persistence & Backup

* **Persistence method:** JSON files (stored in the `data/` directory).
* **Data files:**
  * `users.json`
  * `problems.json`
  * `submissions.json`
  * `audit_logs.json`
  * `similarity_reports.json`
* **Backups:** Created by the admin via the UI or API, stored in `data/backups/`.
* **Temporary judge files:** Stored in `temp/` and automatically cleaned up after each judge run (excluded from Git).

---

## Frontend

The frontend is **server‑side rendered** using **Jinja2** templates.

The frontend/ directory listed in the project explanation file is not present, instead, I used app/templates/ and app/static/

No separate frontend server is required, all pages are served directly from FastAPI.

Static files (CSS, etc.) are located in `app/static/`.

---

## Known Limitations

* Only **Python** code is supported for submissions.
* Memory limits are stored but **not enforced** (only time limits are enforced).
* The judge runs in a **separate subprocess** but does not use Docker or advanced isolation.
* The similarity detection uses AST based normalisation and is **not** a plagiarism‑proof tool, it only provides a suspicion score.

---

## Additional Notes

* **API documentation** (auto‑generated by FastAPI) is available at `/docs` and `/redoc` pages.
* All API endpoints are prefixed with `/api/` and return a unified JSON response format.

---

## Contributors

* Zafer DEMİRCİ 杜哲胜
