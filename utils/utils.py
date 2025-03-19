import os
import json
import base64
import chainlit as cl
from loguru import logger
from dotenv import load_dotenv
from markitdown import MarkItDown
from chainlit.input_widget import Slider, TextInput

# Load environment variables
load_dotenv()
md = MarkItDown()

# Get llm models from llm_config.json
def get_llm_models() -> list:
    """
    Retrieve the list of available LLM models from the configuration file.
    
    Returns:
        A list of LLM model names
    """
    parse_env = False

    if parse_env:
        return json.loads(os.getenv("LLM_CONFIG"))
    else:
        with open("llm_config.json", "r") as file:
            llm_config = json.load(file)

            # Copy this to the env file
            # print(json.dumps(llm_config).replace(" ", ""))
            return llm_config


# Append openai chat completion message
def append_message(role: str, content: str, elements: list = []) -> list:
    instructions = cl.user_session.get("chat_settings").get("instructions")

    # Create system message with instructions
    system_prompt = [{
        "role": "system",
        "content": [{"type": "text", "text": instructions}]
    }]

    chat_history = cl.user_session.get("chat_history") or []
    contents = [{"type": "text", "text": content}]
    uploaded_files = []
    file_contents = []

    # Check if the role is assistant and add the images to the message
    if role == "user":
        for element in elements:
            logger.debug(f"Uploaded file: {element}")
            is_foundry = cl.user_session.get("chat_settings").get("model_provider") == "foundry"

            # All file types are uploaded to the foundry
            if is_foundry:
                uploaded_files.append(element.path)

            # check if the element is an image
            if element.mime.startswith("image/"):
                encoded_image = base64.b64encode(open(element.path, 'rb').read()).decode('ascii')
                contents.append({"type": "image_url", "image_url": { "url": f"data:{element.mime};base64,{encoded_image}"}})

            # Convert the file to markdown format
            elif not is_foundry:
                md_result = md.convert(element.path)
                file_contents.append(f"<file_name:{element.name}>{md_result.text_content}</file_name:{element.name}>")

    cl.user_session.set("uploaded_files", uploaded_files)

    # Check if there are any uploaded files and add them to the message
    if len(file_contents) > 0:
        contents.append({"type": "text", "text": "\n\n".join(file_contents)})

    logger.debug(f"Contents: {contents}")
    # Add message to history
    chat_history.append({
        "role": role,
        "content": contents
    })

    # Prune chat history to keep only the 10 most recent messages
    if role == "assistant" and len(chat_history) > 10:
        chat_history = chat_history[-10:]

    # Update chat history in session
    cl.user_session.set("chat_history", chat_history)
    
    # Return combined messages (system message + chat history)
    return system_prompt + chat_history


# Initialize chat settings
async def init_settings() -> None:
    instructions = """
You are BSP AI Assistant, an advanced conversational AI model designed to assist internal employees of Bangko Sentral ng Pilipinas (BSP).
Your primary role is to provide accurate, timely, and relevant information, support productivity tasks, and enhance the overall efficiency of BSP operations.

### Personality Traits
- Professional: Maintain a formal and respectful tone, reflecting the standards of BSP.
- Knowledgeable: Provide accurate and up-to-date information on BSP policies, procedures, and financial regulations.
- Supportive: Offer assistance and solutions to employees' queries and tasks, promoting a collaborative work environment.
- Efficient: Deliver concise and clear responses to ensure quick and effective communication.

### Capabilities
- Information Retrieval: Access and provide information on BSP policies, procedures, financial regulations, and internal guidelines.
- Task Assistance: Help with scheduling, document management, and other productivity-related tasks.
- Problem Solving: Offer solutions to common issues faced by employees, including technical support and procedural clarifications.
- Learning and Adaptation: Continuously learn from interactions to improve responses and adapt to the evolving needs of BSP employees.

### Safety Guidelines
- Confidentiality: Ensure the privacy and security of sensitive information. Do not share confidential data outside the scope of internal BSP operations.
- Accuracy: Provide correct and verified information. If unsure, indicate the need for further verification or direct the employee to the appropriate department.
- Compliance: Adhere to BSP's internal policies and regulations. Avoid sharing information that conflicts with BSP's standards or legal requirements.
- Transparency: Inform employees if a request exceeds your capabilities or does not align with safety guidelines. Maintain a respectful and professional demeanor.

### Interaction Style
- Formal and Respectful: Use language that reflects the professional environment of BSP.
- Concise and Clear: Ensure responses are straightforward and easy to understand.
- Helpful and Supportive: Aim to assist employees in resolving their queries and completing tasks efficiently.
"""
    settings = await cl.ChatSettings(
        [
            Slider(
                id="temperature",
                label="Temperature",
                initial=0.7,
                min=0,
                max=2,
                step=0.1,
            ),
            TextInput(
                id="instructions",
                label="Instructions",
                initial=instructions
            ),
        ]
    ).send()

    return settings


# Get llm details from the selected model
def get_llm_details() -> dict:
    """
    Retrieve the details of the selected LLM model.
    """
    chat_settings = cl.user_session.get("chat_settings")
    provider, model_name = cl.user_session.get("chat_profile").split("/")

    # Set the model name and provider in the session
    chat_settings["model_name"] = model_name
    chat_settings["model_provider"] = provider
    cl.user_session.set("chat_settings", chat_settings)

    llm_details = next((item for item in get_llm_models() if item["model_deployment"].endswith(f"/{model_name}")), {})
    return llm_details
