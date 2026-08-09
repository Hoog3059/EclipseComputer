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


# class CameraCommand(IntEnum):
#     STOP_VIEWFINDER = 10
#     START_VIEWFINDER = 11

#     STOP_PREVIEW = 12
#     CAPTURE_PREVIEW = 13
#     CAPTURE_SINGLE_HQ_PREVIEW = 14
#     START_PREVIEW = 15

#     TURN_OFF_UI = 16
#     TURN_ON_UI = 17

#     CAPTURE = 18

#     FOCUS_NEAR_1 = 21
#     FOCUS_NEAR_2 = 22
#     FOCUS_NEAR_3 = 23
#     FOCUS_FAR_1 = 24
#     FOCUS_FAR_2 = 25
#     FOCUS_FAR_3 = 26

#     BRACKET_NEXT_EXPOSURE = 30

#     START_TOTALITY_IMAGE_BURST = 99
#     STOP_TOTALITY_IMAGE_BURST = 98


camera = None


def close_camera_connection():
    if camera is not None:
        camera.exit()


atexit.register(close_camera_connection)


command_queue = queue.Queue(maxsize=10)
preview_frame_queue = queue.Queue(maxsize=10)

camera_state_lock = threading.Lock()
camera_state = {
    # Camera info
    "connected": False,
    "uiLocked": False,

    "batterylevel": "0%",

    "iso": "100",
    "shutterspeed": "1/1000",
    "aperture": "6.3",

    # Preview info
    "preview_capture": False,

    # Bracket
    "bracket_running": False,

    "bracket_iso": "100",
    "bracket_aperture": "6.3",
    "bracket_shutterspeed_start": "1/1000",
    "bracket_shutterspeed_stop": "1/10",

    # Intervallometer
    "intervallometer_running": False,
    "intervallometer_interval": 10,
}

current_bracket = None
current_bracket_exposure = None

intervallometer_last_capture = time.time()
intervallometer_interval = 0


def update_state(name, value):
    with camera_state_lock:
        camera_state[name] = value


def get_state(name=None, full=False):
    with camera_state_lock:
        if full:
            return camera_state.copy()
        return camera_state.copy().get(name)


def camera_stop():
    try:
        while True:
            command_queue.get_nowait()
    except queue.Empty as e:
        pass


def camera_worker():
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
            elif error != GP_ERROR.MODEL_NOT_FOUND:
                # Unhandled error
                raise gp.GPhoto2Error(error)
            else:
                # No camera found
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

        # --- Handle commands for camera in queue ---
        if command_queue.empty():
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
            case camera_commands.PushBracketSettings():
                update_state("bracket_iso", command.iso)
                update_state("bracket_aperture", command.aperture)
                update_state("bracket_shutterspeed_start", command.start_shutterspeed)
                update_state("bracket_shutterspeed_stop", command.stop_shutterspeed)                
            case camera_commands.StartBracket():
                next_exposure = camera_commands.BracketCaptureExposure(
                    get_state("bracket_iso"),
                    get_state("bracket_aperture"),
                    get_state("bracket_shutterspeed_start"),
                    get_state("bracket_shutterspeed_stop")
                )
                update_state("bracket_running", True)
                command_queue.put(next_exposure)
            case camera_commands.BracketCaptureExposure():
                _bracket_capture_exposure(camera, widget, command)

            # case CameraCommand.CAPTURE:
            #     _capture(camera, widget)
            # case CameraCommand.CAPTURE_SINGLE_HQ_PREVIEW:
            #     _capture_hq_preview(camera, widget)
            # case CameraCommand.START_TOTALITY_IMAGE_BURST:
            #     _totality_image_burst(camera, widget)
            # case IntervallometerCommand(start_stop, interval_s):
            #     _start_stop_intervallometer(start_stop, interval_s)

            # --- Brackets ---
            # case CaptureBracketCommand(iso, aperture, start_shutterspeed, stop_shutterspeed):
            #     pass
            # case CameraCommand.BRACKET_NEXT_EXPOSURE:
            #     pass

            # --- Fallthrough ---
            case _:
                raise ValueError(f"Command {command} is not a valid command.")

        # --- Intervallometer ---
        if get_state("intervallometer_active"):
            current_time = time.time()
            if current_time > intervallometer_last_capture + intervallometer_interval:
                intervallometer_last_capture = current_time
                _capture(camera, widget)
                # _wait_for_idle(camera)
                _wait_for_capture_finish(camera)


def _bracket_capture_exposure(camera, widget, command: camera_commands.BracketCaptureExposure):
    if not get_state("bracket_running"):
        return

    _set_property(camera, widget, "iso", command.iso)
    _set_property(camera, widget, "aperture", command.aperture)
    _set_property(camera, widget, "shutterspeed", command.shutterspeed_current)
    _capture(camera, widget)
    _wait_for_capture_finish(camera, total_timeout_ms=int(
        eval(command.shutterspeed_current)*1000 + 1000))

    if command.shutterspeed_current == command.shutterspeed_stop:
        update_state("bracket_running", False)
        return

    if available_shutterspeeds.index(command.shutterspeed_stop) < available_shutterspeeds.index(command.shutterspeed_current):
        index_step = -1
    else:
        index_step = 1

    next_shutterspeed = available_shutterspeeds[available_shutterspeeds.index(command.shutterspeed_current) + index_step]

    command.shutterspeed_current = next_shutterspeed
    command_queue.put(command)


def _start_stop_intervallometer(start_stop, interval_s):
    if start_stop:
        intervallometer_interval = interval_s
        intervallometer_last_capture = 0
        update_state("intervallometer_active", True)
    else:
        update_state("intervallometer_active", False)


def _totality_image_burst(camera, widget):
    widget.get_child_by_name("capturetarget").set_value("Memory card")
    widget.get_child_by_name("imageformat").set_value("RAW + L")
    widget.get_child_by_name("imageformatsd").set_value("RAW + L")
    camera.set_config(widget)

    widget.get_child_by_name("iso").set_value("200")
    widget.get_child_by_name("aperture").set_value("6.3")
    camera.set_config(widget)

    exposures = [
        "1/4000",
        "1/2000",
        "1/1000",
        "1/500",
        "1/250",
        "1/125",
        "1/60",
        "1/30",
        "1/15",
        "1/8",
        "1/4",
        "0.5",
        "1",
        "2"
    ]

    for exposure in exposures:
        widget.get_child_by_name("shutterspeed").set_value(exposure)
        camera.set_config(widget)
        _capture(camera, widget)
        _wait_for_capture_finish(
            camera=camera,
            total_timeout_ms=int(eval(exposure)*1000 + 1000)
        )
        # _wait_for_idle(camera, int(eval(exposure)*1000 + 1000))


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


def _wait_for_idle(camera, timeout=1000):
    event_type = None
    while event_type != gp.GP_EVENT_TIMEOUT:
        error, event_type, event_data = gp.gp_camera_wait_for_event(
            camera, timeout)
        time.sleep(0.01)


def _capture_hq_preview(camera, widget):
    old_capture_target = widget.get_child_by_name("capturetarget").get_value()
    widget.get_child_by_name("capturetarget").set_value("Internal RAM")
    camera.set_config(widget)
    _capture(camera, widget)
    camera.wait_for_event(1000)
    print(camera.folder_list_files("/"))
    file = camera.file_get("/", "capt0000.jpg", gp.GP_FILE_TYPE_NORMAL)
    camera.file_delete("/", "capt0000.jpg")
    raise NotImplementedError("Needs to be finished")


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
