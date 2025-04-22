import base64
import os
import asyncio
import traceback
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Union
import logging
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from .const import CERT_NAME_PREFIX

_LOGGER = logging.getLogger(__name__)


class HeWeatherStorageType(Enum):
    LOAD = auto()
    LOAD_FILE = auto()
    SAVE = auto()
    SAVE_FILE = auto()
    DEL = auto()
    DEL_FILE = auto()
    CLEAR = auto()


class HeWeatherCert:
    _main_loop: asyncio.AbstractEventLoop
    _file_future: dict[str, tuple[HeWeatherStorageType, asyncio.Future]]

    _root_path: str
    _cert_path: str

    _openssl_ed25519_private_prefix: bytes
    _openssl_ed25519_public_prefix: bytes

    _cert_private_name: str
    _cert_public_name: str

    def __init__(
        self, root_path: str, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        self._main_loop = loop or asyncio.get_running_loop()
        self._file_future = {}

        self._root_path = os.path.abspath(root_path)
        self._cert_path = os.path.join(self._root_path, "certs")
        os.makedirs(self._cert_path, exist_ok=True)

        self._openssl_ed25519_private_prefix = bytes.fromhex(
            "302e020100300506032b657004220420"
        )
        self._openssl_ed25519_public_prefix = bytes.fromhex("302a300506032b6570032100")

        self._cert_private_name = CERT_NAME_PREFIX + "private.pem"
        self._cert_public_name = CERT_NAME_PREFIX + "public.pem"

        _LOGGER.debug("cert path, %s", self._cert_path)

    def __add_file_future(
        self, key: str, op_type: HeWeatherStorageType, fut: asyncio.Future
    ) -> None:
        def fut_done_callback(fut: asyncio.Future):
            del fut
            self._file_future.pop(key, None)

        fut.add_done_callback(fut_done_callback)
        self._file_future[key] = op_type, fut

    def __save(self, path: str, data: Union[str, None], cover: bool = True) -> bool:
        if data is None:
            _LOGGER.error("save error, save data is None")
            return False
        if os.path.exists(path):
            if not cover:
                _LOGGER.error("save error, file exists, cover is False")
                return False
            if not os.access(path, os.W_OK):
                _LOGGER.error("save error, file not writeable, %s", path)
                return False
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            w_bytes: bytes
            if isinstance(data, str):
                w_bytes = data.encode(encoding="utf-8")
            else:
                _LOGGER.error(
                    "save error, unsupported data type, %s", type(data).__name__
                )
                return False
            with open(path, "wb") as w_file:
                w_file.write(w_bytes)
            return True
        except (OSError, TypeError) as e:
            _LOGGER.error("save error, %s, %s", e, traceback.format_exc())
            return False

    async def __save_async(self, path: str, data: Union[str, None]) -> bool:
        if path in self._file_future:
            # Waiting for the last task to be completed
            fut = self._file_future[path][1]
            await fut
        fut = self._main_loop.run_in_executor(None, self.__save, path, data)
        if not fut.done():
            self.__add_file_future(path, HeWeatherStorageType.SAVE, fut)
        return await fut

    def gen_key(self) -> bool:
        prikey = ed25519.Ed25519PrivateKey.generate()
        pubkey = prikey.public_key()

        prikey_bytes = prikey.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pubkey_bytes = pubkey.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        prikey_b64 = base64.b64encode(
            self._openssl_ed25519_private_prefix + prikey_bytes
        ).decode()
        pubkey_b64 = base64.b64encode(
            self._openssl_ed25519_public_prefix + pubkey_bytes
        ).decode()

        try:
            self.__save(
                os.path.join(self._cert_path, self._cert_private_name),
                f"-----BEGIN PRIVATE KEY-----\n{prikey_b64}\n-----END PRIVATE KEY-----\n",
            )
            self.__save(
                os.path.join(self._cert_path, self._cert_public_name),
                f"-----BEGIN PUBLIC KEY-----\n{pubkey_b64}\n-----END PUBLIC KEY-----\n",
            )
            return True
        except Exception as e:
            _LOGGER.error("Failed to generate key: %s", e)
            self.del_key()
            return False

    async def gen_key_async(self) -> bool:
        prikey = ed25519.Ed25519PrivateKey.generate()
        pubkey = prikey.public_key()

        prikey_bytes = prikey.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pubkey_bytes = pubkey.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        prikey_b64 = base64.b64encode(
            self._openssl_ed25519_private_prefix + prikey_bytes
        ).decode()
        pubkey_b64 = base64.b64encode(
            self._openssl_ed25519_public_prefix + pubkey_bytes
        ).decode()

        try:
            await self.__save_async(
                os.path.join(self._cert_path, self._cert_private_name),
                f"-----BEGIN PRIVATE KEY-----\n{prikey_b64}\n-----END PRIVATE KEY-----\n",
            )
            await self.__save_async(
                os.path.join(self._cert_path, self._cert_public_name),
                f"-----BEGIN PUBLIC KEY-----\n{pubkey_b64}\n-----END PUBLIC KEY-----\n",
            )
            return True
        except Exception as e:
            _LOGGER.error("Failed to generate key: %s", e)
            self.del_key()
            return False

    def __load(self, path: str) -> Union[str, None]:
        if not os.path.exists(path):
            _LOGGER.debug("load error, file does not exist, %s", path)
            return None
        if not os.access(path, os.R_OK):
            _LOGGER.error("load error, file not readable, %s", path)
            return None
        try:
            with open(path, "rb") as r_file:
                r_bytes: bytes = r_file.read()
                if r_bytes is None:
                    _LOGGER.error("load error, empty file, %s", path)
                    return None

                return r_bytes.decode(encoding="utf-8")
        except (OSError, TypeError) as e:
            _LOGGER.error("load error, %s, %s", e, traceback.format_exc())
            return None

    async def __load_async(self, path: str) -> Union[str, None]:
        if path in self._file_future:
            # Waiting for the last task to be completed
            op_type, fut = self._file_future[path]
            if op_type == HeWeatherStorageType.LOAD:
                if not fut.done():
                    return await fut
            else:
                await fut
        fut = self._main_loop.run_in_executor(None, self.__load, path)
        if not fut.done():
            self.__add_file_future(path, HeWeatherStorageType.LOAD, fut)
        return await fut

    def get_pri_key(self) -> Union[str, None]:
        try:
            return self.__load(os.path.join(self._cert_path, self._cert_private_name))
        except Exception as e:
            _LOGGER.error("Failed to read private key: %s", e)
            return None

    async def get_pri_key_async(self) -> Union[str, None]:
        try:
            return await self.__load_async(
                os.path.join(self._cert_path, self._cert_private_name)
            )
        except Exception as e:
            _LOGGER.error("Failed to read private key: %s", e)
            return None

    def get_pub_key(self) -> Union[str, None]:
        try:
            return self.__load(os.path.join(self._cert_path, self._cert_public_name))
        except Exception as e:
            _LOGGER.error("Failed to read public key: %s", e)
            return None

    async def get_pub_key_async(self) -> Union[str, None]:
        try:
            return await self.__load_async(
                os.path.join(self._cert_path, self._cert_public_name)
            )
        except Exception as e:
            _LOGGER.error("Failed to read public key: %s", e)
            return None

    def get_jwt_token(self, payload: dict, headers: dict) -> str | None:
        private_key = self.get_pri_key()
        if private_key:
            return jwt.encode(payload, private_key, algorithm="EdDSA", headers=headers)
        else:
            _LOGGER.error("Failed to get private key")
            return None

    async def get_jwt_token_async(self, payload: dict, headers: dict) -> str | None:
        private_key = await self.get_pri_key_async()
        if private_key:
            return jwt.encode(payload, private_key, algorithm="EdDSA", headers=headers)
        else:
            _LOGGER.error("Failed to get private key")
            return None

    def get_jwt_token_heweather(
        self, sub: str, kid: str, iat: int, exp: int
    ) -> str | None:
        payload = {
            "iat": iat,
            "exp": exp,
            "sub": sub,
        }
        headers = {"kid": kid}
        return self.get_jwt_token(payload, headers)

    async def get_jwt_token_heweather_async(
        self, sub: str, kid: str, iat: int, exp: int
    ) -> str | None:
        payload = {
            "iat": iat,
            "exp": exp,
            "sub": sub,
        }
        headers = {"kid": kid}
        return await self.get_jwt_token_async(payload, headers)

    def __remove(self, path: str) -> bool:
        item = Path(path)
        if item.is_file() or item.is_symlink():
            item.unlink()
        return True

    async def __remove_async(self, path: str) -> bool:
        if path in self._file_future:
            # Waiting for the last task to be completed
            op_type, fut = self._file_future[path]
            if op_type == HeWeatherStorageType.DEL:
                if not fut.done():
                    return await fut
            else:
                await fut
        fut = self._main_loop.run_in_executor(None, self.__remove, path)
        if not fut.done():
            self.__add_file_future(path, HeWeatherStorageType.DEL, fut)
        return await fut

    def del_key(self) -> None:
        self.__remove(os.path.join(self._cert_path, self._cert_private_name))
        self.__remove(os.path.join(self._cert_path, self._cert_public_name))

    async def del_key_async(self) -> None:
        await self.__remove_async(
            os.path.join(self._cert_path, self._cert_private_name)
        )
        await self.__remove_async(os.path.join(self._cert_path, self._cert_public_name))
