from enum import IntEnum

class GP_ERROR(IntEnum):
    OK = 0
 
    # gphoto2-port-result.h
    ERROR = -1
    BAD_PARAMETERS = -2
    NO_MEMORY = -3
    LIBRARY = -4
    UNKNOWN_PORT = -5
    NOT_SUPPORTED = -6
    IO = -7
    FIXED_LIMIT_EXCEEDED = -8
    TIMEOUT = -10
 
    IO_SUPPORTED_SERIAL = -20
    IO_SUPPORTED_USB = -21
 
    IO_INIT = -31
    IO_READ = -34
    IO_WRITE = -35
    IO_UPDATE = -37
    IO_SERIAL_SPEED = -41
 
    IO_USB_CLEAR_HALT = -51
    IO_USB_FIND = -52
    IO_USB_CLAIM = -53
 
    IO_LOCK = -60
 
    HAL = -70
 
    # gphoto2-result.h
    CORRUPTED_DATA = -102
    FILE_EXISTS = -103
    MODEL_NOT_FOUND = -105
    DIRECTORY_NOT_FOUND = -107
    FILE_NOT_FOUND = -108
    DIRECTORY_EXISTS = -109
    CAMERA_BUSY = -110
    PATH_NOT_ABSOLUTE = -111
    CANCEL = -112
    CAMERA_ERROR = -113
    OS_FAILURE = -114
    NO_SPACE = -115