
# ShopAssist - Laptop Recommendation Chatbot

ShopAssist is an intelligent chatbot developed to assist users in finding the best laptop based on their specific needs and preferences. It uses OpenAI's GPT models to provide dynamic and personalized recommendations for laptops, making the process of choosing the right laptop easier and more efficient. The chatbot is built from scratch using Flask as the backend framework and integrates OpenAI's Function Calling API for handling user queries and executing specific functions.

## Features

- **Interactive Conversations**: The chatbot engages in dynamic conversations with users to understand their laptop requirements such as GPU intensity, display quality, portability, multitasking needs, processing speed, and budget.
- **Personalized Recommendations**: Based on the user’s input, the chatbot provides the top 3 laptop recommendations tailored to their preferences.
- **Input Moderation**: The chatbot includes a moderation layer that flags inappropriate content and ensures the conversation stays professional.
- **Asynchronous CSV Generation**: The app includes an admin interface to asynchronously generate and update a catalog of laptops in CSV format, ensuring the data stays fresh.
- **Function Calling API**: Leveraging OpenAI’s Function Calling API, the chatbot dynamically invokes specific functions to execute tasks such as validating user requirements and comparing laptops.

## Technologies Used

- **Flask** (Version 3.0.3): A lightweight Python web framework used to handle routes, HTTP requests, and manage user sessions.
- **OpenAI API** (Version 1.44.0): The official Python library for interacting with OpenAI’s GPT models.
- **Pandas** (Version 2.2.1): A powerful data analysis library used to manage and filter laptop data from CSV files.
- **Threading Module**: Used for asynchronous CSV generation without blocking the chatbot's main functionality.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/AnirbanG-git/shopassist.git
   cd shopassist
   ```

2. Set up a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Add your OpenAI API key:
   - Create a file named `OpenAI_API_Key.txt` in the root of the project.
   - Add your OpenAI API key to this file.

5. Run the Flask app:
   ```bash
   python app.py
   ```

6. Access the app in your browser:
   ```
   http://127.0.0.1:5000/
   ```

## How It Works

### 1. Conversation Flow
The chatbot starts by asking users about their laptop requirements, such as preferred GPU intensity, display quality, and budget. It then processes this information to generate recommendations using OpenAI’s GPT model.

### 2. Function Calling
The chatbot uses the Function Calling API to dynamically execute specific functions based on the user’s responses:
- `compare_laptops_with_user`: Compares the user’s needs with the available laptops and recommends the top 3 options.
- `get_user_info`: Gathers and structures the user's requirements into a Python dictionary for further processing.

### 3. Admin Interface
The admin interface allows for the asynchronous generation of an updated laptop catalog (`updated_laptop.csv`). The status of the CSV generation is tracked and displayed in real-time to the admin user.

## Routes

- **Chat Interface**: `http://127.0.0.1:5000/` – The main user interface for chatting with the ShopAssist chatbot.
- **Admin Panel**: `http://127.0.0.1:5000/admin` – The admin interface for generating and updating the laptop catalog.

