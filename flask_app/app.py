from flask import Flask, render_template, request, jsonify, Response
import requests
import json
import threading
import time

app = Flask(__name__)

# Configuration
BASE_URL = "http://127.0.0.1:5000"

class StreamingClient:
    def __init__(self):
        self.is_generating = False
        self.current_session_id = None
    
    def stream_generate(self, prompt, session_id):
        """Stream generation with session tracking"""
        self.is_generating = True
        self.current_session_id = session_id
        
        try:
            response = requests.post(
                f"{BASE_URL}/generate-stream", 
                json={"prompt": prompt}, 
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
                    if not self.is_generating or self.current_session_id != session_id:
                        break
                    if chunk:
                        yield f"data: {json.dumps({'chunk': chunk, 'status': 'generating'})}\n\n"
                        
                # Signal completion
                if self.is_generating and self.current_session_id == session_id:
                    yield f"data: {json.dumps({'status': 'completed'})}\n\n"
            else:
                yield f"data: {json.dumps({'error': f'Server returned status {response.status_code}', 'status': 'error'})}\n\n"
                
        except requests.exceptions.RequestException as e:
            yield f"data: {json.dumps({'error': f'Connection error: {str(e)}', 'status': 'error'})}\n\n"
        finally:
            self.is_generating = False
            self.current_session_id = None
    
    def stop_generation(self):
        """Stop the current generation"""
        self.is_generating = False
        try:
            response = requests.post(f"{BASE_URL}/stop-generation", timeout=5)
            return response.json() if response.status_code == 200 else {"error": "Failed to stop"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Connection error: {str(e)}"}
    
    def check_status(self):
        """Check generation status"""
        try:
            response = requests.get(f"{BASE_URL}/generation-status", timeout=5)
            return response.json() if response.status_code == 200 else {"error": "Failed to get status"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Connection error: {str(e)}"}

# Global streaming client
streaming_client = StreamingClient()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Start streaming generation"""
    data = request.json
    prompt = data.get('prompt', '')
    session_id = data.get('session_id', str(int(time.time())))
    
    if not prompt.strip():
        return jsonify({"error": "Prompt cannot be empty"}), 400
    
    def generate_stream():
        yield "data: " + json.dumps({"status": "started", "session_id": session_id}) + "\n\n"
        yield from streaming_client.stream_generate(prompt, session_id)
    
    return Response(generate_stream(), mimetype='text/event-stream')

@app.route('/stop', methods=['POST'])
def stop():
    """Stop generation"""
    result = streaming_client.stop_generation()
    return jsonify(result)

@app.route('/status')
def status():
    """Get status"""
    result = streaming_client.check_status()
    return jsonify(result)

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Try to connect to the backend
        response = requests.get(f"{BASE_URL}/generation-status", timeout=2)
        backend_status = "connected" if response.status_code == 200 else "error"
    except:
        backend_status = "disconnected"
    
    return jsonify({
        "status": "healthy",
        "backend_status": backend_status,
        "is_generating": streaming_client.is_generating
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)