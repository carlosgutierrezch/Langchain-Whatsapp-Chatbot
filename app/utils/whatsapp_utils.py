import logging
from flask import current_app, jsonify
import json
import requests
import re
from typing import Dict, Union, Any
from app.services.openai_service import generate_response
def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")

def format_restaurant_message(response_data: Dict[str, Any]) -> str:
    """Format the restaurant data into a WhatsApp-friendly message"""
    message_parts = []
    
    # Add the main answer
    if response_data.get('answer'):
        message_parts.append(response_data['answer'])
    
    # Add recommendation if present and valid
    if response_data.get('recommendation') and response_data['recommendation'] != "No recommendation":
        message_parts.append(f"\nRecommendation: {response_data['recommendation']}")
        
        # Add formatted restaurant data if available
        if response_data.get('formatted_data_for_recommendation'):
            restaurants = response_data['formatted_data_for_recommendation'].get('Top 5 Restaurants', [])
            if restaurants:
                message_parts.append("\nTop 5 Restaurants:")
                for i, restaurant in enumerate(restaurants, 1):
                    restaurant_details = [
                        f"{i}. {restaurant['Restaurant name']}",
                        f"URL: {restaurant['URL']}",
                        f"Description: {restaurant['Description']}"
                    ]
                    message_parts.append("\n".join(restaurant_details))
    
    return "\n\n".join(message_parts)

def get_text_message_input(recipient: str, response_data: Union[str, Dict[str, Any]]) -> str:
    """
    Create the message input for WhatsApp API
    Now handles both string responses and structured response dictionaries
    """
    if isinstance(response_data, dict):
        message_text = format_restaurant_message(response_data)
    else:
        message_text = str(response_data)

    message_text = process_text_for_whatsapp(message_text)
    
    return json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message_text
        }
    })

def send_message(data: str) -> Union[requests.Response, tuple]:
    """Send message to WhatsApp API with proper error handling"""
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        log_http_response(response)
        return response
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except requests.RequestException as e:
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500

def process_text_for_whatsapp(text: str) -> str:
    """Process text to be WhatsApp-friendly"""
    # Remove brackets
    text = re.sub(r"\【.*?\】", "", text).strip()
    
    # Convert markdown-style bold to WhatsApp-style bold
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)
    
    # Ensure URLs are on their own line
    text = re.sub(r"([^\n])(https?://\S+)", r"\1\n\2", text)
    
    return text

def process_whatsapp_message(body: Dict[str, Any]) -> None:
    """Process incoming WhatsApp message and send response"""
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]

    # Generate response using your existing service
    response = generate_response(message_body, wa_id, name)
    
    # Format and send the message
    data = get_text_message_input(wa_id, response)
    send_message(data)

def is_valid_whatsapp_message(body: Dict[str, Any]) -> bool:
    """Validate incoming WhatsApp message structure"""
    try:
        return (
            body.get("object")
            and body.get("entry")
            and body["entry"][0].get("changes")
            and body["entry"][0]["changes"][0].get("value")
            and body["entry"][0]["changes"][0]["value"].get("messages")
            and body["entry"][0]["changes"][0]["value"]["messages"][0]
        )
    except (KeyError, IndexError):
        return False