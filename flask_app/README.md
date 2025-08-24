# AI Text Generator Flask Web Application

A beautiful, modern web interface for your streaming text generation API with real-time updates and a professional UI.

## Features

- 🎨 **Modern Design**: Beautiful gradient UI with glassmorphism effects
- 🔄 **Real-time Streaming**: Live text generation with Server-Sent Events
- 📱 **Responsive**: Works perfectly on desktop and mobile devices
- ⚡ **Fast Performance**: Optimized for smooth real-time updates
- 🛑 **Stop Control**: Ability to stop generation mid-stream
- 📊 **Statistics**: Real-time character and word counts
- 🔍 **Status Monitoring**: Connection status and generation progress
- ⌨️ **Keyboard Shortcuts**: Ctrl+Enter to generate

## Project Structure

```
flask-text-generator/
├── app.py                  # Main Flask application
├── templates/
│   └── index.html         # HTML template
└── requirements.txt       # Python dependencies
```

## Installation

1. **Create project directory:**
```bash
mkdir flask-text-generator
cd flask-text-generator
```

2. **Create and activate virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install flask requests
```

4. **Create the templates directory:**
```bash
mkdir templates
```

5. **Save the files:**
   - Save the Flask application as `app.py`
   - Save the HTML template as `templates/index.html`

## Configuration

The application assumes your text generation API is running on `http://127.0.0.1:5000` with the following endpoints:

- `POST /generate-stream`: Streaming text generation
- `POST /stop-generation`: Stop current generation
- `GET /generation-status`: Get generation status

If your API runs on a different URL, modify the `BASE_URL` variable in `app.py`.

## Usage

1. **Start the Flask application:**
```bash
python app.py
```

2. **Open your browser and go to:**
```
http://127.0.0.1:8080
```

3. **Using the interface:**
   - Enter your prompt in the left textarea
   - Click "Generate" or press Ctrl+Enter to start
   - Watch the real-time streaming output on the right
   - Use "Stop" to halt generation
   - "Clear" to reset the output area

## API Endpoints

The web application provides these endpoints:

- `GET /`: Main web interface
- `POST /generate`: Start streaming generation
- `POST /stop`: Stop current generation
- `GET /status`: Get generation status
- `GET /health`: Health check and backend status

## Technical Features

### Backend Features:
- **Session Management**: Each generation session has a unique ID
- **Error Handling**: Comprehensive error handling with user feedback
- **Connection Management**: Automatic connection status monitoring
- **Threading Safety**: Thread-safe generation state management

### Frontend Features:
- **Server-Sent Events**: Real-time streaming using SSE
- **Responsive Design**: Mobile-first responsive layout
- **Visual Feedback**: Loading spinners, status indicators, and animations
- **Keyboard Shortcuts**: Ctrl+Enter for quick generation
- **Auto-scroll**: Output automatically scrolls during generation
- **Statistics**: Live character and word counting

## Customization

### Styling
The CSS uses CSS custom properties and can be easily customized:
- Colors: Modify the gradient colors in the CSS
- Fonts: Change the font-family properties
- Layout: Adjust the grid layout for different screen sizes

### API Integration
To use with a different API, modify:
1. `BASE_URL` in `app.py`
2. Request format in the `stream_generate` method
3. Response parsing in the `handleStreamData` JavaScript function

## Requirements

```txt
Flask==2.3.3
requests==2.31.0
```

## Security Notes

- The application runs in debug mode by default - disable for production
- No authentication is implemented - add authentication for production use
- CORS headers may need to be configured for cross-origin requests

## Troubleshooting

### Backend Connection Issues:
- Ensure your text generation API is running on the configured URL
- Check that the API endpoints match the expected format
- Verify firewall settings allow connections

### Frontend Issues:
- Check browser console for JavaScript errors
- Ensure WebSocket/SSE connections are not blocked
- Try refreshing the page if streaming stops working

### Performance:
- For long generations, consider implementing pagination
- Monitor memory usage with large outputs
- Consider adding rate limiting for production use

## License

This project is open source and available under the MIT License.