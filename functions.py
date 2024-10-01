import openai
import pandas as pd
import json
from tenacity import retry, wait_random_exponential, stop_after_attempt

# Set model and data paths
MODEL = 'gpt-3.5-turbo'
LAPTOP_DATA_ORIGINAL = 'laptop_data.csv'
LAPTOP_DATA = 'updated_laptop.csv'

# Define function descriptions for the Function Calling API
function_descriptions = [
            {
                "name": "compare_laptops_with_user",
                "description": "Get the top 3 laptops from the catalogue, that best match what the user is asking for based on 'GPU intensity','Display quality','Portability','Multitasking','Processing speed' & 'Budget'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "GPU intensity": {
                            "type": "string",
                            "description": "The user's requirement for GPU capacity, classified as 'low', 'medium', or 'high'."
                        },
                        "Display quality": {
                            "type": "string",
                            "description": "The user's requirement for the laptop's display quality, classified as 'low', 'medium', or 'high'."
                        },
                        "Portability": {
                            "type": "string",
                            "description": "The user's requirement for portability, classified as 'low', 'medium', or 'high'."
                        },
                        "Multitasking": {
                            "type": "string",
                            "description": "The user's requirement for multitasking capability, classified as 'low', 'medium', or 'high'."
                        },
                        "Processing speed": {
                            "type": "string",
                            "description": "The user's requirement for processing speed, classified as 'low', 'medium', or 'high'."
                        },
                        "Budget": {
                            "type": "integer",
                            "description": "The user's maximum budget for the laptop, as an integer in INR."
                        }
                    },
                    "required": ["GPU intensity", "Display quality", "Portability", "Multitasking", "Processing speed", "Budget"]
                }
            },
            {
                "name": "get_user_info",
                "description": "Returns the user laptop information in python dictionary format after gathering all the details.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "GPU intensity": {
                            "type": "string",
                            "description": "GPU intensity classified as low, medium, or high."
                        },
                        "Display quality": {
                            "type": "string",
                            "description": "Display quality classified as low, medium, or high."
                        },
                        "Portability": {
                            "type": "string",
                            "description": "Portability classified as low, medium, or high."
                        },
                        "Multitasking": {
                            "type": "string",
                            "description": "Multitasking capability classified as low, medium, or high."
                        },
                        "Processing speed": {
                            "type": "string",
                            "description": "Processing speed classified as low, medium, or high."
                        },
                        "Budget": {
                            "type": "integer",
                            "description": "The maximum budget."
                        }
                    },
                    "required": ["GPU intensity", "Display quality", "Portability", "Multitasking", "Processing speed", "Budget"]
                }
            }

        ]


# Function to extract user requirement into a dictionary
def get_user_info(function_args):
    """
    Parameters:
    GPU_intensity (str): GPU intensity required by the user.
    Display_quality (str): Display quality required by the user.
    Portability (str): Portability required by the user.
    Multitasking (str): Multitasking capability required by the user.
    Processing_speed (str): Processing speed required by the user.
    Budget (int): Budget of the user.

    Returns:
    dict: A dictionary containing the extracted information (only keys that exist in function_args).
    """

    user_info = {}

    if "GPU intensity" in function_args:
        user_info["GPU intensity"] = function_args["GPU intensity"]

    if "Display quality" in function_args:
        user_info["Display quality"] = function_args["Display quality"]

    if "Portability" in function_args:
        user_info["Portability"] = function_args["Portability"]

    if "Multitasking" in function_args:
        user_info["Multitasking"] = function_args["Multitasking"]

    if "Processing speed" in function_args:
        user_info["Processing speed"] = function_args["Processing speed"]

    if "Budget" in function_args:
        user_info["Budget"] = int(function_args["Budget"])

    return user_info


