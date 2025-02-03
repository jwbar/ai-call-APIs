from flask import Flask, request, Response
import requests
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)
DEEPSEEK_API_KEY = "your-api-key-here"
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"  # Hypothetical endpoint

@app.route("/answer", methods=["POST"])
def answer_call():
    response = VoiceResponse()
    gather = Gather(input="speech", action="/process-speech", method="POST")
    gather.say("Hello! How can I help you?")
    response.append(gather)
    return Response(str(response), mimetype="text/xml")

@app.route("/process-speech", methods=["POST"])
def process_speech():
    user_input = request.form.get("SpeechResult")
    
    # Call DeepSeek API
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-7b",  # Replace with your model name
        "messages": [{"role": "user", "content": user_input}]
    }
    
    # Send request to DeepSeek
    try:
        ai_response = requests.post(
            DEEPSEEK_ENDPOINT,
            headers=headers,
            json=payload
        ).json()["choices"][0]["message"]["content"]
    except Exception as e:
        ai_response = "Sorry, I encountered an error. Please try again later."

    # Convert response to speech
    response = VoiceResponse()
    response.say(ai_response)
    return Response(str(response), mimetype="text/xml")
