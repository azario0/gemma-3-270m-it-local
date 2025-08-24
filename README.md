# Local LLM Server UI

A simple, self-contained desktop application for downloading, hosting, and interacting with open-source language models like Google's Gemma. This project provides a user-friendly Tkinter GUI to manage a local Flask server that exposes API endpoints for text generation.

**Created by: [azario0](https://github.com/azario0)**

## Core Features

*   **Model Downloader**: A script (`GET_MODEL.py`) to easily download the `google/gemma-3-270m-it` model from the Hugging Face Hub.
*   **Local API Server**: The GUI launches a Flask server in a background process, making the model accessible via a local API.
*   **Interactive GUI**: A user-friendly control panel built with Tkinter to:
    *   Start and stop the model server.
    *   View server status.
    *   Monitor real-time generation status (Idle, Generating, Stopping).
    *   Stop an ongoing text generation process at any time.
*   **API Endpoints**:
    *   `/generate-stream`: For real-time, token-by-token streaming responses.
    *   `/generate`: For complete, single-shot responses.
    *   `/stop-generation`: To gracefully interrupt a streaming task.
    *   `/generation-status`: To check if the model is currently processing a request.
*   **Built-in Testing**: A "Test Generation" panel within the app to send prompts and view streamed or complete responses directly.
*   **Code Snippets**: The UI provides ready-to-use Python code for interacting with the API from your own scripts or notebooks.

## How It Works

The application consists of two main parts:

1.  **`GET_MODEL.py`**: This script connects to the Hugging Face Hub, downloads the specified Gemma model and its tokenizer, and saves them to a local directory (`./gemma-3-270m-it-local`). This only needs to be run once.
2.  **`app_gui.py`**: This is the main application. It launches a Tkinter window that serves as a control panel. When you click "Start Server," it spawns a new process running a Flask web server which loads the downloaded model into memory and exposes the API endpoints. The GUI then communicates with this server via HTTP requests to control generation and test prompts.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3.7+**
*   **Git** (for cloning the repository)
*   **An account on [Hugging Face](https://huggingface.co/)**

You will also need to accept the terms of use for the Gemma model on its Hugging Face page.

## Setup & Usage

**Step 1: Clone the Repository**

```bash
git clone https://github.com/azario0/local-llm-server-ui.git
cd local-llm-server-ui
```

**Step 2: Install Dependencies**

This project relies on several Python libraries. Install them using pip:

```bash
pip install transformers torch tkinter flask requests
```
*(Note: `tkinter` is usually included with Python but may require separate installation on some Linux distributions).*

**Step 3: Log in to Hugging Face Hub**

To download the model, you need to authenticate. Run this command in your terminal and enter a Hugging Face access token when prompted. You can generate a token from your [Hugging Face account settings](https://huggingface.co/settings/tokens).

```bash
huggingface-cli login
```

**Step 4: Download the Model**

Run the `GET_MODEL.py` script. This will download the Gemma model files into a folder named `gemma-3-270m-it-local` in the same directory.

```bash
python GET_MODEL.py
```

**Step 5: Run the Application**

Launch the GUI control panel by running the `app_gui.py` script.

```bash
python app_gui.py
```

**Using the Application:**

1.  Click the **"Start Server"** button. Wait a few moments for the model to be loaded into memory. The status will change to "Running."
2.  Enter a prompt in the "Test Prompt" text box.
3.  Click **"Test Stream"** to see the response generated token by token.
4.  While a stream is in progress, click **"Stop Generation"** to interrupt it.
5.  Use the API endpoints provided in the UI from your own applications (e.g., Jupyter notebooks, custom scripts).

## API Endpoints

The server runs on `http://127.0.0.1:5000`.

| Endpoint             | Method | Body (JSON)          | Description                                                                                             |
| -------------------- | ------ | -------------------- | ------------------------------------------------------------------------------------------------------- |
| `/generate-stream`   | `POST` | `{"prompt": "text"}` | Streams the model's response token by token. Ideal for interactive applications.                      |
| `/generate`          | `POST` | `{"prompt": "text"}` | Returns the full, completed response after the model has finished generating.                          |
| `/stop-generation`   | `POST` | (None)               | Requests the server to stop the current generation stream.                                                |
| `/generation-status` | `GET`  | (None)               | Returns the current generation status (e.g., `{"is_generating": true, "stop_requested": false}`). |

### Python Usage Example

The application provides a built-in code snippet for easy integration.

```python
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def stream_generate(prompt):
    """
    Connects to the streaming endpoint and prints the response token by token.
    """
    try:
        response = requests.post(
            f"{BASE_URL}/generate-stream",
            json={"prompt": prompt},
            stream=True
        )
        response.raise_for_status()  # Raise an exception for bad status codes

        print("Model Response: ", end='')
        for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
            if chunk:
                print(chunk, end='', flush=True)
        print()

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

# --- Example Usage ---
if __name__ == "__main__":
    my_prompt = "Explain the importance of local language models in 3 key points."
    stream_generate(my_prompt)
```

## Contributing

Contributions are welcome! If you have suggestions for improvements or find a bug, please feel free to open an issue or submit a pull request.