# Initialize the conversation with a system message
def initialize_conversation():
    '''
    Returns a list [{"role": "system", "content": system_message}]
    '''

    delimiter = "####"

    # Example user preferences for the conversation
    example_user_dict = {'GPU intensity': "high",
                        'Display quality':"high",
                        'Portability': "low",
                        'Multitasking': "high",
                        'Processing speed': "high",
                        'Budget': 150000}

    # Placeholder values to be filled by the assistant
    example_user_req = {'GPU intensity': "_",
                        'Display quality': "_",
                        'Portability': "_",
                        'Multitasking': "_",
                        'Processing speed': "_",
                        'Budget': "_"}

     # System message defining the assistant's behavior and objectives
    system_message = f"""
    You are an intelligent laptop gadget expert and your goal is to find the best laptop for a user.
    You need to ask relevant questions and understand the user profile by analysing the user's responses.
    You final objective is to fill the values for the different keys ('GPU intensity','Display quality','Portability','Multitasking','Processing speed','Budget') in the python dictionary and be confident of the values.
    These key value pairs define the user's profile.
    The python dictionary looks like this
    {{'GPU intensity': 'values','Display quality': 'values','Portability': 'values','Multitasking': 'values','Processing speed': 'values','Budget': 'values'}}
    The value for 'Budget' should be a numerical value extracted from the user's response.
    The values for all keys, except 'Budget', should be 'low', 'medium', or 'high' based on the importance of the corresponding keys, as stated by user.
    All the values in the example dictionary are only representative values.
    {delimiter}
    Here are some instructions around the values for the different keys. If you do not follow this, you'll be heavily penalised:
    - The values for all keys, except 'Budget', should strictly be either 'low', 'medium', or 'high' based on the importance of the corresponding keys, as stated by user.
    - The value for 'Budget' should be a numerical value extracted from the user's response.
    - 'Budget' value needs to be greater than or equal to 25000 INR. If the user says less than that, please mention that there are no laptops in that range.
    - Do not randomly assign values to any of the keys.
    - The values need to be inferred from the user's response.
    {delimiter}

    To fill the dictionary, you need to have the following chain of thoughts:
    Follow the chain-of-thoughts below to construct the final updated python dictionary for the keys as described in {example_user_req}. \n
    Once you have gathered all the required values for the dictionary, call the function `get_user_info`.
    {delimiter}
    Thought 1: Ask a question to understand the user's profile and requirements. \n
    If their primary use for the laptop is unclear. Ask followup questions to understand their needs.
    You are trying to fill the values of all the keys {{'GPU intensity','Display quality','Portability','Multitasking','Processing speed','Budget'}} in the python dictionary by understanding the user requirements.
    Identify the keys for which you can fill the values confidently using the understanding. \n
    Remember the instructions around the values for the different keys.
    If the necessary information has been extracted, only then proceed to the next step. \n
    Otherwise, rephrase the question to capture their profile clearly. \n

    {delimiter}
    Thought 2: Now, you are trying to fill the values for the rest of the keys which you couldn't in the previous step.
    Remember the instructions around the values for the different keys.
    Ask questions you might have for all the keys to strengthen your understanding of the user's profile.
    If yes, move to the next Thought. If no, ask question on the keys whose values you are unsure of. \n
    It is a good practice to ask question with a sound logic as opposed to directly citing the key you want to understand value for.
    {delimiter}

    {delimiter}
    Thought 3: Check if you have correctly updated the values for the different keys in the python dictionary.
    If you are not confident about any of the values, ask clarifying questions.
    {delimiter}

    {delimiter}
    Thought 4: If any key is missing or not specified, please ask the user again for the specification.
    {delimiter}

    {delimiter}
    Here is a sample conversation between the user and assistant. This is just a sample. Don't start with this conversation. Follow the sample, and always remember the following rules.
    1. Don't put the words such as "User:" or "Assistant:". 
    2. Don't put double quotes at the beginning or end every time.
    3. You don't need to strictly start the conversation with same sentence every time.
    Assistant: "Hello! I'm here to help you find the best laptop that suits your needs. Could you please share with me what you primarily use or plan to use your laptop for? This will help me understand your requirements better."
    User: "Hi, I am an editor."
    Assistant: "Great! As an editor, you likely require a laptop that can handle demanding tasks. Hence, the laptop should have high multitasking capability. You would also need a high end display for better visuals and editing. May I know what kind of work do you primarily focus on? Are you more involved in video editing, photo editing, or both? Understanding the specific type of editing work will help me tailor my recommendations accordingly. Let me know if my understanding is correct until now."
    User: "I primarily work with After Effects."
    Assistant: "Thank you for providing that information. Working with After Effects involves working with graphics, animations, and rendering, which will require high GPU. Do you work with high-resolution media files, such as 4K videos or RAW photos? Understanding your file sizes will help determine the storage capacity and processing power needed."
    User: "Yes, sometimes I work with 4K videos as well."
    Assistant: "Thank you for the information. Processing 4K vidoes will require a good processor and high GPU. I think we have already determined earlier that you need a high GPU. To ensure I have a complete understanding of your needs, I have one more question: Are you frequently on the go and require a laptop that is lightweight and easy to carry, or do you primarily work from a stationary location?"
    User: "Yes, sometimes I travel but do not carry my laptop."
    Assistant:"Could you kindly let me know your budget for the laptop? This will help me find options that fit within your price range while meeting the specified requirements."
    User: "my max budget is 1.5lakh inr"
    Assistant: "{example_user_dict}"
    {delimiter}

    {delimiter}
    Mandatory Instruction: You must start with a short welcome message and encourage the user to share their requirements. Example is given below.
    Hello! I'm here to help you find the best laptop that suits your needs. Could you please share with me what you primarily use or plan to use your laptop for? This will help me understand your requirements better.    
    {delimiter}
    """
    conversation = [{"role": "system", "content": system_message}]
    # print(conversation)
    # conversation = system_message
    return conversation


