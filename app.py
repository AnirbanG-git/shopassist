from flask import Flask, redirect, url_for, render_template, request, jsonify
from functions import initialize_conversation, initialize_conv_reco, get_chat_completions, moderation_check,intent_confirmation_layer, recommendation_validation, gen_updated_latop_data

import openai
import pandas as pd
import json
import threading

# Load the OpenAI API key from a file
openai.api_key = open("OpenAI_API_Key.txt", "r").read().strip()

# Initialize Flask app
app = Flask(__name__)

# Global variable to track task status
task_status = {"status": "Not Started"}  # Possible statuses: "Not Started", "In Progress", "Completed"

# Initialize conversation and conversation_bot
conversation_bot = []
conversation = initialize_conversation()
introduction = get_chat_completions(conversation)
conversation.append({"role": "assistant", "content": introduction})
conversation_bot.append({'bot': introduction})
top_3_laptops = None

# Default route to render the chat interface
@app.route("/")
def default_func():
    global conversation, conversation_bot, top_3_laptops
    return render_template("index_chat.html", name = conversation_bot)

# Route to end the conversation and restart the chat
@app.route("/end_conv", methods = ["POST", "GET"])
def end_conv():
    global conversation_bot, conversation, top_3_laptops
    conversation_bot = []
    conversation = initialize_conversation()
    introduction = get_chat_completions(conversation)
    conversation.append({"role": "assistant", "content": introduction})
    conversation_bot.append({'bot': introduction})
    top_3_laptops = None
    return redirect(url_for("default_func"))

# Route to handle the user's chat messages and respond with recommendations
@app.route("/chat", methods = ["POST"])
def chat():
    global conversation_bot, conversation, top_3_laptops, conversation_reco
    user_input = request.form.get("user_input_message")

    # Add a prompt to remind the assistant of its role (laptop-focused)
    prompt = '. Remember your system message and that you are an intelligent laptop assistant. So, you only help with questions around laptop. If user asks about something else, tell him explicitly that you answer only laptop related questions.'

    # Check user input for inappropriate content
    moderation = moderation_check(user_input)
    if moderation == 'Flagged':
        print("Sorry, this message has been flagged. Please restart your conversation.")
        return redirect(url_for("end_conv"))

     # If top 3 laptops is not yet retrieved, use the LLM to ask more questions.
     # If top 3 laptops are fetched, recommend the laptions, and remind the user to end the conversation
    if top_3_laptops is None:

        conversation.append({"role": "user", "content": user_input + prompt})
        conversation_bot.append({"user": user_input})

        # Get chatbot response
        response_assistant = get_chat_completions(conversation)

        # Check the assistant's response for flagged content
        moderation = moderation_check(response_assistant)
        if moderation == 'Flagged':
            print("Sorry, this message has been flagged. Please restart your conversation.")
            return redirect(url_for("end_conv"))


        # Verify if the intent confirmation is complete
        confirmation = intent_confirmation_layer(response_assistant)

        print("Intent Confirmation Yes/No:",confirmation.get('result'))

        # If confirmation is incomplete, continue the conversation
        if "No" in confirmation.get('result'):
            conversation.append({"role": "assistant", "content": str(response_assistant)})
            conversation_bot.append({"bot":  str(response_assistant)})
            print("\n" + str(response_assistant) + "\n")

        else:
            # If the confirmation is successful, proceed to generate laptop recommendations
            print("\n" + str(response_assistant) + "\n")
            print('\n' + "Variables extracted!" + '\n')

            print("Thank you for providing all the information. Kindly wait, while I fetch the products: \n")
            conversation.append({"role": "user", "content": json.dumps(response_assistant)})
            conversation.append({"role": "assistant", "content": "Thank you for providing all the information. Kindly wait, while I fetch the top 3 laptops from the catalogue:"})
            conversation_bot.append({"bot":  "Thank you for providing all the information. Kindly wait, while I fetch the products:"})

            # Get the top 3 laptops based on the user's input
            top_3_laptops = get_chat_completions(conversation)
            print("top 3 laptops are", top_3_laptops)

            # Validate recommendations based on extracted variables
            validated_reco = recommendation_validation(top_3_laptops)

            # If no laptops match the user's preferences, notify the user
            if len(validated_reco) == 0:
                print("Sorry, we do not have laptops that match your requirement. Connecting you to a human assistant.")
                conversation_bot.append({"bot":  "Sorry, we do not have laptops that match your requirement. Connecting you to a human assistant."})

            # Initialize a new conversation for recommendations
            conversation_reco = initialize_conv_reco(validated_reco)
            recommendation = get_chat_completions(conversation_reco)

            # Check the moderation status of the recommendation
            moderation = moderation_check(recommendation)
            if moderation == 'Flagged':
                print("Sorry, this message has been flagged. Please restart your conversation.")
                return redirect(url_for("end_conv"))

            # Add recommendations to the conversation history
            conversation_reco.append({"role": "user", "content": "This is my user profile" + str(response_assistant)})
            conversation_reco.append({"role": "assistant", "content": str(recommendation)})
            conversation_bot.append({"bot":  recommendation})

            print(str(recommendation) + '\n')
    else:
        # If recommendations are already provided, remind the user to end the conversation
        if conversation_reco is not None:
            conversation_bot.append({"user":  user_input})
            conversation_bot.append({"bot":  "Top 3 recommendations already provided. Please end the conversation."})    
        else:    
            # Continue conversation with additional user input
            conversation_reco.append({"role": "user", "content": user_input})
            conversation_bot.append({"user":  user_input})

            # Get chatbot response for the follow-up conversation
            response_asst_reco = get_chat_completions(conversation_reco)

            # Check moderation for the assistant's response
            moderation = moderation_check(response_asst_reco)
            if moderation == 'Flagged':
                print("Sorry, this message has been flagged. Please restart your conversation.")
                return redirect(url_for("end_conv"))

            # Append response to the conversation history
            print('\n' + response_asst_reco + '\n')
            conversation.append({"role": "assistant", "content": response_asst_reco})
            response_asst_reco = response_asst_reco.replace("\n", "<br/><br/>")
            conversation_bot.append({"bot":  response_asst_reco})

    # Redirect back to the default chat route
    return redirect(url_for("default_func"))

# Function for CSV generation
def gen_updated_laptop_data():
    global task_status
    task_status["status"] = "In Progress"
    task_status["progress"] = 0

    # Generate the updated laptop data CSV
    gen_updated_latop_data()
    task_status["status"] = "Completed"

# Route to start the CSV generation task
@app.route("/admin", methods=["GET"])
def admin():
    global task_status
    task_status["status"] = "Not Started"  # Reset status before starting new task
    return render_template("admin.html")

# Route to start the CSV generation asynchronously
@app.route("/start_generation", methods=["POST"])
def start_generation():
    global task_status
    # Start the generation in a separate thread to prevent blocking
    if task_status["status"] == "Not Started":
        thread = threading.Thread(target=gen_updated_laptop_data)
        thread.start()
    return jsonify({"message": "Generation started"}), 202

# Route to check the status of CSV generation
@app.route("/check_status", methods=["GET"])
def check_status():
    return jsonify(task_status), 200

if __name__ == '__main__':
    app.run(debug=True)