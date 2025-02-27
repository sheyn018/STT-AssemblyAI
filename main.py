from flask import Flask, request, Response
from flask_sock import Sock
import json
import base64
from twilio_transcriber import TwilioTranscriber

PORT = 5000
DEBUG = False
INCOMING_CALL_ROUTE = '/'
WEBSOCKET_ROUTE = '/realtime'

app = Flask(__name__)
sock = Sock(app)

# Dictionary to store transcriber instances by connection ID
transcribers = {}

@app.route(INCOMING_CALL_ROUTE, methods=['GET', 'POST'])
def receive_call():
    if request.method == 'POST':
        # Get Twilio call SID if available
        call_sid = request.values.get('CallSid', None)
        if call_sid:
            print(f"📞 Incoming call with SID: {call_sid}")
        
        xml = f"""
<Response>
    <Say>
        Speak to see your speech transcribed in real-time.
    </Say>
    <Connect>
        <Stream url='wss://{request.host}{WEBSOCKET_ROUTE}' />
    </Connect>
</Response>
""".strip()
        return Response(xml, mimetype='text/xml')
    else:
        return "Real-time phone call transcription app"

@sock.route(WEBSOCKET_ROUTE)
def transcription_websocket(ws):
    print('WebSocket connection established')
    
    # Create a new transcriber instance for this connection
    connection_transcriber = TwilioTranscriber()
    
    # First message contains connection info
    data = json.loads(ws.receive())
    if data['event'] == "connected":
        # Store the streamSid as the connection ID
        connection_id = data.get('streamSid', 'unknown')
        transcribers[connection_id] = connection_transcriber
        
        # Extract call SID if available in the start message
        call_sid = data.get('start', {}).get('callSid', None)
        if call_sid:
            connection_transcriber.twilio_call_sid = call_sid
            print(f"📞 Associated call SID: {call_sid} with session ID: {connection_transcriber.session_id}")
        
        connection_transcriber.connect()
        print(f'Transcriber connected for stream: {connection_id}')

    while True:
        try:
            data = json.loads(ws.receive())
            match data['event']:
                case "start":
                    # Extract call SID if available in the start message
                    call_sid = data.get('start', {}).get('callSid', None)
                    if call_sid:
                        connection_transcriber.twilio_call_sid = call_sid
                        print(f"📞 Associated call SID: {call_sid} with session ID: {connection_transcriber.session_id}")
                    print('Twilio started streaming')

                case "media":
                    payload_b64 = data['media']['payload']
                    payload_mulaw = base64.b64decode(payload_b64)
                    connection_transcriber.stream(payload_mulaw)  # Real-time processing

                case "stop":
                    print('Twilio stopped streaming')
                    connection_transcriber.close()  # Send final transcript
                    print('Transcriber closed')
                    
                    # Clean up the transcriber instance
                    if connection_id in transcribers:
                        del transcribers[connection_id]
                    
                    return  # End the WebSocket connection
        except Exception as e:
            print(f"Error processing WebSocket data: {e}")
            if connection_id in transcribers:
                del transcribers[connection_id]
            break

if __name__ == "__main__":
    app.run(port=PORT, debug=DEBUG)