# Function to get chat completions with optional function calling
@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
def get_chat_completions(input, func_call = True):

    if func_call:
        # Call OpenAI API with function calling enabled
        chat_completion = openai.chat.completions.create(
                model = MODEL,
                messages = input,
                functions =  function_descriptions,
                function_call = 'auto',            
                seed = 2345)
    else:
         # Call OpenAI API without function calling
        chat_completion = openai.chat.completions.create(
                model = MODEL,
                messages = input,       
                seed = 2345)        

    # Check if a function call was invoked
    function_call = chat_completion.choices[0].message.function_call

    if function_call is None:
        output = chat_completion.choices[0].message.content
    else:
        # If a function is called, execute the function
        function_name = function_call.name
        function_args = json.loads(function_call.arguments)

        # Dynamically call the function from the globals() dictionary
        function_to_call = globals()[function_name]
        output = function_to_call(function_args)

    return output


# Function to check for inappropriate content using OpenAI moderation API
def moderation_check(user_input):

    if isinstance(user_input, dict):
        return "Not Flagged"

    # Call the OpenAI API to perform moderation on the user's input.
    response = openai.moderations.create(input=user_input)

    # Extract the moderation result from the API response.
    moderation_output = response.results[0].flagged
    # Check if the input was flagged by the moderation system.
    if response.results[0].flagged == True:
        # If flagged, return "Flagged"
        return "Flagged"
    else:
        # If not flagged, return "Not Flagged"
        return "Not Flagged"


# Function to confirm if user intent is fully captured    
def intent_confirmation_layer(response_assistant):

    delimiter = "####"

    allowed_values = {'low','medium','high'}

    prompt = f"""
    You are a senior evaluator who has an eye for detail.The input text will contain a user requirement captured through 6 keys.
    You are provided an input. You need to evaluate if the input text has the following keys:
    {{
    'GPU intensity': 'values',
    'Display quality':'values',
    'Portability':'values',
    'Multitasking':'values',
    'Processing speed':'values',
    'Budget':'number'
    }}
    The values for the keys should only be from the allowed values: {allowed_values}.
    The 'Budget' key can take only a numerical value.
    Next you need to evaluate if the keys have the the values filled correctly.
    Only output a one-word string in JSON format at the key 'result' - Yes/No.
    Thought 1 - Output a string 'Yes' if the values are correctly filled for all keys, otherwise output 'No'. Even if a single key is missing output 'No'.
    Thought 2 - If the answer is No, mention the reason in the key 'reason'.
    Thought 3 - Please enclose the JSON proprty names in double quotes.
    Thought 4 - Ensure that you are correctly validating that budget is a number.
    THought 4 - Think carefully before the answering.
    """

    messages=[{"role": "system", "content":prompt },
              {"role": "user", "content":f"""Here is the input: {response_assistant}""" }]

    response = openai.chat.completions.create(
                                    model=MODEL,
                                    messages = messages,
                                    seed = 1234
                                    # n = 5
                                    )

    print("\n\nin the intent confirmation \n\n")
    print(response)
    json_output = json.loads(response.choices[0].message.content)

    return json_output


