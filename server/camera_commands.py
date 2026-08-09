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

    def __init__(self, focus: ManualFocus.FocusOption):
        self.focus = focus


class IntervallometerCommand():
    __match_args__ = ("start_stop", "interval_s")

    def __init__(self, start_stop, interval_s=None):
        self.start_stop = start_stop

        if start_stop and interval_s is None:
            raise ValueError(
                "If start_stop == True, then interval_s must not be None.")

        self.interval_s = interval_s

class PushBracketSettings():
    __match_args__ = ("iso", "aperture", "start_shutterspeed", "stop_shutterspeed")

    def __init__(self, iso, aperture, start_shutterspeed, stop_shutterspeed):
        assert iso in available_isos
        assert aperture in available_apertures
        assert start_shutterspeed in available_shutterspeeds
        assert stop_shutterspeed in available_shutterspeeds

        self.iso = iso
        self.aperture = aperture
        self.start_shutterspeed = start_shutterspeed
        self.stop_shutterspeed = stop_shutterspeed

class StartBracket():
    pass

class BracketCaptureExposure():
    def __init__(self, iso, aperture, shutterspeed_current, shutterspeed_stop):
        self.iso = iso
        self.aperture = aperture
        self.shutterspeed_current = shutterspeed_current
        self.shutterspeed_stop = shutterspeed_stop

class TurnOffUI():
    pass

class TurnOnUI():
    pass