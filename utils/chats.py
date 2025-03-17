import chainlit as cl
from loguru import logger
from litellm import completion
from utils.utils import get_llm_models


# Get Azure OpenAI parameters
def get_azure_params(model_name: str, messages: list, temperature: float) -> dict:
    # Get the model details from the selected model
    llm_model = next((item for item in get_llm_models() if item["model_name"] == model_name), {})

    chat_parameters = {
        "model": "azure/gpt-4o",
        "messages": messages,
        "stream": True,
        "api_version": llm_model["api_version"],
        "api_base": llm_model["api_endpoint"],
        "api_key": llm_model["api_key"],
    }

    if model_name not in ["o3-mini"]:
        chat_parameters["temperature"] = temperature

    return chat_parameters


# Chat completion function
async def chat_completion(messages: list) -> str:
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
        temperature = chat_settings.get("temperature")
        model_name = chat_settings.get("model_name")

        # Show thinking message to user
        msg = await cl.Message(f"[{model_name}] thinking...", author="agent").send()

        chat_parameters = get_azure_params(model_name, messages, float(temperature))

        # Create chat completion
        # logger.debug(f"Chat parameters: {chat_parameters}")
        response = completion(**chat_parameters)

        full_response = ""
        is_thinking = True

        for chunk in response:
            # Check if the message is still thinking
            if is_thinking:
                msg.content = ""
                is_thinking = False

            if chunk.choices and chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_response += content_chunk
                await msg.stream_token(content_chunk)
        
        await msg.update()
        return full_response

    except Exception as e:
        raise RuntimeError(f"Error generating response in chat_completion: {str(e)}")
