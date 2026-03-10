from flask import Flask, render_template, Response, request, jsonify
import mss
import cv2
import numpy as np
import pyautogui
import socket

# Initialize the Flask application
app = Flask(__name__)

# State dictionary for dynamic settings
state = {
    'rotation': 0
}

# Configure pyautogui
# FAILSAFE is disabled so we can move the mouse to the very edge of the screen
# without unintentionally triggering pyautogui's anti-lockout fail-safe.
pyautogui.FAILSAFE = False 
# Remove default delay so real-time control feels responsive
pyautogui.PAUSE = 0.0      

def get_local_ip():
    """Helper function to find the local IP address of this PC."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't even have to be reachable, but using a public IP ensures
        # the OS routing table selects the primary active internet interface (like WiFi)
        s.connect(('8.8.8.8', 80))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def generate_frames():
    """
    Generator function that continuously captures the screen,
    compresses it into a JPEG, and yields it for the MJPEG video stream.
    """
    with mss.mss() as sct:
        # Get the primary monitor configuration
        monitor = sct.monitors[1]
        
        while True:
            # 1. Capture the screen using mss
            img = sct.grab(monitor)
            
            # 2. Convert to a numpy array for OpenCV processing
            frame = np.array(img)
            
            # 3. mss captures in BGRA format, but we just need BGR for video
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # Apply any requested rotation mapping
            rot = state['rotation']
            if rot == 90:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif rot == 180:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            elif rot == 270:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            # 4. Encode the frame as a JPEG
            # Quality is set to 70 to balance bandwidth vs visual quality
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            if not ret:
                continue
                
            frame_bytes = buffer.tobytes()
            
            # 5. Yield the frame in MJPEG boundary format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    """Serves the main HTML interface."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """
    Provides the multipart MJPEG stream. The browser keeps the connection
    open and continuously receives new frames.
    """
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/settings', methods=['POST'])
def update_settings():
    """Endpoint to update global server settings like rotation."""
    data = request.json
    if data.get('rotate_right'):
        state['rotation'] = (state['rotation'] + 90) % 360
    return jsonify({"status": "success", "rotation": state['rotation']})

@app.route('/action', methods=['POST'])
def action():
    """
    API endpoint that receives mouse coordinates and action types from the client.
    Coordinates are normalized (0.0 to 1.0) so they scale regardless of the client screen size.
    """
    data = request.json
    action_type = data.get('type')
    button = data.get('button', 'left') # Left by default
    norm_x = data.get('x')  # Percentage along X axis
    norm_y = data.get('y')  # Percentage along Y axis
    
    if norm_x is not None and norm_y is not None:
        # Get the actual screen dimensions in pixels
        screen_width, screen_height = pyautogui.size()
        
        # Calculate the target pixel coordinates taking rotation into account
        rot = state['rotation']
        if rot == 90:
            orig_nx = norm_y
            orig_ny = 1.0 - norm_x
        elif rot == 180:
            orig_nx = 1.0 - norm_x
            orig_ny = 1.0 - norm_y
        elif rot == 270:
            orig_nx = 1.0 - norm_y
            orig_ny = norm_x
        else:
            orig_nx = norm_x
            orig_ny = norm_y

        abs_x = int(orig_nx * screen_width)
        abs_y = int(orig_ny * screen_height)
        
        # Clamp coordinates to screen boundaries to prevent errors
        abs_x = max(0, min(screen_width - 1, abs_x))
        abs_y = max(0, min(screen_height - 1, abs_y))
        
        if action_type == 'tap':
            # Perform click (left or right supported)
            pyautogui.click(abs_x, abs_y, button=button)
        elif action_type == 'move':
            # Move the mouse without clicking
            pyautogui.moveTo(abs_x, abs_y)
        elif action_type == 'down':
            # Press mouse button down for dragging
            pyautogui.mouseDown(abs_x, abs_y, button=button)
        elif action_type == 'up':
            # Release mouse button after dragging
            pyautogui.mouseUp(abs_x, abs_y, button=button)
            
    return jsonify({"status": "success"})

@app.route('/key', methods=['POST'])
def handle_key():
    """Endpoint to handle keyboard input from the client."""
    data = request.json
    key = data.get('key')
    text = data.get('text')
    
    # We use pyautogui.write for full text and pyautogui.press for special keys
    if text:
        pyautogui.write(text)
    elif key:
        pyautogui.press(key)
        
    return jsonify({"status": "success"})

if __name__ == '__main__':
    # Print out connection instructions
    ip = get_local_ip()
    print("="*50)
    print(f"Server is starting! Access the remote desktop on your phone by visiting:")
    print(f"http://{ip}:5000")
    print("Make sure your phone and PC are connected to the same WiFi network.")
    print("="*50)
    
    # Run the Flask app on all interfaces (0.0.0.0) so other devices can access it.
    # threaded=True allows it to handle the video stream and API requests simultaneously.
    app.run(host='0.0.0.0', port=5000, threaded=True)
