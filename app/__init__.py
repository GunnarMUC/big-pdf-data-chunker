import os
from flask import Flask


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())

    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024 * 1024))
    app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "data/uploads")
    app.config["OUTPUT_FOLDER"] = os.environ.get("OUTPUT_FOLDER", "data/output")
    app.config["OCR_CACHE_FOLDER"] = os.environ.get("OCR_CACHE_FOLDER", "data/ocr_cache")
    app.config["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://redis:6379")
    app.config["OLLAMA_HOST"] = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
    app.config["OLLAMA_MODEL"] = os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")
    app.config["RQ_TIMEOUT"] = int(os.environ.get("RQ_TIMEOUT", 480))

    for folder in [app.config["UPLOAD_FOLDER"], app.config["OUTPUT_FOLDER"], app.config["OCR_CACHE_FOLDER"]]:
        os.makedirs(folder, exist_ok=True)

    from app.routes import bp
    app.register_blueprint(bp)

    return app
