import time
import chainlit as cl
from loguru import logger
from litellm import completion
from utils.utils import get_llm_models


# Get LLM parameters
def get_llm_params(messages: list, use_tools = False) -> dict:
    # Get chat settings
    chat_settings = cl.user_session.get("chat_settings")
    chat_profile = cl.user_session.get("chat_profile")
    temperature = chat_settings.get("temperature")
    provider = chat_settings.get("model_provider")
    model_name = chat_settings.get("model_name")

    # Get the model details from the selected model
    llm_details = next((item for item in get_llm_models() if item["model_deployment"] == chat_profile), {})
    logger.debug(f"messages: {messages}")

    chat_parameters = {
        "model": chat_profile,
        "messages": messages,
        "stream": True,
        "api_key": llm_details["api_key"],
    }

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the web using SERP API",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"}
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    if provider == "azure":
        if llm_details["api_version"]:
            chat_parameters["api_version"] = llm_details["api_version"]

        if llm_details["api_endpoint"]:
            chat_parameters["api_base"] = llm_details["api_endpoint"]

        # Models that accept temperature
        if model_name not in ["o3-mini"]:
            chat_parameters["temperature"] = temperature
    else:
        chat_parameters["temperature"] = float(temperature)

    # Append search_web tool
    if use_tools:
        chat_parameters["tools"] = tools

    return chat_parameters


# Chat completion function
async def chat_completion(messages: list, use_tools = False) -> str:
    """
    Generate a response from the Azure OpenAI model based on the provided messages.
    
    Args:
        messages: List of messages to send to the model
    
    Returns:
        The generated response from the model
    """
    try:
        # Get chat settings
        chat_settings = cl.user_session.get("chat_settings")
        model_name = chat_settings.get("model_name")

        # Show thinking message to user
        msg = await cl.Message(f"[{model_name}] thinking...", author="agent").send()
        chat_parameters = get_llm_params(messages)
        logger.debug(f"Chat parameters: {chat_parameters}")

        # Create chat completion
        response = completion(**chat_parameters)
        is_thinking = True
        last_chunk = None

        for chunk in response:
            # Check if the message is still thinking
            if is_thinking:
                msg.content = ""
                is_thinking = False
                logger.debug(f"Elapsed time: {(time.time() - cl.user_session.get("start_time")):.2f} seconds")

            if chunk.choices and chunk.choices[0].delta.content:
                # await msg.stream_token(chunk.choices[0].delta.content)
                msg.content += chunk.choices[0].delta.content
                await msg.update()
                logger.debug(f"Chunk content: {chunk.choices[0].delta.content}")

            if "citations" in chunk:
                last_chunk = chunk

        if "citations" in last_chunk:
            msg.content += f"\n\n**Sources:**"

            # Loop through citations and append them to the response
            for citation in last_chunk.citations:
                msg.content += f"\n[{citation}]({citation})"

        logger.debug(f"Last Chunk: {last_chunk}")

        # Remove the thinking message by splitting the content
        if msg and msg.content.startswith(f"<think>"):
            msg.content = msg.content.split(f"</think>")[-1].strip()

        await msg.update()
        return msg.content

    except Exception as e:
        logger.error(f"Error in chat_completion: {str(e)}")
        raise RuntimeError(f"Error generating response in chat_completion: {str(e)}")
