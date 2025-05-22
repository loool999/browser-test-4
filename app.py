# Flask essentials for web application development
from flask import Flask, render_template, request, session # Added session
# SocketIO for real-time bidirectional event-based communication
from flask_socketio import SocketIO, emit, join_room, leave_room # Added join_room, leave_room
# Standard Python library for interacting with the operating system (e.g., path manipulation, directory creation)
import os
# For encoding image bytes to base64
import base64
# For handling byte streams (though not directly used here, good for future IO with images)
import io
# Selenium for web automation and browser interaction
from selenium import webdriver
# Selenium options for configuring the Chrome driver (e.g., headless mode)
from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By # Example if needed
# from selenium.webdriver.support.ui import WebDriverWait # Example if needed

# Comment out or remove: send_from_directory, ActionChains if no longer used directly
# from flask import send_from_directory, jsonify # jsonify might be used for other non-SocketIO routes
# from selenium.webdriver.common.action_chains import ActionChains 


# Initialize the Flask application
app = Flask(__name__)
# Secret key for Flask session management; essential for security
app.secret_key = os.urandom(24) 
# Initialize SocketIO with the Flask app, using gevent for asynchronous operations
socketio = SocketIO(app, async_mode='gevent')

# Global dictionary to store active WebDriver instances, keyed by client session ID (SID)
active_drivers = {}  

# Ensure 'templates' directory exists for HTML files (checked at startup)
if not os.path.exists("templates"):
    os.makedirs("templates")

# Ensure 'static' directory exists (though not used for streaming, good for other static assets)
if not os.path.exists("static"):
    os.makedirs("static")

def init_browser():
    """
    Initializes a headless Chrome browser instance with specific options.
    
    Returns:
        selenium.webdriver.chrome.webdriver.WebDriver: The initialized WebDriver instance, or None if initialization fails.
    """
    options = Options()
    options.add_argument("--headless")  # Run Chrome in headless mode (no GUI)
    options.add_argument("--no-sandbox") # Bypass OS security model; often needed in containerized/CI environments
    options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems in some environments
    options.add_argument("--disable-gpu") # Disable GPU hardware acceleration; often recommended for headless
    options.add_argument("--window-size=1280x800") # Set a consistent window size for screenshots
    
    try:
        # Attempt to create a new Chrome WebDriver instance
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        # Log errors if WebDriver initialization fails
        print(f"Error initializing WebDriver: {e}")
        print("Please ensure ChromeDriver is installed and in your PATH, and compatible with your Chrome browser version.")
        return None

# Route for the main page
@app.route('/')
def index():
    """
    Serves the main HTML page (index.html).
    Passes the 'target_url' from the session if it exists, to pre-fill the URL input.
    """
    return render_template('index.html', requested_url=session.get('target_url'))

# Route to handle initial URL submission (before WebSocket connection)
@app.route('/navigate', methods=['POST'])
def navigate():
    """
    Handles POST requests for initial URL submission.
    Stores the URL in the Flask session and re-renders index.html.
    The client-side JavaScript is then expected to establish a WebSocket connection
    and send a 'start_stream' event with this URL.
    """
    url = request.form.get('url')
    if not url:
        return "URL is required", 400 # Basic error response
    
    session['target_url'] = url # Store the submitted URL in the session
    print(f"URL '{url}' stored in session. Client should now connect WebSocket and send 'start_stream'.")
    
    # Re-render index.html; the JavaScript on this page will handle WebSocket connection
    return render_template('index.html', requested_url=url)


# --- SocketIO Event Handlers ---

@socketio.on('connect')
def handle_connect():
    """
    Handles new client WebSocket connections.
    Each client joins a unique room identified by their session ID (SID).
    """
    sid = request.sid
    join_room(sid) # Client joins a room named after their SID
    print(f"Client connected: {sid}. Joined room: {sid}.")
    # Inform client they are connected and should send 'start_stream'
    emit('status', {'message': 'Connected. Please provide URL via "start_stream" event.'}, room=sid)

@socketio.on('start_stream')
def handle_start_stream(data):
    """
    Handles the 'start_stream' event from a client.
    The client sends the URL they want to stream.
    If a stream already exists for this client, it's stopped before starting a new one.
    """
    sid = request.sid
    url = data.get('url')

    if not url:
        emit('status', {'message': 'URL is required to start stream.'}, room=sid)
        return

    print(f"Received 'start_stream' from {sid} for URL: {url}")

    # If a WebDriver instance already exists for this client (e.g., previous stream), clean it up.
    if sid in active_drivers:
        print(f"Stopping existing stream for {sid} before starting new one.")
        old_driver = active_drivers.pop(sid, None) # Remove and get the old driver
        if old_driver:
            try:
                old_driver.quit() # Close the old browser instance
                print(f"Old driver for {sid} quit.")
            except Exception as e:
                print(f"Error quitting old driver for {sid}: {e}")
       
    # Start the screenshot streaming in a new background task
    socketio.start_background_task(target=stream_screenshots, sid=sid, url_to_load=url)
    emit('status', {'message': f'Streaming initiated for {url}.'}, room=sid)

