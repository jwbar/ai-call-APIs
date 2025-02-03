from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)
TWILIO_ACCOUNT_SID = "your_account_sid"
TWILIO_AUTH_TOKEN = "your_auth_token"
DEEPSEEK_API_KEY = "your_deepseek_key"

# Initiate an outbound call
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
call = client.calls.create(
    url="https://your-server.com/outbound-handler",
    to="+1234567890",
    from_="+1987654321"
)

@app.route("/outbound-handler", methods=["POST"])
def outbound_handler():
    response = VoiceResponse()
    gather = Gather(input="speech", action="/process-outbound-speech", method="POST")
    gather.say("Hi! This is an AI calling. How can we assist you today?")
    response.append(gather)
    return Response(str(response), mimetype="text/xml")

@app.route("/process-outbound-speech", methods=["POST"])
def process_outbound_speech():
    user_input = request.form.get("SpeechResult")
    
    # Call DeepSeek API here (similar to inbound example)
    ai_response = "This is where DeepSeek's response would go."
    
    response = VoiceResponse()
    response.say(ai_response)
    return Response(str(response), mimetype="text/xml")
