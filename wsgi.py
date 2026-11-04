import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app(os.environ.get("FLASK_ENV", "development"))

if app.config.get("RUN_EMBEDDED_WORKER"):
    from app.embedded_worker import start_embedded_worker

    start_embedded_worker(app)

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))
