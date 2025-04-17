import os
import asyncio
import binascii
import json
import shutil
import time
import traceback
import hashlib
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional, Union
import logging

_LOGGER = logging.getLogger(__name__)

class HeWeatherStorage:
    def __init__(
        self, root_path: str,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """Initialize with a root path."""
        self._main_loop = loop or asyncio.get_running_loop()
        self._file_future = {}

        self._root_path = os.path.abspath(root_path)
        os.makedirs(self._root_path, exist_ok=True)

        _LOGGER.debug('root path, %s', self._root_path)

class HeWeatherCert:
    def __init__(self, root_path: str) -> None:
        self._root_path = os.path.abspath(root_path)
        self._cert_path = os.path.join(self._root_path, 'certs')
        os.makedirs(self._cert_path, exist_ok=True)

        _LOGGER.debug('cert path, %s', self._cert_path)

    def get_cert(self, cert_name: str) -> Optional[bytes]:
        cert_file = os.path.join(self._cert_path, cert_name)
        if not os.path.exists(cert_file):
            return None
        with open(cert_file, 'rb') as f:
            return f.read()