from flask import Flask, request, jsonify
import assemblyai as aai
import os

app = Flask(__name__)

# Set AssemblyAI API Key
aai.settings.api_key = ""

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    if "audio" not in request.files:
        print("No audio file provided.")  # Debugging print statement
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    file_path = os.path.join("uploads", audio_file.filename)
    
    # Save the file locally
    audio_file.save(file_path)
    print(f"File saved at {file_path}")  # Debugging print statement

    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(file_path)
        print(f"Transcription: {transcript.text}")  # Debugging print statement

        return jsonify({"transcription": transcript.text})
    
    except Exception as e:
        print(f"Error in transcription: {e}")  # Debugging print statement
        return jsonify({"error": "Transcription failed"}), 500

if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    app.run(debug=True)
