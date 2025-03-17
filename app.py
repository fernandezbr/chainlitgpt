import time
import logging
import chainlit as cl
from loguru import logger
from utils.utils import append_message, init_settings, get_llm_details, get_llm_models
from utils.chats import chat_completion
from utils.foundry import chat_agent

# Disable verbose connection logs
logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)

@cl.set_chat_profiles
async def chat_profile():
    llm_models = get_llm_models()
    # get a list of model names from llm_models
    model_names = [f"{model["provider"]}--{model["model_name"]}--{model["description"]}" for model in llm_models]
    profiles = []

    for model in model_names:
        provider, model_name, description = model.split("--")

        # Create a profile for each model
        profiles.append(
            cl.ChatProfile(
                name=f"{provider}--{model_name}",
                markdown_description=description
            )
        )

    return profiles


@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Morning routine ideation",
            message="Can you help me create a personalized morning routine that would help increase my productivity throughout the day? Start by asking me about my current habits and what activities energize me in the morning.",
            icon="/public/bulb.webp",
            ),

        cl.Starter(
            label="Spot the errors",
            message="How can I avoid common mistakes when proofreading my work?",
            icon="/public/warning.webp",
            ),
        cl.Starter(
            label="Get more done",
            message="How can I improve my productivity during remote work?",
            icon="/public/rocket.png",
            ),
        cl.Starter(
            label="Boost your knowledge",
            message="Help me learn about [topic]",
            icon="/public/book.png",
            )
        ]


@cl.on_chat_start
async def start():
    """
    Initialize the chat session and send a welcome message.
    """
    try:
        cl.user_session.set("chat_settings", await init_settings())
    except Exception as e:
        await cl.Message(content=f"An error occurred: {str(e)}", author="Error").send()
        logger.error(f"Error: {str(e)}")


@cl.on_message
async def main(message: cl.Message):
    """
    Process incoming user messages and generate responses using Azure OpenAI.
    
    Args:
        message: The message object from Chainlit containing user's input
    """
    try:
        cl.user_session.set("start_time", time.time())
        user_input = message.content
        get_llm_details()

        # Get messages from session
        messages = append_message("user", user_input, message.elements)

        if cl.user_session.get("chat_settings").get("model_provider") == "foundry":
            full_response = await chat_agent(user_input)
        else:
            full_response = await chat_completion(messages)

        # Save the complete message to session
        append_message("assistant", full_response)

    except Exception as e:
        await cl.Message(content=f"An error occurred: {str(e)}", author="Error").send()
        logger.error(f"Error: {str(e)}")
