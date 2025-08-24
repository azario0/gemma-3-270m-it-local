from transformers import AutoTokenizer, AutoModelForCausalLM
import os

# --- Step 1: Log in to Hugging Face Hub ---
# Make sure you have run 'huggingface-cli login' in your terminal
# and entered your access token.

# --- Step 2: Define Model and Save Directory ---
model_id = "google/gemma-3-270m-it"
save_directory = "./gemma-3-270m-it-local"

# Create the directory if it doesn't exist
os.makedirs(save_directory, exist_ok=True)

try:
    # --- Step 3: Download and Save Tokenizer ---
    print(f"Downloading tokenizer for '{model_id}'...")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.save_pretrained(save_directory)
    print(f"Tokenizer saved successfully to '{save_directory}'")

    # --- Step 4: Download and Save Model ---
    print(f"Downloading model '{model_id}'... This may take a while.")
    model = AutoModelForCausalLM.from_pretrained(model_id)
    model.save_pretrained(save_directory)
    print(f"Model saved successfully to '{save_directory}'")

    print("\n✅ Download and save complete.")
    print(f"You can now find the model files in the '{save_directory}' directory.")

except Exception as e:
    print(f"\n❌ An error occurred: {e}")
    print("Please ensure you have accepted the model's terms on the Hugging Face website and are logged in via 'huggingface-cli login'.")