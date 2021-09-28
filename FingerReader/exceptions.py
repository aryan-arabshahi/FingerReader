

class InvalidPacket(Exception):
    pass


class CorruptedPacket(Exception):
    pass


class CommunicationError(Exception):
    pass


class NoFingerFound(Exception):
    pass


class ReadImageError(Exception):
    pass


class MessyImageError(Exception):
    pass


class FewFeaturePointsError(Exception):
    pass


class InvalidImageError(Exception):
    pass


class UnknownError(Exception):
    pass


class NoTemplateFound(Exception):
    pass


class FingerNotFound(Exception):
    pass


class ReadInputError(Exception):
    pass


class FingerExists(Exception):
    pass


class CharacteristicsMismatchError(Exception):
    pass


class InvalidPosition(Exception):
    pass


class FlashError(Exception):
    pass


class DeleteTemplateError(Exception):
    pass


class NoAvailablePositionFound(Exception):
    pass


class SensorIsBusy(Exception):
    pass


class KillSignal(Exception):
    pass
