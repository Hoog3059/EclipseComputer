import time
import queue
import threading
from flask import Flask, Response, render_template_string
import gphoto2 as gp

app = Flask(__name__)

# Thread-safe queue to pass frames from the background thread to web clients
frame_queue = queue.Queue(maxsize=10)


# --- 1. Background Worker Thread ---

def image_fetcher_thread():
    """
    This function runs continuously in a separate thread.
    Replace the body of this loop with your actual camera/API/socket reading code.
    """
    print("[Thread] Image fetcher started...")

    camera = gp.Camera()
    camera.init()
    
    while True:
        try:
            file = camera.capture_preview()

            
            # Simulated frame fetching delay (e.g., ~30 FPS)
            time.sleep(1 / 30)
            
            # Example placeholder: create a raw JPEG byte array or fetch from your source
            jpeg_bytes = bytes(file.get_data_and_size())

            # Push to queue (drop oldest frame if queue gets backed up)
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()
                except queue.Empty:
                    pass
            frame_queue.put(jpeg_bytes)

        except Exception as e:
            print(f"[Thread Error] {e}")
            time.sleep(1)


# --- 2. Web Server & MJPEG Generator ---

def mjpeg_generator():
    """Yields frames from the queue to active HTTP connections."""
    boundary = "frame"
    while True:
        # Wait for the next frame from the background thread
        jpeg_bytes = frame_queue.get()

        header = (
            f"--{boundary}\r\n"
            f"Content-Type: image/jpeg\r\n"
            f"Content-Length: {len(jpeg_bytes)}\r\n\r\n"
        ).encode("utf-8")

        yield header + jpeg_bytes + b"\r\n"


@app.route("/video_feed")
def video_feed():
    return Response(
        mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/")
def index():
    return render_template_string("""
        <!DOCTYPE html>
        <html>
            <body style="background:#111; display:flex; justify-content:center; align-items:center; height:100vh; margin:0;">
                <img src="/video_feed" style="max-width:90%; max-height:90%; border:2px solid #555;" />
            </body>
        </html>
    """)


# --- 3. App Entry Point ---

if __name__ == "__main__":
    # Start the image fetcher as a daemon thread.
    # daemon=True ensures the thread terminates automatically when the main Flask process stops.
    fetcher = threading.Thread(target=image_fetcher_thread, daemon=True)
    fetcher.start()

    # Run Flask server
    app.run(host="0.0.0.0", port=5000, threaded=True)