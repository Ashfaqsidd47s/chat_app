import uuid
from django.db import models
from django.core.validators import MinLengthValidator

# Create your models here.
class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, validators=[MinLengthValidator(3)])
    email = models.EmailField(max_length=150, unique=True, validators=[MinLengthValidator(3)])
    password = models.CharField(max_length=128, validators=[MinLengthValidator(6)]) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
# Conversation model
class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user1 = models.ForeignKey(User, related_name="conversations_as_user1", on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name="conversations_as_user2", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation between {self.user1.name} and {self.user2.name}"


# Message model
class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = models.TextField(max_length=1000, validators=[MinLengthValidator(1)])
    sender = models.ForeignKey(User, related_name="messages", on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, related_name="messages", on_delete=models.CASCADE)  # Link to Conversation
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.name}: {self.data[:30]}..."