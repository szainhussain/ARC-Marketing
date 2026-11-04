import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app(os.environ.get("FLASK_ENV", "development"))

# The embedded worker (RUN_EMBEDDED_WORKER) is started by gunicorn.conf.py in
# the web server process only, never during `flask db upgrade` or other CLI
# commands.

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))
