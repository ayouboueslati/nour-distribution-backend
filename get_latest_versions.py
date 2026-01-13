import requests
import json

packages = [
    "fastapi", "uvicorn", "sqlalchemy", "psycopg2-binary", "asyncpg", "alembic",
    "pydantic", "pydantic-settings", "python-dotenv", "email-validator",
    "python-jose", "passlib", "bcrypt", "python-multipart", "structlog",
    "aiosmtplib", "jinja2", "reportlab", "num2words", "qrcode", "pillow",
    "anyio", "click", "pandas", "plotly", "openpyxl", "numpy"
]

def get_latest_version(package):
    try:
        # Handle extras like uvicorn[standard]
        pkg_name = package.split('[')[0]
        response = requests.get(f"https://pypi.org/pypi/{pkg_name}/json", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data["info"]["version"]
    except:
        pass
    return None

results = {}
print("Fetching versions...")
for pkg in packages:
    ver = get_latest_version(pkg)
    if ver:
        results[pkg] = ver
        print(f"{pkg}=={ver}")
    else:
        print(f"# Could not fetch version for {pkg}")
