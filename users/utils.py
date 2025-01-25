from django.shortcuts import get_object_or_404
from .models import Message, User, Conversation

def save_message_to_db(conversation_id, sender_id, data):
    sender = get_object_or_404(User, id=sender_id)
    conversation = get_object_or_404(Conversation, id=conversation_id)

    # Create the message
    message = Message.objects.create(data=data, sender=sender, conversation=conversation)
