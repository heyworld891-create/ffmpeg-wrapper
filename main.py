from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import io

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

API_URL = "http://127.0.0.1:8080"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    conversions = db.relationship("Conversion", backref="user", lazy=True)
class Conversion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    operation = db.Column(db.String(100), nullable=False, default="convert")
    format = db.Column(db.String(50))
    bitrate = db.Column(db.String(50))
    output_filename = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
def current_user():
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return render_template("register.html", error="Please fill in all fields")

        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="Username already exists")

        hashed_pw = generate_password_hash(password)
        user = User(username=username, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            return render_template("login.html", error="Invalid username or password")
        session["user_id"] = user.id
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    download_url = None
    error = None

    if request.method == "POST":
        file = request.files.get("file")
        operation = request.form.get("operation", "convert")
        format = request.form.get("format", "mp4")
        bitrate = request.form.get("bitrate", "1M")
        time = request.form.get("time", "00:00:01")

        if not file:
            error = "Please select a file"
        else:
            files = {"file": (file.filename, file.stream, file.mimetype)}
            data = {"format": format, "bitrate": bitrate, "time": time}

            endpoint_map = {
                "convert": "convert",
                "extract-audio": "extract-audio",
                "extract-video": "extract-video",
                "thumbnail": "thumbnail"
            }
            endpoint = endpoint_map.get(operation, "convert")

            try:
                response = requests.post(f"{API_URL}/{endpoint}", files=files, data=data)
                if response.status_code == 200:
                    json_data = response.json()
                    output_file = json_data["output_file"]

                    conversion = Conversion(
                        filename=file.filename,
                        operation=operation,
                        format=format,
                        bitrate=bitrate,
                        output_filename=output_file,
                        user_id=user.id,
                    )
                    db.session.add(conversion)
                    db.session.commit()
                    download_url = url_for("download", filename=output_file)
                else:
                    error = f"{operation} failed: {response.text}"
            except requests.exceptions.RequestException:
                error = "Conversion API unreachable."

    conversions = Conversion.query.filter_by(user_id=user.id).order_by(Conversion.timestamp.desc()).all()
    return render_template("index.html", user=user, conversions=conversions, download_url=download_url, error=error)

@app.route("/download/<filename>")
def download(filename):
    try:
        response = requests.get(f"{API_URL}/download/{filename}", stream=True)
        if response.status_code == 200:
            return send_file(io.BytesIO(response.content), as_attachment=True, download_name=filename)
        return render_template("index.html", error="File not found on conversion server")
    except requests.exceptions.RequestException:
        return render_template("index.html", error="Conversion API unreachable")
with app.app_context(): 
    db.create_all()
if __name__ == "__main__":
    app.run(port=5000, debug=True)
