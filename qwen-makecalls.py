import os
from twilio.rest import Client
import requests
from flask import Flask, request

# Initialize Twilio client
TWILIO_ACCOUNT_SID = "your_twilio_account_sid"
TWILIO_AUTH_TOKEN = "your_twilio_auth_token"
TWILIO_PHONE_NUMBER = "your_twilio_phone_number"

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Qwen API endpoint
QWEN_API_URL = "https://your-qwen-api-endpoint.com"
QWEN_API_KEY = "your_qwen_api_key"

# Flask app for handling call flow
app = Flask(__name__)

# Function to query Qwen API
def query_qwen(prompt):
    headers = {"Authorization": f"Bearer {QWEN_API_KEY}"}
    payload = {"prompt": prompt}
    response = requests.post(QWEN_API_URL, json=payload, headers=headers)
    return response.json().get("response", "Sorry, I couldn't generate a response.")

# Function to initiate an outbound call
def initiate_call(to_number, talking_point):
    # Generate initial message using Qwen
    initial_message = query_qwen(f"Start a conversation about: {talking_point}")

    # Create TwiML to play the initial message and gather user input
    twiml = f"""
    <Response>
        <Say>{initial_message}</Say>
        <Gather input="speech" action="/handle_response" method="POST" timeout="5" speechTimeout="auto">
            <Say>Please respond now.</Say>
        </Gather>
    </Response>
    """

    # Initiate the call
    call = client.calls.create(
        to=to_number,
        from_=TWILIO_PHONE_NUMBER,
        twiml=twiml
    )
    print(f"Call initiated to {to_number}. Call SID: {call.sid}")

# Flask route to handle user responses
@app.route("/handle_response", methods=["POST"])
def handle_response():
    # Extract user input from Twilio request
    user_input = request.form.get("SpeechResult")
    if not user_input:
        user_input = "No input detected."

    # Query Qwen for a response
    ai_response = query_qwen(f"User said: {user_input}. Continue the conversation.")

    # Generate TwiML to play the AI's response
    twiml_response = f"""
    <Response>
        <Say>{ai_response}</Say>
        <Gather input="speech" action="/handle_response" method="POST" timeout="5" speechTimeout="auto">
            <Say>Please respond now.</Say>
        </Gather>
    </Response>
    """
    return twiml_response

# Function to run the script
def run_script(phone_numbers, talking_points):
    for i, number in enumerate(phone_numbers):
        if i < len(talking_points):
            talking_point = talking_points[i]
            print(f"Calling {number} with talking point: {talking_point}")
            initiate_call(number, talking_point)
        else:
            print(f"No talking point available for {number}. Skipping.")
