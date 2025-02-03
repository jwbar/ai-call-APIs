from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Qwen API endpoint (replace with actual API URL)
QWEN_API_URL = "https://your-qwen-api-endpoint.com"

@app.route("/twilio/webhook", methods=["POST"])
def twilio_webhook():
    # Extract user input from Twilio request
    user_input = request.form.get("SpeechResult")  # If using Twilio Autopilot
    if not user_input:
        user_input = request.form.get("Digits")  # If using <Gather>

    # Query Qwen API
    qwen_response = query_qwen(user_input)

    # Generate TwiML response
    twiml_response = f"""
    <Response>
        <Say>{qwen_response}</Say>
    </Response>
    """
    return twiml_response

def query_qwen(prompt):
    # Replace with actual API key and headers
    headers = {"Authorization": "Bearer YOUR_QWEN_API_KEY"}
    payload = {"prompt": prompt}
    response = requests.post(QWEN_API_URL, json=payload, headers=headers)
    return response.json().get("response", "Sorry, I couldn't understand that.")

if __name__ == "__main__":
    app.run(debug=True)
