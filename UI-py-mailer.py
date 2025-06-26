import json
import os
from functools import wraps

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from openai import OpenAI  # Use OpenAI for OpenRouter compatibility
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.secret_key = 'your_flask_secret_key'  # Replace with a secure secret key

# Set the access password (change this to your preferred password)
ACCESS_PASSWORD = 'flaskpass'

# ---------------------------------------------------
# Login Protection
# ---------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ACCESS_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash('Incorrect password')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------------------------------------------
# Main Form for Email Inputs & Selections
# ---------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    # List all .json files in the same directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_files = [f for f in os.listdir(current_dir) if f.lower().endswith('.json')]
    
    if request.method == 'POST':
        # --- Process Recipient Input ---
        recipient_type = request.form.get('recipient_type')
        emails = []

        if recipient_type == 'json':
            selected_json_file = request.form.get('json_file')
            if not selected_json_file:
                flash("No JSON file selected.")
                return redirect(request.url)
            # Read emails from the chosen JSON file
            json_path = os.path.join(current_dir, selected_json_file)
            if not os.path.exists(json_path):
                flash(f"File {selected_json_file} not found.")
                return redirect(request.url)
            try:
                with open(json_path, 'r') as file:
                    data = json.load(file)
                    emails = data.get("emails")
                    if not emails:
                        flash("JSON file missing 'emails' key or empty list.")
                        return redirect(request.url)
            except Exception as e:
                flash(f"Error reading JSON file: {e}")
                return redirect(request.url)

        elif recipient_type == 'single':
            email = request.form.get('recipient_email')
            if not email:
                flash("Please enter an email address")
                return redirect(request.url)
            emails = [email]
        else:
            flash("Invalid recipient type")
            return redirect(request.url)
        
        # --- Process Sender Selection ---
        sender_choice = request.form.get('sender')
        if sender_choice == '1':
            sender_email = "mel@katari.farm"
            sendgrid_api_key = "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"
        elif sender_choice == '2':
            sender_email = "fresh@katari.farm"
            sendgrid_api_key = "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"
        else:
            sender_email = "mel@katari.farm"
            sendgrid_api_key = "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"
        
        # --- Process LLM Selection ---
        llm_model = request.form.get('llm_model')  # "qwen" or "deepseek"
        
        # --- Get Email Details ---
        subject = request.form.get('subject')
        body = request.form.get('body')
        prompt = f"Refine this email while keeping the subject as '{subject}':\n{body}"
        
        # --- Call the Selected Generation Function ---
        if llm_model == 'qwen':
            refined_body = generate_email_content_with_qwen(prompt)
        elif llm_model == 'deepseek':
            refined_body = generate_email_content_with_deepseek(prompt)
        else:
            refined_body = generate_email_content_with_qwen(prompt)
        
        if not refined_body:
            refined_body = body  # fallback to original body if generation fails
        
        # --- Store details in session for later use ---
        session['emails'] = emails
        session['sender_email'] = sender_email
        session['sendgrid_api_key'] = sendgrid_api_key
        session['subject'] = subject
        session['body'] = refined_body  # refined (and possibly modified) body
        
        return redirect(url_for('preview'))
        
    # Render the form, providing the list of JSON files
    return render_template_string(INDEX_TEMPLATE, json_files=json_files)

# ---------------------------------------------------
# Preview & Approval Page
# ---------------------------------------------------
@app.route('/preview', methods=['GET', 'POST'])
@login_required
def preview():
    if request.method == 'POST':
        # User may have modified the body text in the preview.
        subject = session.get('subject')
        body = request.form.get('body')
        emails = session.get('emails')
        sender_email = session.get('sender_email')
        sendgrid_api_key = session.get('sendgrid_api_key')
        
        # Send emails using SendGrid
        results = send_emails(sendgrid_api_key, sender_email, emails, subject, body)
        return render_template_string(RESULT_TEMPLATE, results=results)
    
    subject = session.get('subject', '')
    body = session.get('body', '')
    return render_template_string(PREVIEW_TEMPLATE, subject=subject, body=body)

