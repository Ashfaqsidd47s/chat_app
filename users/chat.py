import json
from channels.generic.websocket import WebsocketConsumer
from django.db import connection
from .models import Conversation, Message

class ChatManager:
    instance = None
    conversations = {}

    def __new__(cls):
        if not cls.instance:
            cls.instance = super().__new__(cls)
            cls.conversations = {}
        return cls.instance

    def add_user(self, user):
        if not user.id or not user.conversation_id:
            return
        if user.conversation_id not in self.conversations:
            try:
                conversation_exists = self.check_conversation_exists(user.conversation_id)
                if not conversation_exists:
                    user.send_json({
                        'type': 'error',
                        'text': 'invalid conversation id'
                    })
                    return
            except Exception:
                user.send_json({
                    'type': 'error',
                    'text': 'invalid conversation id'
                })
                return
            self.conversations[user.conversation_id] = [user]
            return

        self.conversations[user.conversation_id].append(user)

    def remove_user(self, user, conversation_id):
        users = self.conversations.get(conversation_id)
        if users:
            new_users = [u for u in users if u != user]
            if not new_users:
                del self.conversations[conversation_id]
            else:
                self.conversations[conversation_id] = new_users

    def broadcast(self, message, user_id, conversation_id):
        users = self.conversations.get(conversation_id)
        if users:
            for user in users:
                if user.id != user_id:
                    user.send_json(message)

    def get_active_users(self, user):
        users = self.conversations.get(user.conversation_id)
        if users:
            alive_users = [{'id': u.id} for u in users if u != user]
            user.send_json({
                'type': 'list',
                'users': alive_users
            })
        else:
            user.send_json({
                'type': 'error',
                'text': 'user not found'
            })

    def check_conversation_exists(self, conversation_id):
        with connection.cursor() as cursor:
            query = "SELECT id FROM Conversation WHERE id = %s"
            cursor.execute(query, [conversation_id])
            result = cursor.fetchone()
            return result is not None



JOIN = "JOIN"
SEND_MESSAGE = "SEND_MESSAGE"
TYPING = "TYPING"
NOT_TYPING = "NOT_TYPING"
OFFER = "OFFER"
CANCEL_OFFER = "CANCEL_OFFER"
ANSWER = "ANSWER"