# Function to compare laptops based on user input and recommend top 3
def compare_laptops_with_user(user_req_string):

    """
    Compares user requirements with laptops in the catalogue and returns the top 3 recommendations.

    Parameters:
    user_req_string (dict): A dictionary containing the user's laptop requirements.

    Returns:
    str: A JSON string containing the top 3 recommended laptops.
    """
 
    laptop_df = pd.read_csv(LAPTOP_DATA)

    budget = user_req_string.get('Budget', '0')
  
    # # Creating a copy of the DataFrame and filtering laptops based on the budget
    filtered_laptops = laptop_df.copy()
    filtered_laptops['Price'] = filtered_laptops['Price'].str.replace(',', '').astype(int)
    filtered_laptops = filtered_laptops[filtered_laptops['Price'] <= budget].copy()
    # filtered_laptops
    # # # Mapping string values 'low', 'medium', 'high' to numerical scores 0, 1, 2
    mappings = {'low': 0, 'medium': 1, 'high': 2}

    # # # Creating a new column 'Score' in the filtered DataFrame and initializing it to 0
    filtered_laptops['Score'] = 0


    # # # Iterating over each laptop in the filtered DataFrame to calculate scores based on user requirements
    for index, row in filtered_laptops.iterrows():
        user_product_match_str = row['laptop_feature']
        laptop_values = user_product_match_str
        user_product_match_str = user_product_match_str.replace("'", '"')
        laptop_values = json.loads(user_product_match_str)
        # print("laptop_values - 2")
        # print(laptop_values)
        score = 0

        ## Comparing user requirements with laptop features and updating scores
        for key, user_value in user_req_string.items():
            if key == 'Budget':
                continue  # Skipping budget comparison
            laptop_value = laptop_values.get(key, None)
            # print(key, laptop_value)
            laptop_mapping = mappings.get(laptop_value, -1)
            user_mapping = mappings.get(user_value, -1)
            # print(laptop_mapping,user_mapping)
            if laptop_mapping >= user_mapping:
                score += 1  # Incrementing score if laptop value meets or exceeds user value

        filtered_laptops.loc[index, 'Score'] = score  # Updating the 'Score' column in the DataFrame

    # Sorting laptops by score in descending order and selecting the top 3 products
    top_laptops = filtered_laptops.drop('laptop_feature', axis=1)
    top_laptops = top_laptops.sort_values('Score', ascending=False).head(3)
    top_laptops_json = top_laptops.to_json(orient='records')  # Converting the top laptops DataFrame to JSON format

    # top_laptops
    return top_laptops_json


# Validate if recommended laptops match user preferences
def recommendation_validation(laptop_recommendation):
    data = json.loads(laptop_recommendation)
    data1 = []
    for i in range(len(data)):
        # print(data[i])
        if data[i]['Score'] > 2:
            data1.append(data[i])

    return data1


# Initialize conversation for laptop recommendations
def initialize_conv_reco(products):
    system_message = f"""
    You are an intelligent laptop gadget expert and you are tasked with the objective to \
    solve the user queries about any product from the catalogue in the user message \
    You should keep the user profile in mind while answering the questions.\

    Start with a brief summary of each laptop in the following format, in decreasing order of price of laptops:
    1. <Laptop Name> : <Major specifications of the laptop>, <Price in Rs>
    2. <Laptop Name> : <Major specifications of the laptop>, <Price in Rs>

    """
    user_message = f""" These are the user's products: {products}"""
    conversation = [{"role": "system", "content": system_message },
                    {"role":"user","content":user_message}]
    # conversation_final = conversation[0]['content']
    return conversation


