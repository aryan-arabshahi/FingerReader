from enum import Enum


class DataType(Enum):
    COMMAND = '0x01'
    ACK = '0x07'


class PayloadData(Enum):
    SCAN = '0x01'
    START_BIT = '0xEF01'
    SUCCESS = '0x00'
    BUFFER_IMAGE = '0x02'
    SEARCH_TEMPLATE = '0x04'
    TEMPLATE_INDEX = '0x1F'
    COUNT_TEMPLATES = '0x1D'
    CREATE_TEMPLATE = '0x05'
    STORE_TEMPLATE = '0x06'
    DELETE_TEMPLATE = '0x0C'
    ERASE_FINGERS = '0x0D'


class Error(Enum):
    NO_FINGER_FOUND = '0x02'
    READIMAGE = '0x03'
    MESSY_IMAGE = '0x06'
    FEW_FEATURE_POINTS = '0x07'
    INVALID_IMAGE = '0x15'
    NO_TEMPLATE_FOUND = '0x09'
    COMMUNICATION = '0x01'
    CHARACTERISTICS_MISMATCH = '0x0A'
    INVALID_POSITION = '0x0B'
    FLASH = '0x18'
    DELETE_TEMPLATE = '0x10'


class CharBuffer(Enum):
    READ = '0x01'
    WRITE = '0x02'


class SensorStatus(Enum):
    FREE = 'free'
    BUSY = 'busy'
