from available_camera_settings import available_apertures, available_isos, available_shutterspeeds
from enum import StrEnum

class SetPropertyCommand():
    __match_args__ = ("property_name", "value")

    def __init__(self, property_name, value):
        self.property_name = property_name
        self.value = value

#region Preview
class StartPreview():
    pass

class CapturePreview():
    pass

class StopPreview():
    pass
#endregion

class ManualFocus():
    class FocusOption(StrEnum):
        NEAR_1 = "Near 1"
        NEAR_2 = "Near 2"
        NEAR_3 = "Near 3"
        FAR_1 = "Far 1"
        FAR_2 = "Far 2"
        FAR_3 = "Far 3"

    def __init__(self, focus: FocusOption):
        self.focus = focus


class StartIntervallometer():
    def __init__(self, function_to_call, interval_s):
        self.function_to_call = function_to_call
        self.interval_s = interval_s


class CaptureBracket():
    def __init__(self, iso, aperture, shutterspeeds: list, capture_done_callback = None):
        self.iso = iso
        self.aperture = aperture
        self.shutterspeeds = shutterspeeds
        self.capture_done_callback = capture_done_callback

class LockUI():
    pass

class UnlockUI():
    pass

class Capture():
    pass

class FetchLastCapture():
    def __init__(self, callback):
        self.callback = callback