# ---------------------------------------------------
# Email Generation Functions using OpenRouter API
# ---------------------------------------------------
def generate_email_content_with_qwen(prompt):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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"
    )
    try:
        formatted_prompt = f"{prompt}\n\nPlease format the email with clear paragraphs and proper spacing between sentences."
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://katari.farm",
                "X-Title": "KatariFarms"
            },
            model="qwen/qwen-vl-plus:free",
            messages=[{"role": "user", "content": formatted_prompt}]
        )
        if completion.choices:
            generated_text = completion.choices[0].message.content.strip()
            cleaned_text = generated_text.replace("Subject:", "").strip()
            formatted_text = cleaned_text.replace(". ", ".\n\n").replace("! ", "!\n\n")
            return formatted_text
        return None
    except Exception as e:
        print(f"Error during Qwen API request: {e}")
        return None

def generate_email_content_with_deepseek(prompt):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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"
    )
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://katari.farm",
                "X-Title": "KatariFarms"
            },
            model="deepseek/deepseek-chat:free",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional email assistant. Generate well-structured emails with proper formatting and paragraphs."
                },
                {
                    "role": "user",
                    "content": f"{prompt}\nFormat with clear paragraphs and line breaks between sections."
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        if completion.choices:
            generated_text = completion.choices[0].message.content.strip()
            cleaned_text = generated_text.replace("**", "").replace("#", "").replace("Subject:", "").strip()
            formatted_text = cleaned_text.replace(". ", ".\n\n").replace("! ", "!\n\n")
            return formatted_text
        return None
    except Exception as e:
        print(f"Error during DeepSeek API request: {e}")
        return None

# ---------------------------------------------------
# Function to Send Emails via SendGrid
# ---------------------------------------------------
def send_emails(sendgrid_api_key, sender_email, to_emails_list, subject, body):
    results = {}
    html_body = body.replace("\n", "<br>")
    for to_email in to_emails_list:
        try:
            message = Mail(
                from_email=sender_email,
                to_emails=to_email,
                subject=subject,
                html_content=f"<html><body>{html_body}</body></html>"
            )
            sg = SendGridAPIClient(sendgrid_api_key)
            response = sg.send(message)
            results[to_email] = f"Sent! Status: {response.status_code}"
        except Exception as e:
            results[to_email] = f"Error: {e}"
    return results

# ---------------------------------------------------
# HTML Templates (Inline)
# ---------------------------------------------------
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Login</title>
    <style>
        body {
            background-color: #1a1a1a;
            color: #f1f1f1;
            font-family: 'Courier New', Courier, monospace;
            text-align: center;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
            height: 100vh;
        }
        h2 {
            color: #27ae60;
            margin-bottom: 20px;
        }
        form {
            margin: 0 auto;
        }
        input[type="password"] {
            width: 200px;
            padding: 6px;
            margin-bottom: 10px;
            border: none;
            border-radius: 3px;
        }
        button {
            padding: 8px 15px;
            background-color: #27ae60;
            border: none;
            border-radius: 5px;
            color: #f1f1f1;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h2>Login</h2>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul>
        {% for message in messages %}
          <li style="color:red;">{{ message }}</li>
        {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
    <form method="post">
        <input type="password" name="password" placeholder="Enter Password" required>
        <br>
        <button type="submit">Login</button>
    </form>
</body>
</html>
'''

INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Email Generator</title>
    <style>
        body {
            background-color: #1a1a1a;
            color: #f1f1f1;
            font-family: 'Courier New', Courier, monospace;
            text-align: center;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        h2 {
            color: #27ae60;
            margin-bottom: 20px;
        }
        form {
            margin: 0 auto;
            max-width: 600px;
        }
        .radio-group {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 15px;
            margin-bottom: 10px;
        }
        .radio-group label {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            margin: 0;
        }
        select,
        input[type="email"],
        input[type="text"],
        textarea {
            width: 70%;
            padding: 8px;
            margin-bottom: 8px;
            border: none;
            border-radius: 5px;
        }
        button {
            padding: 8px 20px;
            background-color: #27ae60;
            border: none;
            border-radius: 5px;
            color: #f1f1f1;
            cursor: pointer;
        }
    </style>
    <script>
        function toggleOptions() {
            var recipientType = document.querySelector('input[name="recipient_type"]:checked').value;
            var jsonDropdown = document.getElementById('json_dropdown');
            var singleEmail = document.getElementById('single_email');

            if (recipientType === 'json') {
                jsonDropdown.style.display = 'block';
                singleEmail.style.display = 'none';
            } else {
                jsonDropdown.style.display = 'none';
                singleEmail.style.display = 'block';
            }
        }
    </script>
</head>
<body onload="toggleOptions()">
    <h2>Email Generator</h2>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul>
        {% for message in messages %}
          <li style="color:red;">{{ message }}</li>
        {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
    <form method="post">
        <div class="radio-group">
            <label><input type="radio" name="recipient_type" value="json" required onclick="toggleOptions()">Batch email (JSON list)</label>
            <label><input type="radio" name="recipient_type" value="single" required onclick="toggleOptions()">Specific email address</label>
        </div>
        <div id="json_dropdown" style="display:none;">
            <select name="json_file">
                <option value="">Select a JSON file</option>
                {% for file in json_files %}
                    <option value="{{ file }}">{{ file }}</option>
                {% endfor %}
            </select>
        </div>
        <div id="single_email" style="display:none;">
            <input type="email" name="recipient_email" placeholder="Recipient Email (if single)">
        </div>
        <div class="radio-group">
            <label><input type="radio" name="sender" value="1" required>mel@katari.farm</label>
            <label><input type="radio" name="sender" value="2" required>fresh@katari.farm</label>
        </div>
        <div class="radio-group">
            <label><input type="radio" name="llm_model" value="qwen" required>Qwen</label>
            <label><input type="radio" name="llm_model" value="deepseek" required>DeepSeek</label>
        </div>
        <input type="text" name="subject" placeholder="Email Subject" required>
        <br>
        <textarea name="body" placeholder="Email Body" rows="8" required></textarea>
        <br>
        <button type="submit">Generate and Preview Email</button>
    </form>
</body>
</html>
'''

PREVIEW_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Preview Email</title>
    <style>
        body {
            background-color: #1a1a1a;
            color: #f1f1f1;
            font-family: 'Courier New', Courier, monospace;
            text-align: center;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        h2 {
            color: #27ae60;
            margin-bottom: 20px;
        }
        form {
            margin: 0 auto;
            max-width: 600px;
        }
        input[type="text"] {
            width: 70%;
            padding: 8px;
            margin-bottom: 8px;
            border: none;
            border-radius: 5px;
        }
        textarea {
            width: 70%;
            padding: 8px;
            margin-bottom: 8px;
            border: none;
            border-radius: 5px;
        }
        button {
            padding: 8px 20px;
            background-color: #27ae60;
            border: none;
            border-radius: 5px;
            color: #f1f1f1;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h2>Preview Email</h2>
    <form method="post">
        <input type="text" name="subject" value="{{ subject }}" readonly>
        <br>
        <textarea name="body" rows="12">{{ body }}</textarea>
        <br>
        <button type="submit">Send Email</button>
    </form>
</body>
</html>
'''

RESULT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Email Sending Results</title>
    <style>
        body {
            background-color: #1a1a1a;
            color: #f1f1f1;
            font-family: 'Courier New', Courier, monospace;
            text-align: center;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        h2 {
            color: #27ae60;
            margin-bottom: 20px;
        }
        .result {
            margin: 10px 0;
        }
        a {
            color: #27ae60;
        }
    </style>
</head>
<body>
    <h2>Email Sending Results</h2>
    {% for email, status in results.items() %}
        <div class="result">{{ email }}: {{ status }}</div>
    {% endfor %}
    <br>
    <a href="{{ url_for('index') }}">Send Another Email</a>
</body>
</html>
'''

# ---------------------------------------------------
# Run the Flask App on Port 5005
# ---------------------------------------------------
if __name__ == '__main__':
    app.run(port=5005, host="0.0.0.0", debug=True)
