import time
import chainlit as cl
from pathlib import Path
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from utils.utils import get_llm_models
from azure.ai.projects.models import (
    CodeInterpreterTool,
    MessageAttachment,
    FilePurpose,
    MessageRole,
    AgentStreamEvent,
    MessageDeltaChunk,
    ThreadRun,
)


# Chat with Azure AI Agents
async def chat_agent(user_input: str) -> str:
    """
    Generate a response from the Azure AI Agent based on the provided user input.
    """
    try:
        # Get chat settings
        chat_settings = cl.user_session.get("chat_settings")
        model_name = chat_settings.get("model_name")

        # Get the model details from the selected model
        llm_details = next((item for item in get_llm_models() if item["model_name"] == model_name), {})

        # Show thinking message to user
        msg = await cl.Message(f"[{model_name}] thinking...", author="agent").send()

        # Create an instance of the AIProjectClient using DefaultAzureCredential
        project_client = AIProjectClient.from_connection_string(
            conn_str=llm_details["api_key"], credential=DefaultAzureCredential()
        )

        # create thread for the agent
        if not cl.user_session.get("thread_id"):
            thread = project_client.agents.create_thread()
            cl.user_session.set("thread_id", thread.id)

        thread_id = cl.user_session.get("thread_id")
        uploaded_files = cl.user_session.get("uploaded_files") or []
        attachments = []

        if len(uploaded_files) > 0:
            for file in uploaded_files:
                # Upload a file and wait for it to be processed
                file = project_client.agents.upload_file_and_poll(
                    file_path=file, purpose=FilePurpose.AGENTS
                )
                print(f"Uploaded file, file ID: {file.id}")

                # Create a message with the attachment
                attachment = MessageAttachment(file_id=file.id, tools=CodeInterpreterTool().definitions)
                attachments.append(attachment)

        # Create a message, with the prompt being the message content that is sent to the model
        project_client.agents.create_message(
            thread_id=thread_id,
            role="user",
            content=user_input,
            attachments=attachments
        )

        # Run the agent to process tne message in the thread
        with project_client.agents.create_stream(thread_id=thread_id, agent_id=llm_details["model_id"]) as stream:
            msg.content = ""
            for event_type, event_data, _ in stream:
                if isinstance(event_data, MessageDeltaChunk):
                    msg.content += event_data.text
                    await msg.update()

                    elapsed_time = time.time() - cl.user_session.get("start_time")
                    print(f"Elapsed time: {elapsed_time:.2f} seconds")

                elif isinstance(event_data, ThreadRun):
                    if event_data.status == "failed":
                        print(f"Run failed. Error: {event_data.last_error}")
                        raise Exception(event_data.last_error)

                elif event_type == AgentStreamEvent.ERROR:
                    print(f"An error occurred. Data: {event_data}")
                    raise Exception(event_data)

        # Get all messages from the thread
        messages = project_client.agents.list_messages(thread_id)
        images = []

        for image_content in messages.image_contents:
            file_id = image_content.image_file.file_id
            file_name = f"{file_id}_image_file.png"

            # Save the image file to the current working directory
            project_client.agents.save_file(file_id=file_id, file_name=file_name)
            image = cl.Image(path=f"{Path.cwd() / file_name}", name=file_name, display="inline")
            images.append(image)

        # Append the images to the message
        if len(images) > 0:
            msg.elements = images

        last_msg = messages.get_last_text_message_by_role(MessageRole.AGENT)
        if not last_msg:
            raise Exception("No response from the model.")

        msg.content = last_msg.text.value
        await msg.update()
        return msg.content

    except Exception as e:
        raise RuntimeError(f"Error generating response in chat_agent: {str(e)}")
