import queue
import threading
import time
import gphoto2 as gp
from enum import IntEnum
from gp_error import GP_ERROR
import atexit
from available_camera_settings import available_apertures, available_isos, available_shutterspeeds
import camera_commands
from camera_commands import SetPropertyCommand

camera = None


def close_camera_connection():
    if camera is not None:
        print("Attempting to close connection...")
        camera.exit()


atexit.register(close_camera_connection)

command_queue = queue.Queue(maxsize=10)
preview_frame_queue = queue.Queue(maxsize=10)

camera_state_lock = threading.Lock()
camera_state = {
    # Camera info
    "connected": False,

    "batterylevel": "0%",

    "iso": "200",
    "shutterspeed": "1/800",
    "aperture": "8",

    # Preview info
    "preview_capture": False,

    # All brackets
    "stop_bracket": False,

    # Paritality bracket
    "partiality_bracket_running": False,

    "partiality_bracket_iso": "200",
    "partiality_bracket_aperture": "8",
    "partiality_bracket_shutterspeed_1": "1/1600",
    "partiality_bracket_shutterspeed_2": "1/800",
    "partiality_bracket_shutterspeed_3": "1/400",

    # Partiality Intervallometer
    "intervallometer_running": False,
    "intervallometer_interval": 10,

    # Totality bracket
    "totality_bracket_running": False,
    "totality_bracket_iso": "200",
}


_intervallometer_last_capture = time.time()
_intervallometer_function_to_call = None


def update_state(name, value):
    with camera_state_lock:
        camera_state[name] = value


def get_state(name=None, full=False):
    with camera_state_lock:
        if full:
            return camera_state.copy()
        return camera_state.copy().get(name)


def start_intervallometer(function_to_call):
    global _intervallometer_function_to_call
    global _intervallometer_last_capture
    _intervallometer_function_to_call = function_to_call
    _intervallometer_last_capture = 0
    update_state("intervallometer_running", True)


def stop_intervallometer():
    update_state("intervallometer_running", False)


def camera_worker():
    global camera
    global _intervallometer_last_capture
    global _intervallometer_function_to_call
    camera = gp.Camera()

    while True:
        # --- Establish connection ---
        while not get_state("connected"):
            camera = gp.Camera()
            error = gp.gp_camera_init(camera)
            if error >= GP_ERROR.OK:
                # Success
                print("Camera initialized successfully.")
                update_state("connected", True)

                command_queue.put(
                    SetPropertyCommand("imageformat", "RAW + L")
                )
                command_queue.put(
                    SetPropertyCommand("imageformatsd", "RAW + L")
                )
                command_queue.put(
                    SetPropertyCommand("capturetarget", "Memory card")
                )
            else:
                # Connection issue
                print("No camera found. Retrying...")
                time.sleep(1)

        # --- Check whether we're still connected ---
        error, _ = gp.gp_camera_get_storageinfo(camera)
        if error < GP_ERROR.OK:
            # Not connected or connection issue
            update_state("connected", False)
            continue
        else:
            # No error
            pass

        # --- Get current camera parameters ---
        error, widget = gp.gp_camera_get_config(camera)
        update_state("batterylevel", widget.get_child_by_name(
            "batterylevel").get_value())
        update_state("iso", widget.get_child_by_name("iso").get_value())
        update_state("shutterspeed", widget.get_child_by_name(
            "shutterspeed").get_value())
        update_state("aperture", widget.get_child_by_name(
            "aperture").get_value())

        # --- Intervallometer ---
        if get_state("intervallometer_running"):
            current_time = time.time()
            if current_time > _intervallometer_last_capture + get_state("intervallometer_interval"):
                _intervallometer_last_capture = current_time
                _intervallometer_function_to_call()

        # --- Handle commands for camera in queue ---
        if command_queue.empty():
            error, event_type, event_data = gp.gp_camera_wait_for_event(camera, 100) # Try to keep the camera event queue empty.
            continue

        command = command_queue.get()
        match command:
            case camera_commands.SetPropertyCommand(property_name, value):
                _set_property(camera, widget, property_name, value)
            case camera_commands.StartPreview():
                _start_preview(camera, widget)
            case camera_commands.CapturePreview():
                _capture_preview(camera)
            case camera_commands.StopPreview():
                _stop_preview(camera, widget)
            case camera_commands.ManualFocus():
                _manual_focus_drive(camera, widget, command)
            case camera_commands.UnlockUI():
                _set_property(camera, widget, "uilock", 0)
            case camera_commands.LockUI():
                _set_property(camera, widget, "uilock", 1)
            case camera_commands.CaptureBracket():
                _bracket_capture_next_exposure(camera, widget, command)
            case camera_commands.Capture():
                _capture(camera, widget)
            case camera_commands.FetchLastCapture():
                _fetch_last_capture(camera, widget, command.callback)

            # --- Fallthrough ---
            case _:
                raise ValueError(f"Command {command} is not a valid command.")


