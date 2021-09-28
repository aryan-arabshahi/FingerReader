import os
import json
from typing import List, Any
from .enums import SensorStatus


class Global:

    def __init__(self):
        """The global manager

        Keyword Arguments:
            config_path {str} -- the module config file (default: {None})
            global_config {str} -- the global config file (default: {None})
        """
        self._data = {
            'status': SensorStatus.FREE,
            'signals': {},
        }

    def all(self) -> dict:
        """Get All data

        Returns:
            dict
        """
        return self._data

    def get(self, target_key: str, default_value: Any = None) -> Any:
        """Get the specific config key

        Arguments:
            target_key {str}
        
        Keyword Arguments:
            default_value {Any} -- (default: {None})
        
        Returns:
            Any
        """
        _keys = target_key.split('.')
        iteration = len(_keys)
        if iteration > 1:
            result = None
            counter = 1
            for key_holder in _keys:
                if counter == 1:
                    result = self._data.get(key_holder, {})
                elif counter < iteration:
                    result = result.get(key_holder, {})
                else:
                    result = result.get(key_holder, default_value)
                counter += 1
            return result
        else:
            return self._data.get(_keys[0], default_value)

    def __getattr__(self, target_key):
        return self.get(target_key)
