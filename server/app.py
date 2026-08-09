import time
import queue
import threading
from flask import Flask, Response, jsonify, render_template_string, request, make_response
import gphoto2 as gp
from flask_cors import CORS, cross_origin
import subprocess
import logging

from camera_worker import camera_worker, preview_frame_queue, command_queue, get_state, update_state, start_intervallometer
import camera_commands

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.route("/computer/shutdown")
def shutdown():
    subprocess.Popen(['shutdown','-h','now'])


#################
# System status #
#################


@app.route("/status")
def status():
    response = jsonify(get_state(full=True))
    return response

############################
# General property setting #
############################


@app.route("/camera/set_property/<string:property_name>")
def set_property(property_name):
    value = request.args.get("value")
    command_queue.put(camera_commands.SetPropertyCommand(property_name, value))
    return "", 202  # Accepted

################
# Live preview #
################


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

################
# Manual focus #
################


@app.route("/camera/manualfocus/<string:focus_command>")
def manual_focus(focus_command):
    command = camera_commands.ManualFocus(
        camera_commands.ManualFocus.FocusOption[focus_command.upper()])
    command_queue.put(command)
    return "", 202  # Accepted


######################
# Partiality bracket #
######################


@app.route("/camera/partiality_bracket")
def partiality_bracket():
    iso = request.args.get("iso")
    aperture = request.args.get("aperture")
    shutterspeed_1 = request.args.get("shutterspeed_1")
    shutterspeed_2 = request.args.get("shutterspeed_2")
    shutterspeed_3 = request.args.get("shutterspeed_3")
    update_state("partiality_bracket_iso", iso)
    update_state("partiality_bracket_aperture", aperture)
    update_state("partiality_bracket_shutterspeed_1", shutterspeed_1)
    update_state("partiality_bracket_shutterspeed_2", shutterspeed_2)
    update_state("partiality_bracket_shutterspeed_3", shutterspeed_3)
    return "", 202


@app.route("/camera/partiality_bracket/start")
def start_partiality_bracket():
    command = camera_commands.CaptureBracket(
        get_state("partiality_bracket_iso"),
        get_state("partiality_bracket_aperture"),
        [
            get_state("partiality_bracket_shutterspeed_1"),
            get_state("partiality_bracket_shutterspeed_2"),
            get_state("partiality_bracket_shutterspeed_3"),
        ],
        lambda: update_state("partiality_bracket_running", False),
    )
    update_state("partiality_bracket_running", True)
    command_queue.put(command)
    return "", 202


@app.route("/camera/partiality_bracket/stop")
def stop_partiality_bracket():
    update_state("stop_bracket", True)
    update_state("partiality_bracket_running", False)
    return "", 202

##############################
# Partiality Intervallometer #
##############################


@app.route("/camera/partiality_intervallometer")
def partiality_intervallometer():
    interval = int(request.args.get("interval"))
    update_state("intervallometer_interval", interval)
    return "", 202


@app.route("/camera/partiality_intervallometer/start")
def start_partiality_intervallometer():
    start_intervallometer(start_partiality_bracket)
    update_state("intervallometer_running", True)
    return "", 202


@app.route("/camera/partiality_intervallometer/stop")
def stop_partiality_intervallometer():
    update_state("intervallometer_running", False)
    return "", 202

####################
# Totality bracket #
####################

@app.route("/camera/totality_bracket")
def totality_bracket():
    iso = request.args.get("iso")
    update_state("totality_bracket_iso", iso)
    return "", 202

@app.route("/camera/totality_bracket/start")
def start_totality_bracket():
    command = camera_commands.CaptureBracket(
        get_state("totality_bracket_iso"),
        "8",
        [
            "1/4000",
            "1/2000",
            "1/1000",
            "1/500",
            "1/250",
            "1/100",
            "1/50",
            "1/25",
            "1/10",
            "1/4",
            "0.5",
            "1",
            "2",
            "5",
            "10"
        ],
        lambda: update_state("totality_bracket_running", False),
    )
    update_state("totality_bracket_running", True)
    command_queue.put(command)
    return "", 202

@app.route("/camera/totality_bracket/stop")
def stop_totality_bracket():
    update_state("stop_bracket", True)
    update_state("totality_bracket_running", False)
    return "", 202

##############
# UI Locking #
##############


@app.route("/camera/lock_ui")
def lock_ui():
    command_queue.put(camera_commands.LockUI())
    return "", 202


@app.route("/camera/unlock_ui")
def unlock_ui():
    command_queue.put(camera_commands.UnlockUI())
    return "", 202

##################
# Single capture #
##################
@app.route("/camera/capture")
def capture():
    command_queue.put(camera_commands.Capture())
    return "", 202

####################
# Get last picture #
####################
@app.route("/camera/last_capture.jpg")
def get_last_capture():
    done_getting = False
    last_capture = None
    def finished(image):
        nonlocal done_getting, last_capture
        done_getting = True
        last_capture = image
    command_queue.put(camera_commands.FetchLastCapture(finished))
    loop_count = 0
    while not done_getting:
        time.sleep(1) # Yield to multithreader and come back to check
        loop_count += 1

        if loop_count > 10:
            placeholder = open("./placeholder_last_image.jpg", "rb").read()
            last_capture = placeholder
            break

    timestamp = int(time.time())
    
    response = make_response(last_capture)
    response.headers.set('Content-Type', 'image/jpeg')
    response.headers.set('Content-Disposition', 'attachment', filename=f'last_capture_{timestamp}.jpg')
    return response

@app.route("/camera/last_capture_placeholder.jpg")
def get_last_capture_placeholder():
    placeholder = open("./placeholder_last_image.jpg", "rb").read()
    last_capture = placeholder
    response = make_response(last_capture)
    response.headers.set('Content-Type', 'image/jpeg')
    response.headers.set('Content-Disposition', 'attachment', filename='last_capture.jpg')
    return response
    
    

if __name__ == "__main__":
    camera_worker_thread = threading.Thread(target=camera_worker, daemon=True)
    camera_worker_thread.start()

    # Run Flask server
    app.run(host="0.0.0.0", port=5000, threaded=True)
