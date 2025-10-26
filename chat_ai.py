import random

class ChatAI:
    def __init__(self):
        self.responses = [
            "Hi there! How can I help you today? 😊",
            "We appreciate your interest! Would you like to view our latest offers?",
            "I’m here 24/7 — feel free to ask about our products!"
        ]

    def listen_and_reply(self):
        print("💬 Listening to customer queries (simulated)...")
        print(random.choice(self.responses))