# Map given laptop descriptions to feature classification, and update the dataframe
def product_map_layer(laptop_description):
    delimiter = "#####"

    lap_spec = {
        "GPU intensity":"(Type of the Graphics Processor)",
        "Display quality":"(Display Type, Screen Resolution, Display Size)",
        "Portability":"(Laptop Weight)",
        "Multitasking":"(RAM Size)",
        "Processing speed":"(CPU Type, Core, Clock Speed)"
    }

    values = {'low','medium','high'}

    prompt=f"""
    You are a Laptop Specifications Classifier whose job is to extract the key features of laptops and classify them as per their requirements.
    To analyze each laptop, perform the following steps:
    Step 1: Extract the laptop's primary features from the description {laptop_description}
    Step 2: Store the extracted features in {lap_spec} \
    Step 3: Classify each of the items in {lap_spec} into {values} based on the following rules: \
    {delimiter}
    GPU Intensity:
    - low: <<< if GPU is entry-level such as an integrated graphics processor or entry-level dedicated graphics like Intel UHD >>> , \n
    - medium: <<< if mid-range dedicated graphics like M1, AMD Radeon, Intel Iris >>> , \n
    - high: <<< high-end dedicated graphics like Nvidia RTX >>> , \n

    Display Quality:
    - low: <<< if resolution is below Full HD (e.g., 1366x768). >>> , \n
    - medium: <<< if Full HD resolution (1920x1080) or higher. >>> , \n
    - high: <<< if High-resolution display (e.g., 4K, Retina) with excellent color accuracy and features like HDR support. >>> \n

    Portability:
    - high: <<< if laptop weight is less than 1.51 kg >>> , \n
    - medium: <<< if laptop weight is between 1.51 kg and 2.51 kg >>> , \n
    - low: <<< if laptop weight is greater than 2.51 kg >>> \n

    Multitasking:
    - low: <<< If RAM size is 8 GB, 12 GB >>> , \n
    - medium: <<< if RAM size is 16 GB >>> , \n
    - high: <<< if RAM size is 32 GB, 64 GB >>> \n

    Processing Speed:
    - low: <<< if entry-level processors like Intel Core i3, AMD Ryzen 3 >>> , \n
    - medium: <<< if Mid-range processors like Intel Core i5, AMD Ryzen 5 >>> , \n
    - high: <<< if High-performance processors like Intel Core i7, AMD Ryzen 7 or higher >>> \n
    {delimiter}

    {delimiter}
    Here is input output pair for few-shot learning:
    input 1: "The Dell Inspiron is a versatile laptop that combines powerful performance and affordability. It features an Intel Core i5 processor clocked at 2.4 GHz, ensuring smooth multitasking and efficient computing. With 8GB of RAM and an SSD, it offers quick data access and ample storage capacity. The laptop sports a vibrant 15.6" LCD display with a resolution of 1920x1080, delivering crisp visuals and immersive viewing experience. Weighing just 2.5 kg, it is highly portable, making it ideal for on-the-go usage. Additionally, it boasts an Intel UHD GPU for decent graphical performance and a backlit keyboard for enhanced typing convenience. With a one-year warranty and a battery life of up to 6 hours, the Dell Inspiron is a reliable companion for work or entertainment. All these features are packed at an affordable price of 35,000, making it an excellent choice for budget-conscious users."
    output 1: {{'GPU intensity': 'medium','Display quality':'medium','Portability':'medium','Multitasking':'high','Processing speed':'medium'}}

    {delimiter}
    ### Strictly don't keep any other text in the values of the JSON dictionary other than low or medium or high ###
    """
    input = f"""Follow the above instructions step-by-step and output the dictionary in JSON format {lap_spec} for the following laptop {laptop_description}."""

    messages=[{"role": "system", "content":prompt },{"role": "user","content":input}]

    response = get_chat_completions(messages)

    return response


# Function to generate an updated laptop CSV with extracted features
def gen_updated_latop_data():
    ##Run this code once to extract product info in the form of a dictionary
    laptop_df= pd.read_csv(LAPTOP_DATA_ORIGINAL)

    ## Create a new column "laptop_feature" that contains the dictionary of the product features
    laptop_df['laptop_feature'] = laptop_df['Description'].apply(lambda x: product_map_layer(x))

    laptop_df.to_csv(LAPTOP_DATA,index=False,header = True)
