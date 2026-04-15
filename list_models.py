import os
from dotenv import load_dotenv
from google import genai

# Load your API key from the .env file
load_dotenv()

# Initialize the client
client = genai.Client()

print("🔍 Fetching available Gemini models...\n")
print("-" * 50)

# Fetch and loop through all available models
for model in client.models.list():
    # We only care about models that support text generation
    if 'generateContent' in model.supported_actions:
        print(f"Name:         {model.name}")
        print(f"Display Name: {model.display_name}")
        print(f"Version:      {model.version}")
        print("-" * 50)

print("\n✅ Done!")