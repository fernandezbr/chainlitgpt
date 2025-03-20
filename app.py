import time
import logging
import chainlit as cl
from loguru import logger
from typing import Dict, Optional
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from utils.utils import append_message, init_settings, get_llm_details, get_llm_models
from utils.chats import chat_completion
from utils.foundry import chat_agent

# Disable verbose connection logs
logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)

@cl.oauth_callback
def oauth_callback(
  provider_id: str,
  token: str,
  raw_user_data: Dict[str, str],
  default_user: cl.User,
) -> Optional[cl.User]:
  print(f">>>>> OAuth callback for provider {provider_id} with token {token}")
  print(f">>>>> Raw user data: {raw_user_data}")
  return default_user


@cl.set_chat_profiles
async def chat_profile():
    llm_models = get_llm_models()
    # get a list of model names from llm_models
    model_list = [f"{model["model_deployment"]}--{model["description"]}" for model in llm_models]
    profiles = []

    for item in model_list:
        model_deployment, description = item.split("--")

        # Create a profile for each model
        profiles.append(
            cl.ChatProfile(
                name=model_deployment,
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


@cl.on_chat_resume
async def on_chat_resume(thread):
    pass


@cl.on_chat_start
async def start():
    """
    Initialize the chat session and send a welcome message.
    """
    try:
        cl.user_session.set("chat_settings", await init_settings())
        llm_details = get_llm_details()
        # app_user = cl.user_session.get("user")
        # print(f">>>>> User: {app_user}")

        # Create an instance of the AIProjectClient using DefaultAzureCredential
        if cl.user_session.get("chat_settings").get("model_provider") == "foundry" and not cl.user_session.get("thread_id"):
            project_client = AIProjectClient.from_connection_string(
                conn_str=llm_details["api_key"], credential=DefaultAzureCredential()
            )

            # Create a thread for the agent
            thread = project_client.agents.create_thread()
            cl.user_session.set("thread_id", thread.id)
            logger.warning(f"New thread created, thread ID: {thread.id}")

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
