import os
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# Get the variable
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# Print the result
print(f"The secret key is: '{webhook_secret}'")