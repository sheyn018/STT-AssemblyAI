import os
import requests
import assemblyai as aai
import uuid
from dotenv import load_dotenv

load_dotenv()

# AssemblyAI API Key
aai.settings.api_key = os.getenv('ASSEMBLY_API_KEY')

# Twilio Settings
TWILIO_SAMPLE_RATE = 8000  # Hz

# n8n Webhook URL
N8N_WEBHOOK_URL = "https://insiderperks.app.n8n.cloud/webhook-test/83427a82-fb9a-4a79-8a59-22f1752ac7bb"

class TwilioTranscriber(aai.RealtimeTranscriber):
    def __init__(self):
        super().__init__(
            on_data=self.on_data,
            on_error=self.on_error,
            on_open=self.on_open,
            on_close=self.on_close,
            sample_rate=TWILIO_SAMPLE_RATE,
            encoding=aai.AudioEncoding.pcm_mulaw
        )
        self.final_transcript = ""  # Stores the final transcript
        self.session_id = str(uuid.uuid4())  # Generate a unique session ID for this call
        self.twilio_call_sid = None  # Will be set from main.py if available
        print(f"🆔 Generated session ID: {self.session_id}")

    def on_open(self, session_opened: aai.RealtimeSessionOpened):
        """Called when the transcription session is opened."""
        print("✅ Transcription session started. Session ID:", session_opened.session_id)
        print(f"✅ Call session ID: {self.session_id}")

    def on_data(self, transcript: aai.RealtimeTranscript):
        """Handles incoming transcription data."""
        if not transcript.text:
            return  # Ignore empty responses

        if isinstance(transcript, aai.RealtimeFinalTranscript):
            # Store final transcript when the user stops speaking
            self.final_transcript += transcript.text + " "
            print(f"\n🎤 Final: {transcript.text}")  # Print when speech segment ends
            self.send_to_n8n(transcript.text)  # Send only the final part to n8n
        else:
            # Print partial transcript in real-time
            print(f"📝 {transcript.text}", end="\r", flush=True)  # Print partial text live

    def on_error(self, error: aai.RealtimeError):
        """Handles errors during transcription."""
        print("❌ An error occurred:", error)

    def on_close(self):
        """Handles session closure."""
        print("🔴 Transcription session closed.")
        
        # Send the complete transcript when the call ends
        if self.final_transcript.strip():
            print(f"📝 Complete transcript: {self.final_transcript.strip()}")
            try:
                params = {
                    "transcription": self.final_transcript.strip(), 
                    "complete": "true",
                    "session_id": self.session_id
                }
                
                # Add Twilio call SID if available
                if self.twilio_call_sid:
                    params["call_sid"] = self.twilio_call_sid
                
                response = requests.get(N8N_WEBHOOK_URL, params=params)
                if response.status_code == 200:
                    print("✅ Complete transcript sent successfully to n8n.")
                    print(f"📊 Response from webhook: {response.text}")
                else:
                    print(f"⚠️ Failed to send complete transcript to n8n. Status Code: {response.status_code}")
            except Exception as e:
                print(f"❌ Error sending complete transcript to n8n: {e}")

    def send_to_n8n(self, transcript):
        """Sends the final transcript to the n8n webhook using GET request."""
        if not transcript.strip():
            return  # Don't send empty transcripts

        params = {
            "transcription": transcript.strip(),
            "session_id": self.session_id
        }
        
        # Add Twilio call SID if available
        if self.twilio_call_sid:
            params["call_sid"] = self.twilio_call_sid
        
        try:
            response = requests.get(N8N_WEBHOOK_URL, params=params)
            if response.status_code == 200:
                print("✅ Transcript sent successfully to n8n.")
                print(f"📊 Response from webhook: {response.text}")
            else:
                print(f"⚠️ Failed to send transcript to n8n. Status Code: {response.status_code}")
        except Exception as e:
            print(f"❌ Error sending transcript to n8n: {e}")
