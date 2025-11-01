from flask import Flask, request, jsonify, send_file
import ffmpeg
import os
import uuid

app = Flask(__name__)

BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg", "ffmpeg.exe")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/convert", methods=["POST"])
def convert():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    input_path = os.path.join(UPLOAD_FOLDER, file.filename.strip())
    file.save(input_path)
    format = request.form.get("format", "mp4").strip().lower()
    bitrate = request.form.get("bitrate", "1M").strip()
    output_filename = f"{uuid.uuid4()}.{format}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    try:
        stream = ffmpeg.input(input_path)
        if format in ["mp4", "mov", "avi", "mkv"]:
            stream = ffmpeg.output(stream, output_path, video_bitrate=bitrate)
        else:
            stream = ffmpeg.output(stream, output_path, audio_bitrate=bitrate)
        stream.run(cmd=FFMPEG_PATH, overwrite_output=True)
    except ffmpeg.Error as e:
        return jsonify({"error": e.stderr.decode() if hasattr(e, "stderr") else str(e)}), 500
    return jsonify({"status": "success", "output_file": output_filename})

@app.route("/extract-audio", methods=["POST"])
def extract_audio():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    input_path = os.path.join(UPLOAD_FOLDER, file.filename.strip())
    file.save(input_path)
    format = request.form.get("format", "mp3").strip().lower()
    output_filename = f"{uuid.uuid4()}.{format}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    try:
        ffmpeg.input(input_path).output(output_path, vn=None).run(cmd=FFMPEG_PATH, overwrite_output=True)
    except ffmpeg.Error as e:
        return jsonify({"error": e.stderr.decode() if hasattr(e, "stderr") else str(e)}), 500
    return jsonify({"status": "success", "output_file": output_filename})

@app.route("/extract-video", methods=["POST"])
def extract_video():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    input_path = os.path.join(UPLOAD_FOLDER, file.filename.strip())
    file.save(input_path)
    format = request.form.get("format", "mp4").strip().lower()
    output_filename = f"{uuid.uuid4()}.{format}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    try:
        ffmpeg.input(input_path).output(output_path, an=None).run(cmd=FFMPEG_PATH, overwrite_output=True)
    except ffmpeg.Error as e:
        return jsonify({"error": e.stderr.decode() if hasattr(e, "stderr") else str(e)}), 500
    return jsonify({"status": "success", "output_file": output_filename})

@app.route("/thumbnail", methods=["POST"])
def thumbnail():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    input_path = os.path.join(UPLOAD_FOLDER, file.filename.strip())
    file.save(input_path)
    time = request.form.get("time", "00:00:01").strip()
    output_filename = f"{uuid.uuid4()}.jpg"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    try:
        ffmpeg.input(input_path, ss=time).output(output_path, vframes=1).run(cmd=FFMPEG_PATH, overwrite_output=True)
    except ffmpeg.Error as e:
        return jsonify({"error": e.stderr.decode() if hasattr(e, "stderr") else str(e)}), 500
    return jsonify({"status": "success", "output_file": output_filename})

@app.route("/download/<filename>", methods=["GET"])
def download(filename):
    path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(port=8080, debug=True)