def _fetch_last_capture(camera, widget, callback):
    error, list = gp.gp_camera_folder_list_files(camera, "/store_00020001/DCIM/100CANON")
    last_filename = list.get_name(list.count() - 1)
    file = camera.file_get("/store_00020001/DCIM/100CANON", last_filename, gp.GP_FILE_TYPE_NORMAL)
    last_capture = bytes(file.get_data_and_size())
    callback(last_capture)


def _bracket_capture_next_exposure(camera, widget, command: camera_commands.CaptureBracket):
    if get_state("stop_bracket"):
        update_state("stop_bracket", False)
        return

    try:
        current_shutterspeed = command.shutterspeeds.pop(0)
    except IndexError:
        # We captured all shutterspeeds
        if command.capture_done_callback is not None:
            command.capture_done_callback()

        return

    _set_property(camera, widget, "iso", command.iso)
    _set_property(camera, widget, "aperture", command.aperture)
    _set_property(camera, widget, "shutterspeed", current_shutterspeed)
    _capture(camera, widget)
    _wait_for_capture_finish(
        camera,
        total_timeout_ms=int(eval(current_shutterspeed)*1000 + 1000)
    )

    command_queue.put(command)


def _wait_for_capture_finish(camera, timeout_after_file_creation_ms=1000, file_creation_counts_to_wait_for=2, total_timeout_ms=10000):
    file_creations_counted = 0
    while file_creations_counted < file_creation_counts_to_wait_for:
        error, event_type, event_data = gp.gp_camera_wait_for_event(
            camera, total_timeout_ms)
        if event_type == gp.GP_EVENT_FILE_ADDED:
            file_creations_counted += 1
        elif event_type == gp.GP_EVENT_TIMEOUT:
            break
        else:
            pass

    time.sleep(timeout_after_file_creation_ms / 1000)


def _capture(camera, widget):
    widget.get_child_by_name("eosremoterelease").set_value("Press Full MF")
    camera.set_config(widget)
    widget.get_child_by_name("eosremoterelease").set_value("Release")
    camera.set_config(widget)


def _set_property(camera, widget, property_name, value):
    widget_type = widget.get_child_by_name(property_name).get_type()
    if widget_type == gp.GP_WIDGET_TOGGLE:
        value = int(value)
    widget.get_child_by_name(property_name).set_value(value)
    camera.set_config(widget)

# region Preview


def _start_preview(camera, widget):
    update_state("preview_capture", True)
    command_queue.put(camera_commands.CapturePreview())


def _capture_preview(camera):
    if not get_state("preview_capture"):
        return

    command_queue.put(camera_commands.CapturePreview())

    error, frame_file = gp.gp_camera_capture_preview(camera)
    if error >= GP_ERROR.OK:
        frame_bytes = bytes(frame_file.get_data_and_size())
        # Push to queue (drop oldest frame if queue gets backed up)
        if preview_frame_queue.full():
            try:
                preview_frame_queue.get_nowait()
            except queue.Empty:
                pass
        preview_frame_queue.put(frame_bytes)

        # time.sleep(1/30) # Limit framerate


def _stop_preview(camera, widget):
    update_state("preview_capture", False)
    # Also disable the viewfinder.
    # For some reason this only works if you first enable it, and then disable it
    widget.get_child_by_name("viewfinder").set_value(1)
    camera.set_config(widget)
    widget.get_child_by_name("viewfinder").set_value(0)
    camera.set_config(widget)
# endregion


def _manual_focus_drive(camera, widget, command: camera_commands.ManualFocus):
    widget.get_child_by_name("manualfocusdrive").set_value(command.focus.value)
    camera.set_config(widget)


if __name__ == "__main__":
    worker_thread = threading.Thread(target=camera_worker, daemon=True)
    worker_thread.start()
