import struct
from enum import Enum
from typing import Tuple, List, Union, Optional
from serial import Serial, EIGHTBITS
from logging import StreamHandler, Formatter, DEBUG, getLogger
from FingerReader.exceptions import InvalidPacket, CorruptedPacket, CommunicationError, NoFingerFound, ReadImageError, \
    MessyImageError, FewFeaturePointsError, InvalidImageError, UnknownError, NoTemplateFound, ReadInputError, \
    FingerNotFound, FingerExists, CharacteristicsMismatchError, InvalidPosition, FlashError, DeleteTemplateError, \
    NoAvailablePositionFound, SensorIsBusy, KillSignal
from .enums import DataType, PayloadData, CharBuffer, Error, SensorStatus
from traceback import format_exc
from time import time
from .global_manager import Global


g = Global()


class FingerReader:

    def __init__(self, port: str = '/dev/ttyUSB', baud_rate: int = 57600, address: int = 0xFFFFFFFF,
                 serial_timeout: int = 2, debug: bool = False) -> None:
        """Initiate the class

        Keyword Arguments:
            port {str} -- (default: {'/dev/ttyUSB'})
            baud_rate {int} -- (default: {57600})
            address {int} -- (default: {0xFFFFFFFF})
            serial_timeout {int} -- The serial communication timeout (default: {2})
            debug {bool} --  (default: {False})
        """
        if debug:
            self._setup_logger()
        self._logger = getLogger(__name__)
        self._port = port
        self._baud_rate = baud_rate
        self._serial_timeout = serial_timeout
        self._address = address
        self._serial = self._create_serial_connection(port=port, baud_rate=baud_rate, timeout=serial_timeout)

    def _create_serial_connection(self, port: str, baud_rate: int, timeout: int) -> Union[Serial, None]:
        """Create and open the serial connection

        Arguments:
            port {str}
            baud_rate {int}
            timeout {int} -- The serial communication timeout (default: {2})
        
        Returns:
            Union[Serial, None]
        """
        try:
            self._serial = Serial(port=port, baudrate=baud_rate, bytesize=EIGHTBITS, timeout=timeout)
            self._open_serial_connection()
            return self._serial

        except Exception as e:
            self._logger.error(f'Can not open the serial connection - {e}')

        return None

    @staticmethod
    def _setup_logger():
        handler = StreamHandler()
        formatter = Formatter("%(levelname)s:%(name)s:%(message)s")
        handler.setFormatter(formatter)
        _logger = getLogger('FingerReader')
        _logger.setLevel(DEBUG)
        _logger.addHandler(handler)

    def _open_serial_connection(self) -> None:
        self._logger.debug('Opening the serial connection')
        if self._serial.isOpen():
            self._serial.close()

        self._serial.open()

    def _close_serial_connection(self) -> None:
        if self._serial and self._serial.isOpen():
            self._serial.close()

    def __del__(self):
        self._close_serial_connection()

    def _send_data(self, data_type: DataType, payload: Tuple) -> None:
        """Send data to the FPS

        Arguments:
            data_type {DataType}
            payload {Tuple]}
        """
        self._logger.debug(f'Sending data to the FPS - data_type: {data_type.name} - payload: {payload}')

        if self._serial is None:
            self._create_serial_connection(port=self._port, baud_rate=self._baud_rate, timeout=self._serial_timeout)

        self._serial.write(self._pack_bytes(self._shift_right(self._enum_to_hexadecimal(PayloadData.START_BIT), 8)))
        self._serial.write(self._pack_bytes(self._shift_right(self._enum_to_hexadecimal(PayloadData.START_BIT), 0)))

        self._serial.write(self._pack_bytes(self._shift_right(self._address, 24)))
        self._serial.write(self._pack_bytes(self._shift_right(self._address, 16)))
        self._serial.write(self._pack_bytes(self._shift_right(self._address, 8)))
        self._serial.write(self._pack_bytes(self._shift_right(self._address, 0)))

        self._serial.write(self._pack_bytes(self._enum_to_hexadecimal(data_type)))

        # The packet length = payload (n bytes) + checksum (2 bytes)
        packet_length = len(payload) + 2

        self._serial.write(self._pack_bytes(self._shift_right(packet_length, 8)))
        self._serial.write(self._pack_bytes(self._shift_right(packet_length, 0)))

        # The packet checksum = packet type (1 byte) + packet length (2 bytes) + payload (n bytes)
        packet_checksum = self._enum_to_hexadecimal(data_type) + self._shift_right(packet_length, 8) + \
                          self._shift_right(packet_length, 0)

        for i in range(0, len(payload)):
            self._serial.write(self._pack_bytes(payload[i]))
            packet_checksum += payload[i]

        self._serial.write(self._pack_bytes(self._shift_right(packet_checksum, 8)))
        self._serial.write(self._pack_bytes(self._shift_right(packet_checksum, 0)))

    @staticmethod
    def _enum_to_hexadecimal(data: Enum) -> int:
        """Convert an enum value to hexadecimal

        Arguments:
            data {Enum}
        
        Returns:
            int
        """
        return int(data.value, 16)

    @staticmethod
    def _pack_bytes(data: int) -> bytes:
        """Convert data to bytes

        Arguments:
            data {int}

        Returns:
            bytes
        """
        return struct.pack('B', data)

    @staticmethod
    def _unpack_bytes(data: bytes) -> bytes:
        """Unpack the received data

        Arguments:
            data {str}

        Returns:
            bytes
        """
        return struct.unpack('B', data)[0]

    @staticmethod
    def _shift_right(x: int, y: int) -> int:
        """Shift to right by y bits

        Arguments:
            x {int}
            y {int}

        Returns:
            int
        """
        return x >> y & 0xFF

    @staticmethod
    def _shift_left(x: Union[bytes, int], y: Union[bytes, int]) -> int:
        """Shift to left by y bits

        Arguments:
            x {int}
            y {int}

        Returns:
            int
        """
        return x << y

    @staticmethod
    def _get_bit_by_pos(data: Optional[bytes], pos: int) -> int:
        """Gets the bit by position

        Arguments:
            data {Optional[bytes]}
            pos {int}
        
        Returns:
            int
        """
        return int((data and (1 << pos)) > 0)

    def _scan(self) -> None:
        """Scan the finger

        Raises:
            InvalidPacket
            CommunicationError
            NoFingerError
            ReadImageError
            UnknownError
        """
        self._logger.debug('Scanning the finger')

        self._send_data(
            data_type=DataType.COMMAND,
            payload=(
                self._enum_to_hexadecimal(PayloadData.SCAN),
            )
        )

        data_type, payload = self._read_data()

        if data_type != self._enum_to_hexadecimal(DataType.ACK):
            self._logger.error('The received packet is not an ACK packet')
            raise InvalidPacket

        elif payload[0] == self._enum_to_hexadecimal(PayloadData.SUCCESS):
            self._logger.debug('The finger has been scanned')
            return

        elif payload[0] == self._enum_to_hexadecimal(Error.NO_FINGER_FOUND):
            self._logger.debug('No finger found.')
            raise NoFingerFound

        elif payload[0] == self._enum_to_hexadecimal(Error.COMMUNICATION):
            self._logger.error('Communication error.')
            raise CommunicationError

        elif payload[0] == self._enum_to_hexadecimal(Error.READIMAGE):
            self._logger.error('Read image error')
            raise ReadImageError

        else:
            self._logger.error('Unknown error')
            raise UnknownError

    def _check_packet_header(self, received_data: List[bytes]) -> None:
        """Check the packet header

        Arguments:
            received_data {List[bytes]}

        Raises:
            InvalidPacket
        """
        self._logger.debug('Checking the packet header')
        if received_data[0] != self._shift_right(self._enum_to_hexadecimal(PayloadData.START_BIT), 8) or \
                received_data[1] != self._shift_right(self._enum_to_hexadecimal(PayloadData.START_BIT), 0):
            raise InvalidPacket

    def _read_data(self) -> Tuple[Optional[bytes], List[Optional[bytes]]]:
        """Read data from the FPS

        Returns:
            Tuple[Union[bytes, int], Union[bytes, int]]
        
        Raises:
            CorruptedPacket
        """

        self._logger.debug('Reading the FPS data from the serial connection')

        received_data = []

        _counter = 0
        while True:

            received_fragment = self._serial.read()

            received_data.append(
                self._unpack_bytes(received_fragment) if (len(received_fragment) != 0) else received_fragment
            )

            _counter += 1

            if _counter >= 12:

                # Checking the packet header
                self._check_packet_header(received_data)

                packet_payload_length = self._shift_left(received_data[7], 8) or self._shift_left(received_data[8], 0)

                if _counter < packet_payload_length + 9:
                    continue

                self._logger.debug('The packet completely received')

                data_type = received_data[6]

                packet_checksum = data_type + received_data[7] + received_data[8]

                payload = []

                for i in range(9, 9 + packet_payload_length - 2):
                    payload.append(received_data[i])
                    packet_checksum += received_data[i]

                received_checksum = self._shift_left(received_data[_counter - 2], 8) or \
                                    self._shift_left(received_data[_counter - 1], 0)

                if received_checksum != packet_checksum:
                    raise CorruptedPacket

                return data_type, payload

    def read(self, timeout: int = None) -> None:
        """Read the FPS to detect the finger

        Keyword Arguments:
            timeout {int} -- The reading state timeout (default: {None})

        Raises:
            NoFingerFound -- Whenever reach the timeout
            KillSignal -- Kill the reading process using the specified flag
            ReadInputError
        """
        self.set_status(SensorStatus.BUSY)
        self._logger.debug('Reading the FPS to detect the finger')
        start_time = self.get_current_timestamp()
        while True:
            try:
                self._scan()
                break

            except NoFingerFound as e:
                if g.signals.get('kill_read_finger'):
                    # Killing the read process
                    g.signals['kill_read_finger'] = None
                    self.set_status(SensorStatus.FREE)
                    # Getting the count of the stored fingers to change the sensor mode
                    self.count_fingers()
                    raise KillSignal

                elif timeout and (self.get_current_timestamp() - start_time) >= timeout:
                    self.set_status(SensorStatus.FREE)
                    # Getting the count of the stored fingers to change the sensor mode
                    self.count_fingers()
                    raise NoFingerFound

            except Exception as e:
                self._logger.error(f'Could not read the input - {e} - {format_exc()}')
                self.set_status(SensorStatus.FREE)
                raise ReadInputError

        self.set_status(SensorStatus.FREE)

    @staticmethod
    def set_status(status: SensorStatus) -> None:
        """Set the status of the sensor
        Arguments:
            status {SensorStatus}
        """
        g.status = status

    @staticmethod
    def get_current_timestamp() -> int:
        """Getting the current unix timestamp
        
        Returns:
            int
        """
        return int(time())

    def _buffer_image(self, char_buffer: CharBuffer) -> None:
        """Buffer the scanned image

        Arguments:
            char_buffer {CharBuffer}

        Raises:
            InvalidPacket
            CommunicationError
            MessyImageError
            FewFeaturePointsError
            InvalidImageError
            UnknownError
        """
        self._logger.debug('Buffering the scanned image')

        self._send_data(
            data_type=DataType.COMMAND,
            payload=(
                self._enum_to_hexadecimal(PayloadData.BUFFER_IMAGE),
                self._enum_to_hexadecimal(char_buffer)
            )
        )

        data_type, payload = self._read_data()

        if data_type != self._enum_to_hexadecimal(DataType.ACK):
            self._logger.error('The received packet is not an ACK packet')
            raise InvalidPacket

        elif payload[0] == self._enum_to_hexadecimal(PayloadData.SUCCESS):
            self._logger.debug('The scanned image has been buffered')
            return

        elif payload[0] == self._enum_to_hexadecimal(Error.COMMUNICATION):
            self._logger.error('Communication error.')
            raise CommunicationError

        elif payload[0] == self._enum_to_hexadecimal(Error.MESSY_IMAGE):
            self._logger.error('Messy image error')
            raise MessyImageError

        elif payload[0] == self._enum_to_hexadecimal(Error.FEW_FEATURE_POINTS):
            self._logger.error('Few feature points error')
            raise FewFeaturePointsError

        elif payload[0] == self._enum_to_hexadecimal(Error.INVALID_IMAGE):
            self._logger.error('Invalid image error')
            raise InvalidImageError

        else:
            self._logger.error('Unknown error')
            raise UnknownError

    def _search_template(self, char_buffer: CharBuffer = CharBuffer.READ) -> Tuple[int, int]:
        """Search the buffered image to fine the stored template

        Keyword Arguments:
            char_buffer {CharBuffer} -- (default: {CharBuffer.READ})

        Returns:
            Tuple[int, int] -- Template position (Finger ID), Accuracy score
        """
        self._logger.debug('Searching the buffered image to fine the stored template')

        start_pos = 0x0000
        total_templates = 0x00A3

        self._send_data(
            data_type=DataType.COMMAND,
            payload=(
                self._enum_to_hexadecimal(PayloadData.SEARCH_TEMPLATE),
                self._enum_to_hexadecimal(char_buffer),
                self._shift_right(start_pos, 8),
                self._shift_right(start_pos, 0),
                self._shift_right(total_templates, 8),
                self._shift_right(total_templates, 0)
            )
        )

        data_type, payload = self._read_data()

        if data_type != self._enum_to_hexadecimal(DataType.ACK):
            self._logger.error('The received packet is not an ACK packet')
            raise InvalidPacket

        elif payload[0] == self._enum_to_hexadecimal(PayloadData.SUCCESS):
            self._logger.debug('The template has been found')

            template_pos = self._shift_left(payload[1], 8) or self._shift_left(payload[2], 0)

            score = self._shift_left(payload[3], 8) or self._shift_left(payload[4], 0)

            self._logger.debug(f'Template position: {template_pos} - Score: {score}')

            return template_pos, score

        elif payload[0] == self._enum_to_hexadecimal(Error.NO_TEMPLATE_FOUND):
            self._logger.error('No template found.')
            raise NoTemplateFound

        elif payload[0] == self._enum_to_hexadecimal(Error.COMMUNICATION):
            self._logger.error('Communication error.')
            raise CommunicationError

        else:
            self._logger.error('Unknown error')
            raise UnknownError

    def check_finger(self, timeout: int = None) -> Tuple[int, int]:
        """Check the finger

        Keyword Arguments:
            timeout {int} -- The reading state timeout (default: {None})

        Returns:
            Tuple[int, int] -- Template position (Finger ID), Accuracy score

        Raises:
            FingerNotFound
            NoFingerFound
        """
        try:
            self._logger.debug(f'Checking the finger')
            self.read(timeout=timeout)
            self._buffer_image(CharBuffer.READ)
            return self._search_template()

        except NoFingerFound as e:
            self._logger.debug('No finger found on the sensor')
            raise NoFingerFound

        except NoTemplateFound as e:
            self._logger.debug('Finger not found')
            raise FingerNotFound

    def count_fingers(self) -> int:
        """Count the stored fingers

        Returns:
            int

        Raises:
            InvalidPacket
            CommunicationError
            UnknownError
        """
        self._logger.debug('Counting the stored fingers')
        self._send_data(
            data_type=DataType.COMMAND,
            payload=(
                self._enum_to_hexadecimal(PayloadData.COUNT_TEMPLATES),
            )
        )

        data_type, payload = self._read_data()

        if data_type != self._enum_to_hexadecimal(DataType.ACK):
            self._logger.error('The received packet is not an ACK packet')
            raise InvalidPacket

        elif payload[0] == self._enum_to_hexadecimal(PayloadData.SUCCESS):

            return self._shift_left(payload[1], 8) or self._shift_left(payload[2], 0)

        elif payload[0] == self._enum_to_hexadecimal(Error.COMMUNICATION):
            self._logger.error('Communication error.')
            raise CommunicationError

        else:
            self._logger.error('Unknown error')
            raise UnknownError

    def _create_template(self) -> None:
        """Create a new template to store

        Raises:
            InvalidPacket
            CommunicationError
            CharacteristicsMismatchError
            UnknownError
        """
        self._send_data(
            data_type=DataType.COMMAND,
            payload=(
                self._enum_to_hexadecimal(PayloadData.CREATE_TEMPLATE),
            )
        )

        data_type, payload = self._read_data()

        if data_type != self._enum_to_hexadecimal(DataType.ACK):
            self._logger.error('The received packet is not an ACK packet')
            raise InvalidPacket

        elif payload[0] == self._enum_to_hexadecimal(PayloadData.SUCCESS):
            self._logger.debug('The template has been created successfully')
            return

        elif payload[0] == self._enum_to_hexadecimal(Error.COMMUNICATION):
            self._logger.error('Communication error.')
            raise CommunicationError

        elif payload[0] == self._enum_to_hexadecimal(Error.CHARACTERISTICS_MISMATCH):
            self._logger.error('Characteristics mismatch.')
            raise CharacteristicsMismatchError

        else:
            self._logger.error('Unknown error')
            raise UnknownError

    def register(self, position: int = None, timeout: int = None) -> int:
        """Register a new finger

        Keyword Arguments:
            position {int} -- The finger position to store (Finger ID) (default: {None})
            timeout {int} -- The reading state timeout (default: {None})

        Returns:
            int -- The stored position (Finger ID)

        Raises:
            FingerExists
            NoFingerFound
            NoAvailablePositionFound
            SensorIsBusy
        """
        self._logger.debug(f'Storing the new finger - position: {position} - timeout: {timeout}')

        if g.status != SensorStatus.FREE:
            self._logger.debug('The sensor is busy')
            raise SensorIsBusy

        try:
            self.check_finger(timeout=timeout)
            raise FingerExists

        except NoFingerFound as e:
            self._logger.debug('No finger found on the sensor')
            raise NoFingerFound

        except FingerNotFound as e:
            self._logger.debug('The new finger does not exist. Going to store it.')

        return self._store_finger(position=position)

    def _store_finger(self, position: int = None) -> int:
        """Store the new finger

        Keyword Arguments:
            position {int} -- The finger position to store (Finger ID) (default: {None})

        Returns:
            int -- The stored position (Finger ID)

        Raises:
            NoAvailablePositionFound
            Exception
        """
        try:
            self._logger.debug(f'Storing the new finger - position: {position}')
            self.read()
            self._buffer_image(CharBuffer.WRITE)

            self._create_template()

            available_position = position if position is not None else self.get_available_position()

            self._logger.debug(f'Storing the template at: {available_position}')

            return self._store_template(position=available_position)

        except NoAvailablePositionFound as e:
            self._logger.debug(f'No available position found')

        except Exception as e:
            self._logger.error(f'Could not store the new finger - {e} - {format_exc()}')
            raise e

    def _store_template(self, position: int, char_buffer: CharBuffer = CharBuffer.WRITE) -> int:
        """Store the template from the buffer

        Arguments:
            position {int}

        Keyword Arguments:
            char_buffer {CharBuffer} -- (default: {CharBuffer.WRITE})

        Returns:
            int -- The stored position
        """
        self._logger.debug(f'Storing the new finger at: {position}')

        self._send_data(
            data_type=DataType.COMMAND,
            payload=(
                self._enum_to_hexadecimal(PayloadData.STORE_TEMPLATE),
                self._enum_to_hexadecimal(char_buffer),
                self._shift_right(position, 8),
                self._shift_right(position, 0)
            )
        )

        data_type, payload = self._read_data()

        if data_type != self._enum_to_hexadecimal(DataType.ACK):
            self._logger.error('The received packet is not an ACK packet')
            raise InvalidPacket

        elif payload[0] == self._enum_to_hexadecimal(PayloadData.SUCCESS):
            self._logger.debug(f'The template has been stored successfully at: {position}')
            return position

        elif payload[0] == self._enum_to_hexadecimal(Error.COMMUNICATION):
            self._logger.error('Communication error.')
            raise CommunicationError

        elif payload[0] == self._enum_to_hexadecimal(Error.INVALID_POSITION):
            self._logger.error('Invalid position.')
            raise InvalidPosition

        elif payload[0] == self._enum_to_hexadecimal(Error.FLASH):
            self._logger.error('Flash error.')
            raise FlashError

        else:
            self._logger.error('Unknown error')
            raise UnknownError

    def delete(self, position: int) -> None:
        """Delete the specified finger

        Arguments:
            position {int} -- The template position (Finger ID)
        """
        self._logger.debug(f'Deleting the specified finger - position: {position}')
        self._delete_template(position=position)

    def _delete_template(self, position: int) -> None:
        """Delete the template at the specified position

        Arguments:
            position {int} -- The template position (Finger ID)
        """
        self._logger.debug(f'Deleting the specified template - position: {position}')

        templates_to_delete = 0x0001

        self._send_data(
            data_type=DataType.COMMAND,
            payload=(
                self._enum_to_hexadecimal(PayloadData.DELETE_TEMPLATE),
                self._shift_right(position, 8),
                self._shift_right(position, 0),
                self._shift_right(templates_to_delete, 8),
                self._shift_right(templates_to_delete, 0)
            )
        )

        data_type, payload = self._read_data()

        if data_type != self._enum_to_hexadecimal(DataType.ACK):
            self._logger.error('The received packet is not an ACK packet')
            raise InvalidPacket

        elif payload[0] == self._enum_to_hexadecimal(PayloadData.SUCCESS):
            self._logger.debug('The template has been deleted')
            return

        elif payload[0] == self._enum_to_hexadecimal(Error.COMMUNICATION):
            self._logger.error('Communication error.')
            raise CommunicationError

        elif payload[0] == self._enum_to_hexadecimal(Error.DELETE_TEMPLATE):
            self._logger.error('Delete template error')
            raise DeleteTemplateError

        else:
            self._logger.error('Unknown error')
            raise UnknownError

    def get_available_position(self) -> int:
        """Get the available position to store the template

        Returns:
            int
        """
        self._logger.debug('Getting the available position to store the template')

        # TODO: Find the available position to store the new template

        return self.count_fingers()

    def erase_fingers(self) -> None:
        """Erase fingers

        Raises:
            InvalidPacket
            CommunicationError
            UnknownError
        """
        self._logger.debug('Erasing fingers')

        self._send_data(
            data_type=DataType.COMMAND,
            payload=(
                self._enum_to_hexadecimal(PayloadData.ERASE_FINGERS),
            )
        )

        data_type, payload = self._read_data()

        if data_type != self._enum_to_hexadecimal(DataType.ACK):
            self._logger.error('The received packet is not an ACK packet')
            raise InvalidPacket

        elif payload[0] == self._enum_to_hexadecimal(PayloadData.SUCCESS):
            self._logger.debug('The fingers have been deleted')
            return

        elif payload[0] == self._enum_to_hexadecimal(Error.COMMUNICATION):
            self._logger.error('Communication error.')
            raise CommunicationError

        else:
            self._logger.error('Unknown error')
            raise UnknownError