class ChatUser(WebsocketConsumer):
    def __init__(self, ws, user_id='', conversation_id=''):
        self.id = user_id
        self.conversation_id = conversation_id
        self.ws = ws
        self.chat_manager = ChatManager()
        print("inside the user ", ws)
        self.initial_handler()

    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        self.chat_manager.remove_user(self, self.conversation_id)
        self.chat_manager.broadcast({
            'type': 'offline',
            'payload': {'userId': self.id, 'text': 'user is offline'}
        }, self.id, self.conversation_id)

    def receive(self, text_data):
        message = json.loads(text_data)
        print("message recieved inside as well")
        if not message.get('type') or not message.get('payload') or not message['payload'].get('conversationId') or not message['payload'].get('userId'):
            self.send_json({
                'type': 'error',
                'text': 'invalid format'
            })
            return

        message_type = message['type']
        payload = message['payload']
        conversation_id = payload.get('conversationId')
        user_id = payload.get('userId')

        if conversation_id not in self.chat_manager.conversations:
            self.send_json({
                'type': 'error',
                'text': 'conversation not found'
            })
            return

        if message_type == 'JOIN':
            self.id = user_id
            self.conversation_id = conversation_id
            self.chat_manager.add_user(self)
            self.chat_manager.broadcast({
                'type': 'online',
                'payload': {'userId': user_id, 'text': 'user joined'}
            }, user_id, conversation_id)
            self.chat_manager.get_active_users(self)

        elif message_type == 'SEND_MESSAGE':
            self.chat_manager.broadcast({
                'type': 'normal',
                'payload': {'userId': user_id, 'text': payload.get('text')}
            }, user_id, conversation_id)
            # Save message to DB
            # save_message_to_db(conversation_id, payload.get('text'), user_id)

        elif message_type == 'TYPING':
            self.chat_manager.broadcast({
                'type': 'typing',
                'payload': {'userId': user_id, 'text': 'user is typing'}
            }, user_id, conversation_id)

        elif message_type == 'NOT_TYPING':
            self.chat_manager.broadcast({
                'type': 'not_typing',
                'payload': {'userId': user_id, 'text': 'user is not typing'}
            }, user_id, conversation_id)

        elif message_type == 'OFFER':
            self.chat_manager.broadcast({
                'type': 'offer',
                'payload': {'userId': user_id, 'text': payload.get('text')}
            }, user_id, conversation_id)

        elif message_type == 'CANCEL_OFFER':
            self.chat_manager.broadcast({
                'type': 'cancel_offer',
                'payload': {'userId': user_id, 'text': 'offer canceled'}
            }, user_id, conversation_id)

        elif message_type == 'ANSWER':
            self.chat_manager.broadcast({
                'type': 'answer',
                'payload': {'userId': user_id, 'text': payload.get('text')}
            }, user_id, conversation_id)

        else:
            self.send_json({'message': 'invalid type'})

    def send_json(self, data):
        # Assuming send_json is a method that sends the message back to the WebSocket client
        self.ws.send(text_data=json.dumps(data))

    def initial_handler(self):
        # Handle incoming messages from the WebSocket
        def on_message(data):
            print("its working")
            try:
                message = json.loads(data)
                
                if not message.get('type') or not message.get('payload') or not message['payload'].get('conversationId') or not message['payload'].get('userId'):
                    self.send_error("invalid format")
                    return

                message_type = message['type']
                payload = message['payload']
                conversation_id = payload.get('conversationId')
                user_id = payload.get('userId')

                if message_type == JOIN:
                    self.set_id(user_id)
                    self.set_conversation_id(conversation_id)
                    ChatManager.get_instance().add_user(self)
                    ChatManager.get_instance().broadcast({
                        "type": "online",
                        "payload": {
                            "userId": user_id,
                            "text": "user joined"
                        }
                    }, user_id, conversation_id)
                    ChatManager.get_instance().get_active_users(self)

                elif message_type == SEND_MESSAGE:
                    if ChatManager.get_instance().conversations.get(conversation_id):
                        ChatManager.get_instance().broadcast({
                            "type": "normal",
                            "payload": {
                                "userId": user_id,
                                "text": payload['text']
                            }
                        }, user_id, conversation_id)
                    else:
                        self.send_error("conversation not found")

                elif message_type == TYPING:
                    if ChatManager.get_instance().conversations.get(conversation_id):
                        ChatManager.get_instance().broadcast({
                            "type": "typing",
                            "payload": {
                                "userId": user_id,
                                "text": "user is typing"
                            }
                        }, user_id, conversation_id)
                    else:
                        self.send_error("conversation not found")

                elif message_type == NOT_TYPING:
                    if ChatManager.get_instance().conversations.get(conversation_id):
                        ChatManager.get_instance().broadcast({
                            "type": "not_typing",
                            "payload": {
                                "userId": user_id,
                                "text": "user is not typing"
                            }
                        }, user_id, conversation_id)
                    else:
                        self.send_error("conversation not found")

                elif message_type == OFFER:
                    if ChatManager.get_instance().conversations.get(conversation_id):
                        ChatManager.get_instance().broadcast({
                            "type": "offer",
                            "payload": {
                                "userId": user_id,
                                "text": payload['text']
                            }
                        }, user_id, conversation_id)
                    else:
                        self.send_error("conversation not found")

                elif message_type == CANCEL_OFFER:
                    if ChatManager.get_instance().conversations.get(conversation_id):
                        ChatManager.get_instance().broadcast({
                            "type": "cancel_offer",
                            "payload": {
                                "userId": user_id,
                                "text": "offer canceled"
                            }
                        }, user_id, conversation_id)
                    else:
                        self.send_error("conversation not found")

                elif message_type == ANSWER:
                    if ChatManager.get_instance().conversations.get(conversation_id):
                        ChatManager.get_instance().broadcast({
                            "type": "answer",
                            "payload": {
                                "userId": user_id,
                                "text": payload['text']
                            }
                        }, user_id, conversation_id)
                    else:
                        self.send_error("conversation not found")

                else:
                    self.send_error("invalid type")

            except json.JSONDecodeError:
                self.send_error("error parsing message")

        self.ws = on_message  # Attach handler to WebSocket instance (assuming self.ws is the WebSocket)

# JWT Check (commented out for now, for security check)
# def verify_user(token: str) -> bool:
#     try:
#         JWT_SECRET = process.env.JWT_SECRET
#         decoded = jwt_decode(token, JWT_SECRET)
#         return True
#     except Exception:
#         return False
