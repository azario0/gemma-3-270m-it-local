import tkinter as tk
from tkinter import ttk, scrolledtext
import multiprocessing
import time
import os
from flask import Flask, request, jsonify, Response
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
import torch
import threading
import signal
import sys

# --- Part 1: Flask Web Server ---
# This code will be run in a separate process.

# Global variables for generation control
current_generation_thread = None
stop_generation_flag = threading.Event()

def run_flask_app():
    """
    Initializes and runs the Flask application to serve the model.
    """
    global current_generation_thread, stop_generation_flag
    
    app = Flask(__name__)

    # --- Load the Model and Tokenizer (only once when the process starts) ---
    local_model_path = "./gemma-3-270m-it-local"
    device = "cpu"  # Change to "cuda" if you have a compatible GPU

    print("Server Process: Loading model and tokenizer...")
    try:
        # Check if the path exists to give a better error message
        if not os.path.isdir(local_model_path):
            raise FileNotFoundError(f"The model directory was not found at '{local_model_path}'. Please ensure it's in the same folder as the script.")
        
        tokenizer = AutoTokenizer.from_pretrained(local_model_path)
        model = AutoModelForCausalLM.from_pretrained(local_model_path)
        model.to(device)
        print("Server Process: Model loaded successfully!")
    except Exception as e:
        print(f"Server Process: Error loading model: {e}")
        model = None

    # --- Enhanced Streaming Endpoint with Stop Functionality ---
    @app.route('/generate-stream', methods=['POST'])
    def stream_generate():
        global current_generation_thread, stop_generation_flag
        
        if model is None:
            return Response("Error: Model is not loaded. Check the terminal for errors.", status=500, mimetype='text/plain')
        
        data = request.get_json()
        prompt = data.get('prompt')

        if not prompt:
            return Response("Error: Prompt not provided.", status=400, mimetype='text/plain')

        # Reset the stop flag for new generation
        stop_generation_flag.clear()

        def generate_tokens():
            global current_generation_thread, stop_generation_flag
            
            try:
                messages = [{"role": "user", "content": prompt}]
                inputs = tokenizer.apply_chat_template(
                    messages, add_generation_prompt=True, tokenize=True,
                    return_dict=True, return_tensors="pt"
                ).to(model.device)

                streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True)

                # Custom generation function that checks for stop flag
                def generation_with_stop():
                    generation_kwargs = dict(**inputs, streamer=streamer, max_new_tokens=4000, do_sample=True)
                    try:
                        model.generate(**generation_kwargs)
                    except Exception as e:
                        print(f"Generation error: {e}")

                # Run generation in a separate thread
                current_generation_thread = threading.Thread(target=generation_with_stop)
                current_generation_thread.start()

                print("Server Process: Starting stream...")
                generated_tokens = 0
                
                for new_text in streamer:
                    # Check if generation should be stopped
                    if stop_generation_flag.is_set():
                        print("Server Process: Generation stopped by request.")
                        break
                    
                    generated_tokens += 1
                    yield new_text
                    
                    # Optional: Stop if no client is listening (connection dropped)
                    # This is handled by Flask automatically when client disconnects
                
                print(f"Server Process: Stream finished. Generated {generated_tokens} tokens.")
                
            except GeneratorExit:
                # This happens when the client disconnects
                print("Server Process: Client disconnected, stopping generation.")
                stop_generation_flag.set()
            except Exception as e:
                print(f"Server Process: Error during generation: {e}")
                stop_generation_flag.set()
        
        # Return the streaming response
        return Response(generate_tokens(), mimetype='text/plain')

    # --- Stop Generation Endpoint ---
    @app.route('/stop-generation', methods=['POST'])
    def stop_generation():
        global stop_generation_flag
        stop_generation_flag.set()
        print("Server Process: Stop generation requested.")
        return jsonify({"message": "Generation stop requested"}), 200

    # --- Check Generation Status ---
    @app.route('/generation-status', methods=['GET'])
    def generation_status():
        global current_generation_thread
        is_generating = current_generation_thread is not None and current_generation_thread.is_alive()
        return jsonify({
            "is_generating": is_generating,
            "stop_requested": stop_generation_flag.is_set()
        }), 200

    # --- Original Non-Streaming Endpoint ---
    @app.route('/generate', methods=['POST'])
    def generate_text():
        if model is None:
            return jsonify({"error": "Model is not loaded."}), 500
        
        data = request.get_json()
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({"error": "Prompt not provided."}), 400
        
        input_ids = tokenizer(prompt, return_tensors="pt").to(device)
        outputs = model.generate(**input_ids, max_new_tokens=150)
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return jsonify({"response": response_text})
        
    @app.route('/health', methods=['GET'])
    def health_check():
        return "OK", 200

    print("Server Process: Starting Flask server on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, threaded=True)


# --- Part 2: Enhanced Tkinter Desktop Application ---

class ModelHostApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Local Model Server")
        self.root.geometry("800x700")  # Increased size for new features
        self.root.configure(bg='#f0f0f0')

        self.server_process = None
        self.status_update_job = None

        style = ttk.Style()
        style.configure('TButton', font=('Helvetica', 12), padding=10)
        style.configure('SmallButton.TButton', font=('Helvetica', 10), padding=5)
        style.configure('TLabel', font=('Helvetica', 12), background='#f0f0f0')
        style.configure('TFrame', background='#f0f0f0')
        style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'))
        style.configure('Status.TLabel', font=('Helvetica', 11), background='#f0f0f0')

        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_label = ttk.Label(main_frame, text="Gemma Model Control Panel", style='Header.TLabel')
        header_label.pack(pady=(0, 20))

        # Server Status and Control Section
        server_frame = ttk.LabelFrame(main_frame, text="Server Control", padding="15")
        server_frame.pack(fill=tk.X, pady=10)

        # Server control buttons
        button_frame = ttk.Frame(server_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_button = ttk.Button(button_frame, text="Start Server", command=self.start_server, style='TButton')
        self.start_button.pack(side=tk.LEFT, expand=True, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED, style='TButton')
        self.stop_button.pack(side=tk.RIGHT, expand=True, padx=5)

        self.status_label = ttk.Label(server_frame, text="Status: Idle", style='Status.TLabel')
        self.status_label.pack(pady=5)

        # Generation Control Section
        generation_frame = ttk.LabelFrame(main_frame, text="Generation Control", padding="15")
        generation_frame.pack(fill=tk.X, pady=10)

        # Generation status display
        gen_status_frame = ttk.Frame(generation_frame)
        gen_status_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(gen_status_frame, text="Generation Status:", style='TLabel').pack(side=tk.LEFT)
        self.generation_status_label = ttk.Label(gen_status_frame, text="Idle", style='Status.TLabel', foreground='green')
        self.generation_status_label.pack(side=tk.LEFT, padx=(10, 0))

        # Generation control buttons
        gen_control_frame = ttk.Frame(generation_frame)
        gen_control_frame.pack(fill=tk.X, pady=5)

        self.stop_generation_button = ttk.Button(
            gen_control_frame, 
            text="Stop Generation", 
            command=self.stop_generation, 
            state=tk.DISABLED, 
            style='SmallButton.TButton'
        )
        self.stop_generation_button.pack(side=tk.LEFT, padx=5)

        self.refresh_status_button = ttk.Button(
            gen_control_frame, 
            text="Refresh Status", 
            command=self.manual_refresh_status, 
            state=tk.DISABLED, 
            style='SmallButton.TButton'
        )
        self.refresh_status_button.pack(side=tk.LEFT, padx=5)

        # Auto-refresh checkbox
        self.auto_refresh_var = tk.BooleanVar(value=True)
        self.auto_refresh_check = ttk.Checkbutton(
            gen_control_frame, 
            text="Auto-refresh (every 2s)", 
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh
        )
        self.auto_refresh_check.pack(side=tk.RIGHT, padx=5)

        # Test Generation Section
        test_frame = ttk.LabelFrame(main_frame, text="Test Generation", padding="15")
        test_frame.pack(fill=tk.X, pady=10)

        # Test prompt input
        prompt_frame = ttk.Frame(test_frame)
        prompt_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(prompt_frame, text="Test Prompt:", style='TLabel').pack(anchor=tk.W)
        self.test_prompt_entry = tk.Entry(prompt_frame, font=('Helvetica', 11), width=60)
        self.test_prompt_entry.pack(fill=tk.X, pady=(5, 0))
        self.test_prompt_entry.insert(0, "Tell me a short joke")

        # Test buttons
        test_button_frame = ttk.Frame(test_frame)
        test_button_frame.pack(fill=tk.X, pady=5)

        self.test_stream_button = ttk.Button(
            test_button_frame, 
            text="Test Stream", 
            command=self.test_stream_generation, 
            state=tk.DISABLED, 
            style='SmallButton.TButton'
        )
        self.test_stream_button.pack(side=tk.LEFT, padx=5)

        self.test_complete_button = ttk.Button(
            test_button_frame, 
            text="Test Complete", 
            command=self.test_complete_generation, 
            state=tk.DISABLED, 
            style='SmallButton.TButton'
        )
        self.test_complete_button.pack(side=tk.LEFT, padx=5)

        # Test output
        self.test_output = scrolledtext.ScrolledText(
            test_frame, 
            height=6, 
            font=('Consolas', 10),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.test_output.pack(fill=tk.X, pady=(10, 0))

        # Instructions
        instructions_frame = ttk.LabelFrame(main_frame, text="API Information", padding="15")
        instructions_frame.pack(fill=tk.X, pady=10)
        
        instructions_text = (
            "API Endpoints:\n"
            "  • Streaming: POST http://127.0.0.1:5000/generate-stream\n"
            "  • Complete response: POST http://127.0.0.1:5000/generate\n"
            "  • Stop generation: POST http://127.0.0.1:5000/stop-generation\n"
            "  • Generation status: GET http://127.0.0.1:5000/generation-status"
        )
        instructions_label = ttk.Label(instructions_frame, text=instructions_text, justify=tk.LEFT, wraplength=600)
        instructions_label.pack(fill=tk.X)

        # Python notebook usage example (collapsible)
        usage_frame = ttk.LabelFrame(main_frame, text="Python Notebook Usage", padding="15")
        usage_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Show/Hide button for usage code
        self.show_usage_var = tk.BooleanVar(value=False)
        self.toggle_usage_button = ttk.Button(
            usage_frame, 
            text="Show Usage Code", 
            command=self.toggle_usage_display,
            style='SmallButton.TButton'
        )
        self.toggle_usage_button.pack(pady=(0, 10))

        # Usage text (initially hidden)
        self.usage_text = scrolledtext.ScrolledText(
            usage_frame, 
            height=8, 
            font=('Consolas', 9),
            wrap=tk.WORD
        )
        
        # Insert usage example
        usage_example = '''import requests

BASE_URL = "http://127.0.0.1:5000"

def stream_generate(prompt):
    response = requests.post(f"{BASE_URL}/generate-stream", json={"prompt": prompt}, stream=True)
    if response.status_code == 200:
        for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
            if chunk: print(chunk, end='', flush=True)

def stop_generation():
    return requests.post(f"{BASE_URL}/stop-generation").json()

def check_status():
    return requests.get(f"{BASE_URL}/generation-status").json()

# Usage: stream_generate("Tell me a joke")'''

        self.usage_text.insert(tk.END, usage_example)
        self.usage_text.config(state=tk.DISABLED)

        # Copy button for usage code
        self.copy_button = ttk.Button(usage_frame, text="Copy to Clipboard", command=self.copy_usage, style='SmallButton.TButton')

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_usage_display(self):
        """Toggle the visibility of usage code."""
        if self.show_usage_var.get():
            # Hide the usage code
            self.usage_text.pack_forget()
            self.copy_button.pack_forget()
            self.toggle_usage_button.config(text="Show Usage Code")
            self.show_usage_var.set(False)
        else:
            # Show the usage code
            self.usage_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            self.copy_button.pack()
            self.toggle_usage_button.config(text="Hide Usage Code")
            self.show_usage_var.set(True)

    def copy_usage(self):
        """Copy the usage example to clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.usage_text.get(1.0, tk.END))
        # Show temporary feedback
        original_text = self.status_label.cget("text")
        self.status_label.config(text="Usage code copied to clipboard!")
        self.root.after(2000, lambda: self.status_label.config(text=original_text))

    def make_request(self, url, method='GET', data=None):
        """Make HTTP requests to the server."""
        try:
            import requests
            if method == 'POST':
                response = requests.post(url, json=data, timeout=5)
            else:
                response = requests.get(url, timeout=5)
            return response
        except ImportError:
            self.log_to_output("Error: requests library not installed. Run: pip install requests")
            return None
        except Exception as e:
            self.log_to_output(f"Request error: {e}")
            return None

    def log_to_output(self, message):
        """Log message to test output area."""
        self.test_output.config(state=tk.NORMAL)
        self.test_output.insert(tk.END, f"{message}\n")
        self.test_output.see(tk.END)
        self.test_output.config(state=tk.DISABLED)

    def clear_output(self):
        """Clear the test output area."""
        self.test_output.config(state=tk.NORMAL)
        self.test_output.delete(1.0, tk.END)
        self.test_output.config(state=tk.DISABLED)

    def stop_generation(self):
        """Stop current generation via API."""
        if not self.server_process or not self.server_process.is_alive():
            self.log_to_output("Server is not running!")
            return

        response = self.make_request("http://127.0.0.1:5000/stop-generation", method='POST')
        if response and response.status_code == 200:
            result = response.json()
            self.log_to_output(f"Stop request sent: {result.get('message', 'OK')}")
            self.manual_refresh_status()
        else:
            self.log_to_output("Failed to send stop request")

    def refresh_generation_status(self):
        """Refresh generation status from server."""
        if not self.server_process or not self.server_process.is_alive():
            self.generation_status_label.config(text="Server Offline", foreground='red')
            self.stop_generation_button.config(state=tk.DISABLED)
            return

        response = self.make_request("http://127.0.0.1:5000/generation-status")
        if response and response.status_code == 200:
            status_data = response.json()
            is_generating = status_data.get('is_generating', False)
            stop_requested = status_data.get('stop_requested', False)
            
            if is_generating:
                if stop_requested:
                    status_text = "Stopping..."
                    status_color = 'orange'
                else:
                    status_text = "Generating"
                    status_color = 'blue'
                self.stop_generation_button.config(state=tk.NORMAL)
            else:
                status_text = "Idle"
                status_color = 'green'
                self.stop_generation_button.config(state=tk.DISABLED)
                
            self.generation_status_label.config(text=status_text, foreground=status_color)
        else:
            self.generation_status_label.config(text="Unknown", foreground='red')
            self.stop_generation_button.config(state=tk.DISABLED)

    def manual_refresh_status(self):
        """Manually refresh status (called by button)."""
        self.refresh_generation_status()

    def auto_refresh_status(self):
        """Automatically refresh status if enabled."""
        if self.auto_refresh_var.get() and self.server_process and self.server_process.is_alive():
            self.refresh_generation_status()
        
        # Schedule next refresh
        if self.server_process and self.server_process.is_alive():
            self.status_update_job = self.root.after(2000, self.auto_refresh_status)

    def toggle_auto_refresh(self):
        """Toggle auto-refresh functionality."""
        if self.auto_refresh_var.get() and self.server_process and self.server_process.is_alive():
            self.auto_refresh_status()
        elif self.status_update_job:
            self.root.after_cancel(self.status_update_job)
            self.status_update_job = None

    def test_stream_generation(self):
        """Test streaming generation with the current prompt."""
        if not self.server_process or not self.server_process.is_alive():
            self.log_to_output("Server is not running!")
            return

        prompt = self.test_prompt_entry.get().strip()
        if not prompt:
            self.log_to_output("Please enter a test prompt!")
            return

        self.clear_output()
        self.log_to_output(f"Testing stream generation with: '{prompt}'")
        self.log_to_output("Response: ")

        # Make streaming request
        try:
            import requests
            response = requests.post(
                "http://127.0.0.1:5000/generate-stream",
                json={"prompt": prompt},
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                full_response = ""
                for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
                    if chunk:
                        full_response += chunk
                        # Update the output in real-time
                        self.test_output.config(state=tk.NORMAL)
                        self.test_output.insert(tk.END, chunk)
                        self.test_output.see(tk.END)
                        self.test_output.config(state=tk.DISABLED)
                        self.root.update()  # Force GUI update
                
                self.log_to_output(f"\n\n--- Generation complete ({len(full_response)} characters) ---")
            else:
                self.log_to_output(f"Error: {response.text}")
                
        except ImportError:
            self.log_to_output("Error: requests library not installed. Run: pip install requests")
        except Exception as e:
            self.log_to_output(f"Stream test error: {e}")

    def test_complete_generation(self):
        """Test complete generation with the current prompt."""
        if not self.server_process or not self.server_process.is_alive():
            self.log_to_output("Server is not running!")
            return

        prompt = self.test_prompt_entry.get().strip()
        if not prompt:
            self.log_to_output("Please enter a test prompt!")
            return

        self.clear_output()
        self.log_to_output(f"Testing complete generation with: '{prompt}'")
        self.log_to_output("Please wait...")

        response = self.make_request("http://127.0.0.1:5000/generate", method='POST', data={"prompt": prompt})
        if response and response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '')
            self.log_to_output("Response:")
            self.log_to_output(response_text)
        else:
            self.log_to_output("Failed to get response from server")

    def start_server(self):
        self.status_label.config(text="Status: Loading model... Please wait.")
        self.start_button.config(state=tk.DISABLED)
        self.server_process = multiprocessing.Process(target=run_flask_app)
        self.server_process.start()
        self.root.after(5000, self.update_status_running)

    def update_status_running(self):
        if self.server_process and self.server_process.is_alive():
            self.status_label.config(text="Status: Running on http://127.0.0.1:5000")
            self.stop_button.config(state=tk.NORMAL)
            # Enable generation control buttons
            self.refresh_status_button.config(state=tk.NORMAL)
            self.test_stream_button.config(state=tk.NORMAL)
            self.test_complete_button.config(state=tk.NORMAL)
            # Start auto-refresh if enabled
            if self.auto_refresh_var.get():
                self.auto_refresh_status()
        else:
            self.status_label.config(text="Status: Error - Failed to start server. Check terminal.")
            self.start_button.config(state=tk.NORMAL)

    def stop_server(self):
        # Cancel auto-refresh
        if self.status_update_job:
            self.root.after_cancel(self.status_update_job)
            self.status_update_job = None
            
        if self.server_process and self.server_process.is_alive():
            self.server_process.terminate()
            self.server_process.join()
            self.status_label.config(text="Status: Server Stopped")
        else:
            self.status_label.config(text="Status: Idle (Server was not running)")
            
        # Disable generation control buttons
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.stop_generation_button.config(state=tk.DISABLED)
        self.refresh_status_button.config(state=tk.DISABLED)
        self.test_stream_button.config(state=tk.DISABLED)
        self.test_complete_button.config(state=tk.DISABLED)
        
        # Reset generation status
        self.generation_status_label.config(text="Idle", foreground='green')

    def on_closing(self):
        # Cancel any scheduled updates
        if self.status_update_job:
            self.root.after_cancel(self.status_update_job)
            
        if self.server_process and self.server_process.is_alive():
            self.stop_server()
        self.root.destroy()


if __name__ == "__main__":
    multiprocessing.set_start_method('fork', force=True)
    root = tk.Tk()
    app = ModelHostApp(root)
    root.mainloop()