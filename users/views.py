from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import check_password, make_password
from django.contrib import messages
from .models import User, Conversation, Message
from django.contrib.sessions.backends.db import SessionStore
from django.http import JsonResponse



# Register View
def register(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        messages.get_messages(request).used = True
        # Validate input
        if len(name) < 3:
            messages.get_messages(request).used = True
            messages.error(request, "Name must be at least 3 characters long.")
            return redirect('register')

        if len(email) < 3:
            messages.get_messages(request).used = True
            messages.error(request, "Email must be at least 3 characters long.")
            return redirect('register')

        if len(password) < 6:
            messages.get_messages(request).used = True
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect('register')

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.get_messages(request).used = True
            messages.error(request, "Email already exists.")
            return redirect('register')

        # Save the user
        User.objects.create(
            name=name,
            email=email,
            password=make_password(password),
        )
        messages.get_messages(request).used = True
        return redirect('login')

    return render(request, 'register.html')


# Login View
def login(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Clear all previous messages
        messages.get_messages(request).used = True
        
        try:
            user = User.objects.get(email=email)
            if check_password(password, user.password):
                # Create session
                request.session['user_id'] = str(user.id)
                request.session['user_name'] = user.name
                messages.get_messages(request).used = True
                return redirect('home')
            else:
                messages.get_messages(request).used = True
                messages.error(request, "Invalid email or password.")
                return redirect('login')
        except User.DoesNotExist:
            messages.get_messages(request).used = True
            messages.error(request, "User does not exist.")
            return redirect('login')

    return render(request, 'login.html')


# Logout View
def logout(request):
    request.session.flush()
    messages.success(request, "Logged out successfully.")
    return redirect('login')


# Home View
def home(request):
    if 'user_id' not in request.session:
        return redirect('login')  
    
    user_id = request.session.get("user_id")

    users = User.objects.exclude(id=user_id)  
    context = {
        'user_name': request.session.get('user_name'),
        'user_id': request.session.get('user_id'),
        'users': users,  
    }
    return render(request, 'home.html', context)

def chat(request):
    if 'user_id' not in request.session:
        return redirect('login')  
    
    user_id = request.session.get("user_id")

    users = User.objects.exclude(id=user_id)  
    context = {
        'user_name': request.session.get('user_name'),
        'user_id': request.session.get('user_id'),
        'users': users,  
    }
    return render(request, 'chat.html', context)



def get_or_create_conversation(request, user_id):
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    current_user = get_object_or_404(User, id=request.session['user_id'])
    other_user = get_object_or_404(User, id=user_id)

    # Check if a conversation already exists
    conversation = Conversation.objects.filter(
        (Q(user1=current_user) & Q(user2=other_user)) |
        (Q(user1=other_user) & Q(user2=current_user))
    ).first()

    if not conversation:
        # Create a new conversation
        conversation = Conversation.objects.create(user1=current_user, user2=other_user)

    # Fetch messages for the conversation
    messages = Message.objects.filter(conversation=conversation).order_by('created_at')
    messages_data = [
        {
            'id': message.id,
            'data': message.data,
            'sender': message.sender.name,
            'self': bool(message.sender.id == current_user.id),
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        } for message in messages
    ]

    return JsonResponse({'conversation_id': str(conversation.id), 'messages': messages_data})

def send_message(request):
    if request.method == 'POST' and 'user_id' in request.session:
        conversation_id = request.POST.get('conversation_id')
        data = request.POST.get('message')
        sender = get_object_or_404(User, id=request.session['user_id'])

        conversation = get_object_or_404(Conversation, id=conversation_id)

        # Create the message
        message = Message.objects.create(data=data, sender=sender, conversation=conversation)

        return JsonResponse({
            'id': message.id,
            'data': message.data,
            'sender': message.sender.name,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)