import time
import queue
import threading
from flask import Flask, Response, jsonify, render_template_string, request
import gphoto2 as gp
from flask_cors import CORS, cross_origin

from camera_worker import camera_worker, preview_frame_queue, command_queue, get_state, camera_stop, update_state
import camera_commands

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


def mjpeg_generator():
    """Yields frames from the queue to active HTTP connections."""
    boundary = "frame"

    # Fallback to a placeholder image
    jpeg_bytes = open("./placeholder.jpg", "rb").read()
    header = (
        f"--{boundary}\r\n"
        f"Content-Type: image/jpeg\r\n"
        f"Content-Length: {len(jpeg_bytes)}\r\n\r\n"
    ).encode("utf-8")
    yield header + jpeg_bytes + b"\r\n"

    while True:
        # Wait for the next frame from the background thread
        try:
            jpeg_bytes = preview_frame_queue.get(timeout=1)
        except queue.Empty:
            # Fallback to a placeholder image
            jpeg_bytes = open("./placeholder.jpg", "rb").read()

        header = (
            f"--{boundary}\r\n"
            f"Content-Type: image/jpeg\r\n"
            f"Content-Length: {len(jpeg_bytes)}\r\n\r\n"
        ).encode("utf-8")

        yield header + jpeg_bytes + b"\r\n"


@app.route("/preview_feed")
def video_feed():
    return Response(
        mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/camera/start_preview")
def start_preview():
    command_queue.put(camera_commands.StartPreview())
    return "", 202  # Accepted


@app.route("/camera/stop_preview")
def stop_preview():
    command_queue.put(camera_commands.StopPreview())
    return "", 202  # Accepted


@app.route("/camera/manualfocus/<string:focus_command>")
def manual_focus(focus_command):
    command = camera_commands.ManualFocus(camera_commands.ManualFocus.FocusOption[focus_command.upper()])
    command_queue.put(command)
    return "", 202  # Accepted


@app.route("/camera/set_property/<string:property_name>")
def set_property(property_name):
    value = request.args.get("value")
    command_queue.put(camera_commands.SetPropertyCommand(property_name, value))
    return "", 202  # Accepted

@app.route("/camera/bracket")
def bracket():
    iso = request.args.get("iso")
    aperture = request.args.get("aperture")
    shutterspeed_start = request.args.get("shutterspeed_start")
    shutterspeed_stop = request.args.get("shutterspeed_stop")
    command = camera_commands.PushBracketSettings(
        iso,
        aperture,
        shutterspeed_start,
        shutterspeed_stop
    )
    command_queue.put(command)
    return "", 202

@app.route("/camera/bracket/start")
def start_bracket():
    command_queue.put(camera_commands.StartBracket())
    return "", 202

@app.route("/camera/bracket/stop")
def stop_bracket():
    update_state("bracket_running", False)
    return "", 202


# @app.route("/camera/capture")
# def capture():
#     command_queue.put(CameraCommand.CAPTURE)
#     return "", 202

# @app.route("/camera/capture_hq_preview")
# def capture_hq_preview():
#     command_queue.put(CameraCommand.CAPTURE_SINGLE_HQ_PREVIEW)
#     return "", 202


# @app.route("/camera/totality_image_burst")
# def totality_image_burst():
#     command_queue.put(CameraCommand.START_TOTALITY_IMAGE_BURST)
#     return "", 202


# @app.route("/camera/start_intervallometer")
# def start_intervallometer():
#     interval_s = int(request.args.get("interval_s"))
#     command_queue.put(IntervallometerCommand(True, interval_s))
#     return "", 202

# @app.route("/camera/stop_intervallometer")
# def stop_intervallometer():
#     command_queue.put(IntervallometerCommand(False))
#     return "", 202


@app.route("/status")
def status():
    response = jsonify(get_state(full=True))
    return response


if __name__ == "__main__":
    camera_worker_thread = threading.Thread(target=camera_worker, daemon=True)
    camera_worker_thread.start()

    # Run Flask server
    app.run(host="0.0.0.0", port=5000, threaded=True)
