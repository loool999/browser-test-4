# Simple Headless Browser Web UI (with Experimental Streaming)

## Description
This application provides a web interface to interact with a headless Chrome browser. 
Users can enter a URL and view an **experimental real-time stream** of the webpage. 
The previous click-to-interact feature is temporarily disabled in this version.

## Prerequisites
*   Python 3.7+
*   PIP (Python package installer)
*   Google Chrome browser installed.
*   ChromeDriver:
    *   Must be installed and compatible with your version of Google Chrome.
    *   Ensure ChromeDriver is in your system's PATH or its location is specified to Selenium (this script assumes it's in PATH).
    *   Download from: [https://chromedriver.chromium.org/downloads](https://chromedriver.chromium.org/downloads)
*   Key backend technologies now include `Flask-SocketIO` and `gevent` for WebSocket communication and asynchronous operations.

## Setup
1.  **Clone the repository** (or download the files into a project directory).
    ```bash
    # git clone <repository_url> # If it were a git repo
    # cd <project_directory>
    ```
2.  **Create and activate a virtual environment** (recommended):
    ```bash
    python -m venv venv
    ```
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        . venv\Scripts\activate
        ```
3.  **Install dependencies**:
    The `requirements.txt` file includes all necessary packages, such as `Flask`, `Selenium`, `Flask-SocketIO`, and `gevent`.
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application
1.  Execute the Flask application (now using Flask-SocketIO with gevent):
    ```bash
    python app.py
    ```
2.  Open your web browser and navigate to:
    [http://0.0.0.0:8080](http://0.0.0.0:8080) or [http://localhost:8080](http://localhost:8080)

## How to Use
1.  Once the application is running, you'll see an input field.
2.  Enter a full website URL (e.g., `https://www.google.com`) and click "Go / Change URL."
3.  An attempt will be made to stream screenshots of the website to the image area in real-time.
4.  To view a different URL, enter it in the input field and click "Go / Change URL" again. The stream will restart.

## Experimental Streaming Feature
This version now includes an experimental real-time streaming feature using WebSockets (`Flask-SocketIO` with `gevent`).

*   **How it works:** After submitting a URL, the backend attempts to stream screenshots of the headless browser to your client at roughly 20 FPS.
*   **Status:** This is highly experimental.
    *   Performance may vary significantly based on the website being rendered and server/network conditions.
    *   It may not be stable and can consume significant server resources (CPU/memory per connected client).
    *   The interactive click feature (clicking on coordinates) has been temporarily disabled in this version to focus on the streaming experiment.

## Notes and Limitations
*   The screenshot streaming feature is **experimental**, may be unstable, and is resource-intensive.
*   The interactive click functionality (clicking on page coordinates) is **temporarily disabled** in this streaming version.
*   This is a basic demonstration and may not render or stream correctly for all websites, especially those with:
    *   Heavy JavaScript or complex dynamic content.
    *   Complex user interface elements.
    *   Anti-bot measures (like CAPTCHAs).
*   Error handling is implemented but may not cover all edge cases.
*   Screenshots are no longer saved to the `static` folder in this streaming version; they are sent directly over WebSockets.
*   The browser window size is fixed in `app.py`; complex pages might look different than in a regular browser.
