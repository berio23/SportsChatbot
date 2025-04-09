from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Home route to render the chat interface
@app.route("/")
def index():
    return render_template("chat.html")

# Route to send user message to the Rasa bot and return its response
@app.route("/send_message", methods=["POST"])
def send_message():
    # Get the user's message from the POST request form data
    user_message = request.form.get("message")
    
    # Prepare the payload for Rasa REST endpoint
    payload = {
        "sender": "user",  # In production, you might want to use unique IDs per user
        "message": user_message
    }
    
    try:
        # Send the user's message to the Rasa REST endpoint.
        # Make sure your Rasa server is running with the --enable-api flag.
        response = requests.post("http://localhost:5005/webhooks/rest/webhook", json=payload)
        if response.status_code == 200:
            responses = response.json()
        else:
            responses = [{"text": "There was an error contacting the bot."}]
    except Exception as e:
        responses = [{"text": f"Request error: {e}"}]
    
    # Return the response messages as JSON
    return jsonify(responses)

if __name__ == '__main__':
    app.run(debug=True)
