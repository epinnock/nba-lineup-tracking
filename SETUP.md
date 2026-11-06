# NBA Lineup Tracker - Environment Setup Guide

This guide walks you through setting up a Python virtual environment for the NBA Lineup Tracker project.

## Prerequisites

- **Python 3.9 or higher** (Check: `python --version` or `python3 --version`)
- **pip** (Python package installer, usually comes with Python)
- **Git** (optional, for cloning the repository)

---

## Quick Setup (Recommended)

### macOS/Linux

```bash
# 1. Navigate to project directory
cd /Users/ejirohome/Documents/Projects/nba-lineup-tracking

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate

# 4. Upgrade pip
pip install --upgrade pip

# 5. Install dependencies
pip install -r requirements.txt

# 6. Verify installation
python -c "import nba_api; print('✅ NBA API installed successfully')"
```

### Windows

```cmd
# 1. Navigate to project directory
cd C:\path\to\nba-lineup-tracking

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
venv\Scripts\activate

# 4. Upgrade pip
python -m pip install --upgrade pip

# 5. Install dependencies
pip install -r requirements.txt

# 6. Verify installation
python -c "import nba_api; print('✅ NBA API installed successfully')"
```

---

## Detailed Step-by-Step Instructions

### Step 1: Create Virtual Environment

A virtual environment isolates project dependencies from your system Python.

```bash
# Using venv (built-in to Python 3.3+)
python3 -m venv venv

# Alternative: Using virtualenv (if installed)
virtualenv venv

# Alternative: Using conda
conda create -n nba-lineup python=3.11
```

**What this does:**
- Creates a `venv/` directory with Python binaries
- Isolates packages from system-wide Python installation
- Prevents dependency conflicts with other projects

### Step 2: Activate Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Conda:**
```bash
conda activate nba-lineup
```

**Verification:**
Your terminal prompt should now show `(venv)` prefix:
```
(venv) user@machine:~/nba-lineup-tracking$
```

### Step 3: Install Dependencies

```bash
# Upgrade pip first (recommended)
pip install --upgrade pip

# Install all project dependencies
pip install -r requirements.txt
```

**What gets installed:**

| Package | Version | Purpose |
|---------|---------|---------|
| nba_api | ≥1.1.14 | NBA data access |
| pandas | ≥1.5.0 | Data manipulation |
| numpy | ≥1.23.0 | Numerical operations |
| python-dateutil | ≥2.8.2 | Date handling |
| requests | ≥2.28.0 | HTTP requests |
| pytest | ≥7.2.0 | Testing framework |
| pytest-cov | ≥4.0.0 | Test coverage |
| black | ≥22.0.0 | Code formatting |
| flake8 | ≥6.0.0 | Linting |
| mypy | ≥0.990 | Type checking |

### Step 4: Verify Installation

```bash
# Check installed packages
pip list

# Run a quick test
python -c "from api.nba_client import get_play_by_play; print('✅ Setup successful!')"

# Run test suite
pytest tests/ -v
```

---

## Working with the Virtual Environment

### Activating (Every Time You Work on Project)

**Before running any scripts or tests, activate the environment:**

```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Deactivating

```bash
deactivate
```

### Checking Active Environment

```bash
# Show Python location (should point to venv)
which python  # macOS/Linux
where python  # Windows

# Show installed packages
pip list

# Show environment info
pip show nba_api
```

---

## Usage Examples

### Running the Application

```bash
# Activate environment first
source venv/bin/activate

# Run analysis
python main.py 0022500032

# With options
python main.py 0022500032 --output-dir ./results --no-cache
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_boxscore.py -v

# Integration tests only
pytest tests/test_end_to_end.py -m integration -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Development Tasks

```bash
# Format code
black .

# Lint code
flake8 .

# Type check
mypy .
```

---

## Troubleshooting

### Issue: "python: command not found"

**Solution:** Use `python3` instead:
```bash
python3 -m venv venv
```

### Issue: "pip: command not found"

**Solution:** Use `python -m pip`:
```bash
python -m pip install -r requirements.txt
```

### Issue: Permission denied (macOS/Linux)

**Solution:** Don't use `sudo` with pip in virtual environments:
```bash
# ❌ Wrong
sudo pip install -r requirements.txt

# ✅ Correct
pip install -r requirements.txt
```

### Issue: PowerShell script execution disabled (Windows)

**Solution:** Enable script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: Module not found after installation

**Solution:** Ensure virtual environment is activated:
```bash
# Check Python location
which python  # Should show /path/to/venv/bin/python

# If not in venv, activate it
source venv/bin/activate
```

### Issue: Old package versions

**Solution:** Upgrade packages:
```bash
pip install --upgrade -r requirements.txt
```

---

## Environment Management Best Practices

### 1. Always Activate Before Working
```bash
# Add to your workflow
cd nba-lineup-tracking
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

### 2. Keep Dependencies Updated
```bash
# Check outdated packages
pip list --outdated

# Upgrade specific package
pip install --upgrade nba_api

# Freeze current versions
pip freeze > requirements.txt
```

### 3. Separate Dev and Prod Dependencies

**Option 1: Multiple requirement files**
```
requirements.txt          # Production dependencies
requirements-dev.txt      # Development dependencies
```

**Option 2: Use extras**
```python
# setup.py
extras_require={
    'dev': ['pytest', 'black', 'flake8', 'mypy'],
}
```

### 4. .gitignore Virtual Environment
```bash
# Already in .gitignore
venv/
__pycache__/
*.pyc
```

---

## Alternative: Using Docker

If you prefer containerization:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

```bash
# Build and run
docker build -t nba-lineup-tracker .
docker run -v $(pwd)/output:/app/output nba-lineup-tracker 0022500032
```

---

## Alternative: Using Poetry

Poetry is a modern dependency manager:

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Initialize project
poetry init

# Install dependencies
poetry install

# Run commands
poetry run python main.py 0022500032
poetry run pytest tests/
```

---

## Quick Reference

### Common Commands

| Task | Command |
|------|---------|
| Create venv | `python3 -m venv venv` |
| Activate (macOS/Linux) | `source venv/bin/activate` |
| Activate (Windows) | `venv\Scripts\activate` |
| Deactivate | `deactivate` |
| Install deps | `pip install -r requirements.txt` |
| Run app | `python main.py <game_id>` |
| Run tests | `pytest tests/ -v` |
| Check location | `which python` |
| List packages | `pip list` |

---

## Summary

**Your environment is ready when:**
- ✅ Virtual environment is activated (prompt shows `(venv)`)
- ✅ `pip list` shows all required packages
- ✅ `python -c "import nba_api"` runs without error
- ✅ `pytest tests/` passes (or shows expected results)

**Next Steps:**
1. Run a test game: `python main.py 0022300001`
2. Explore the output files: `0022300001_lineups.json` and `.csv`
3. Read the [README.md](README.md) for detailed usage

---

## Need Help?

- **Check Python version:** `python --version` (need 3.9+)
- **Check pip version:** `pip --version`
- **Verify installation:** `pip show nba_api`
- **Test import:** `python -c "import nba_api; print('OK')"`

If issues persist, consult the [README.md](README.md) or check the test documentation.