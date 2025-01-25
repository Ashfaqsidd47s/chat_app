import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from .models import Conversation
from .utils import save_message_to_db


connected_users = set()

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        # Get room name from URL
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"
        self.user_id = self.scope['session'].get('user_id')
        self.user_name = self.scope['session'].get("user_name")



        if not self.user_id:
            self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'unauthenticated'
            }))
            return

        connected_users.add(self.user_id)

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        

        # Broadcast a "user joined" message to the root group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'type': 'online', 
                    'message': 'User joined',
                    "user_id": self.user_id
                }
            }
        )

        # Accept the WebSocket connection
        self.accept()
        self.send(text_data=json.dumps({
                'type': 'list',
                'users': list(connected_users)
            }))

    def disconnect(self, close_code):
        # Broadcast a "user disconnected" message to the root group
        connected_users.discard(self.user_id)

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'type': 'offline',
                    'user_id': self.user_id
                }
            }
        )

        # Leave the root group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        # Receive message from WebSocket
        text_data_json = None
        try:
            text_data_json = json.loads(text_data)
        except json.JSONDecodeError:
            self.send(text_data=json.dumps({
            'type': 'error',
            'message': 'Invalid JSON format'
            }))
            return
        
        print("Messge recieved", text_data_json)
        
        message_type = text_data_json.get('type')
        payload = text_data_json.get('payload')
        user_id = self.user_id
        user_name = self.user_name

        if not payload or not user_id or not payload.get('conversation_id'):
            self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'un authorized'
            }))
            return
        
        conversation_id = payload.get('conversation_id')
        sender_id = payload.get("user_id")
        sender_name = payload.get("user_name")

        if message_type == 'join_conversation':
            # Check if the room exists
            conversation_group_name = f"conversation_{conversation_id}"
            # Check if the conversation exists in the database
            if not Conversation.objects.filter(id=conversation_id).exists():
                self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Conversation not found'
                }))
                return

            # If conversation exists, create the room
            async_to_sync(self.channel_layer.group_add)(
                conversation_group_name,
                self.channel_name
            )

            # Broadcast a "member joined" message
            async_to_sync(self.channel_layer.group_send)(
                conversation_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'type': 'member_joined',
                        'content': 'Member joined',
                        'user_id': sender_id,
                        'user_name': sender_name,
                    }
                }
            )

        elif message_type == 'send_message':
            message_content = payload.get('message_content')
            sender_id = payload.get("user_id")

            # Broadcast the message to the specific conversation group
            conversation_group_name = f"conversation_{conversation_id}"
            async_to_sync(self.channel_layer.group_send)(
                conversation_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'type': 'normal',
                        'content': message_content,
                        'user_id': sender_id,
                        'user_name': sender_name,
                    }
                }
            )

            #save message to the database 
            save_message_to_db(conversation_id=conversation_id, sender_id=user_id, data=message_content)

        elif message_type == 'typing':
            # Broadcast the message to the specific conversation group
            sender_id = payload.get("user_id")
            conversation_group_name = f"conversation_{conversation_id}"
            async_to_sync(self.channel_layer.group_send)(
                conversation_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'type': 'typing',
                        'content': "user typing",
                        'user_id': sender_id,
                        'user_name': sender_name,
                    }
                }
            )
            
        elif message_type == 'not_typing':
            # Broadcast the message to the specific conversation group
            conversation_group_name = f"conversation_{conversation_id}"
            async_to_sync(self.channel_layer.group_send)(
                conversation_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'type': 'not_typing',
                        'content': "user typing",
                        'user_id': sender_id,
                        'user_name': sender_name,
                    }
                }
            )
            
    
        else:
            self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': "invalid message type"
                }))
            

            
    def chat_message(self, event):
        # Send message to WebSocket
        self.send(text_data=json.dumps(event['message']))