def stream_screenshots(sid, url_to_load):
    """
    Background task to continuously take screenshots of a URL and stream them to the client.
    This function runs in a separate thread managed by SocketIO.
    
    Args:
        sid (str): The session ID of the client to stream to.
        url_to_load (str): The URL to navigate to and screenshot.
    """
    print(f"Background screenshot streaming task started for {sid} to URL: {url_to_load}")
    driver = init_browser() # Initialize a new browser instance for this stream

    if not driver:
        print(f"Failed to initialize browser for stream: {sid}")
        socketio.emit('stream_error', {'error': 'Browser initialization failed.'}, room=sid)
        return

    active_drivers[sid] = driver # Store this driver, associating it with the client's SID
    print(f"Driver for {sid} (URL: {url_to_load}) stored in active_drivers.")

    try:
        # Ensure the URL has a scheme (http or https)
        if not url_to_load.startswith(('http://', 'https://')):
            url_to_load = 'http://' + url_to_load
           
        driver.get(url_to_load) # Navigate to the target URL
        print(f"Driver for {sid} navigated to {url_to_load}")

        # Streaming loop: continues as long as this driver is the active one for the SID
        while sid in active_drivers and active_drivers.get(sid) == driver:
            try:
                # Capture screenshot as PNG bytes
                img_bytes = driver.get_screenshot_as_png()
                # Encode bytes to base64 string for transmission over WebSocket
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                # Emit the screenshot data to the client's room
                socketio.emit('screenshot_update', {'image': img_base64}, room=sid)
                # Control frame rate (e.g., 20 FPS)
                socketio.sleep(1/20) 
            except Exception as e:
                print(f"Error during screenshot/emit for {sid} on {url_to_load}: {e}")
                socketio.emit('stream_error', {'error': f'Screenshot or emit error: {str(e)}'}, room=sid)
                break # Exit loop on error
        print(f"Streaming loop for {sid} to {url_to_load} ended. Driver in active_drivers for sid: {active_drivers.get(sid)==driver}")

    except Exception as e:
        # Handle errors during initial navigation or setup
        print(f"Error in stream_screenshots setup (e.g., navigation) for {sid} on {url_to_load}: {e}")
        socketio.emit('stream_error', {'error': f'Navigation or setup error: {str(e)}'}, room=sid)
    finally:
        # Cleanup: Ensure the driver for this specific task is quit and removed from active_drivers.
        # This 'finally' block is crucial for resource management.
        current_driver_for_sid = active_drivers.get(sid)
        
        if current_driver_for_sid == driver:
            # This task's driver is still the one associated with the SID, so clean it up.
            print(f"Cleaning up driver for {sid} (URL: {url_to_load}) from its stream_screenshots task.")
            driver.quit()
            del active_drivers[sid]
            print(f"Driver for {sid} (URL: {url_to_load}) removed from active_drivers.")
        elif driver: 
            # The driver for this SID was replaced by a new stream, or removed by disconnect.
            # This instance of the driver (for an old stream) still needs to be quit.
            print(f"Driver for {sid} (URL: {url_to_load}) seems to be orphaned or replaced. Quitting it now.")
            driver.quit()
            print(f"Orphaned/replaced driver for {sid} (URL: {url_to_load}) quit.")
        
        print(f"Stream_screenshots task for {sid} (URL: {url_to_load}) fully concluded.")


@socketio.on('disconnect')
def handle_disconnect():
    """
    Handles client disconnections.
    Cleans up resources associated with the disconnected client, primarily their WebDriver instance.
    """
    sid = request.sid
    print(f"Client disconnected: {sid}. Cleaning up...")
    
    driver = active_drivers.pop(sid, None) # Remove driver from active_drivers and get it
    if driver:
        try:
            driver.quit() # Close the browser instance
            print(f"Driver for {sid} quit successfully due to disconnect.")
        except Exception as e:
            print(f"Error quitting driver for {sid} on disconnect: {e}")
            
    # session.pop('target_url', None) # Optionally clear Flask session data
    leave_room(sid) # Ensure client is removed from their SocketIO room
    print(f"Resources for {sid} cleaned up after disconnect.")

# Main entry point for running the Flask-SocketIO application
if __name__ == '__main__':
    print("Starting Flask-SocketIO server with gevent...")
    # Run the app using SocketIO's server, enabling gevent for async operations.
    # Host '0.0.0.0' makes the server accessible externally.
    # Debug mode should be False in production.
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)

# Old HTTP-based screenshot/click logic (commented out or deleted as per instructions)
# def navigate_and_screenshot(driver, url, filename="screenshot.png"): ...
# def navigate_click_and_screenshot(driver, url, x, y, filename="screenshot.png"): ...
# @app.route('/click', methods=['POST']) def handle_click(): ...
# (Also ensure jsonify and other specific imports for these are removed if not used elsewhere)
# The `app.run` for standard Flask development server is replaced by `socketio.run`.
