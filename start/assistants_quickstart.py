from openai import OpenAI
import shelve
from dotenv import load_dotenv
import os
import time
from pathlib import Path
from typing import List

load_dotenv()
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
client = OpenAI(api_key=OPEN_AI_API_KEY)



def create_assistant():
    client = OpenAI()
    assistant = client.beta.assistants.create(
    name="Restaurant expert",
    instructions="You're a helpful WhatsApp assistant that can assist guests that are looking for a place to eat in their neighborhood, you are supposed to give recommendations based in the reviews, rating, an total user reviews. Be friendly and funny",
    model="gpt-3.5-turbo",
    tools=[{"type": "file_search"}])
    
    return assistant

assistant = create_assistant()

file_paths = ["../data/todos_restaurantes.csv"]

def vectorize_data(file_paths:List[Path]):

    vector_store = client.beta.vector_stores.create(name="Knowledge_base")
    file_streams = [open(path, "rb") for path in file_paths]
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(vector_store_id=vector_store.id, files=file_streams)
    return vector_store,file_batch

vector_store,file_batch=vectorize_data(file_paths)

 
def update_assistant(assistant):

    assistant = client.beta.assistants.update(assistant_id=assistant.id,tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}})
    
    return assistant

assistant=update_assistant(assistant)


# --------------------------------------------------------------
# Thread management
# --------------------------------------------------------------

def check_if_thread_exists(wa_id):
    with shelve.open("threads_db.db") as threads_shelf:
        return threads_shelf.get(wa_id, None)


def store_thread(wa_id, thread_id):
    with shelve.open("threads_db.db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = thread_id


# --------------------------------------------------------------
# Generate response
# --------------------------------------------------------------
def generate_response(message_body, wa_id, name):
    # Check if there is already a thread_id for the wa_id
    thread_id = check_if_thread_exists(wa_id)

    # If a thread doesn't exist, create one and store it
    if thread_id is None:
        print(f"Creating new thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.create()
        store_thread(wa_id, thread.id)
        thread_id = thread.id

    # Otherwise, retrieve the existing thread
    else:
        print(f"Retrieving existing thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.retrieve(thread_id)

    # Add message to thread
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_body,
    )

    # Run the assistant and get the new message
    new_message = run_assistant(thread)
    print(f"To {name}:", new_message)
    return new_message


# --------------------------------------------------------------
# Run assistant
# --------------------------------------------------------------
def run_assistant(thread):
    # Retrieve the Assistant
    assistant = client.beta.assistants.retrieve(assistant.id)

    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )

    # Wait for completion
    while run.status != "completed":
        # Be nice to the API
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    # Retrieve the Messages
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    new_message = messages.data[0].content[0].text.value
    print(f"Generated message: {new_message}")
    return new_message


# --------------------------------------------------------------
# Test assistant
# --------------------------------------------------------------

new_message = generate_response("What's the check in time?", "123", "John")

new_message = generate_response("What's the pin for the lockbox?", "456", "Sarah")

new_message = generate_response("What was my previous question?", "123", "John")

new_message = generate_response("What was my previous question?", "456", "Sarah")
