import logging

import asyncio
from typing import Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

from .heweather.const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_AUTH_METHOD,
    CONF_LONGITUDE,
    CONF_LATITUDE,
    CONF_HOST,
    CONF_KEY,
    CONF_STORAGE_PATH,
    CONF_JWT_SUB,
    CONF_JWT_KID,
    CONF_DISASTERLEVEL,
    CONF_DISASTERMSG,
    CONF_SENSOR_LIST,
    DEFAULT_HOST,
    DEFAULT_AUTH_METHOD,
    AUTH_METHOD,
    DEFAULT_DISASTER_LEVEL_CONF,
    DISASTER_LEVEL_CONF,
    DEFAULT_DISASTER_MSG,
    DISASTER_MSG
)

from .heweather.heweather_cert import HeWeatherCert

_LOGGER = logging.getLogger(__name__)

async def migrate_entities_for_location_change(hass, config_entry, old_longitude=None, old_latitude=None, new_longitude=None, new_latitude=None):
    """迁移实体到新的经纬度，保持实体ID和配置"""
    if old_longitude is None or old_latitude is None or new_longitude is None or new_latitude is None:
        return
    
    entity_registry = er.async_get(hass)
    
    # 获取所有与此集成相关的旧实体
    entities_to_migrate = []
    old_unique_id_suffix = f"_{old_longitude}_{old_latitude}"
    new_unique_id_suffix = f"_{new_longitude}_{new_latitude}"
    
    for entity_id, entity in entity_registry.entities.items():
        if entity.config_entry_id == config_entry.entry_id and entity.platform == DOMAIN:
            if entity.unique_id and old_unique_id_suffix in entity.unique_id:
                entities_to_migrate.append((entity_id, entity))
    
    # 迁移实体：更新unique_id而不删除实体
    migrated_count = 0
    for entity_id, entity in entities_to_migrate:
        # 生成新的unique_id
        new_unique_id = entity.unique_id.replace(old_unique_id_suffix, new_unique_id_suffix)
        
        try:
            # 更新实体的unique_id
            entity_registry.async_update_entity(
                entity_id,
                new_unique_id=new_unique_id
            )
            _LOGGER.info(f"Migrated entity {entity_id}: {entity.unique_id} -> {new_unique_id}")
            migrated_count += 1
        except Exception as e:
            _LOGGER.error(f"Failed to migrate entity {entity_id}: {e}")
            # 如果迁移失败，则删除旧实体让系统重新创建
            entity_registry.async_remove(entity_id)
            _LOGGER.info(f"Removed entity {entity_id} due to migration failure")
    
    if migrated_count > 0:
        _LOGGER.info(f"Successfully migrated {migrated_count} entities to new location")

async def cleanup_old_entities(hass, config_entry, old_longitude=None, old_latitude=None):
    """清理旧的实体，当经纬度发生变化时（备用方法）"""
    if old_longitude is None or old_latitude is None:
        return
    
    entity_registry = er.async_get(hass)
    
    # 获取所有与此集成相关的实体
    entities_to_remove = []
    
    for entity_id, entity in entity_registry.entities.items():
        if entity.config_entry_id == config_entry.entry_id and entity.platform == DOMAIN:
            # 检查是否是旧的实体（基于旧的经纬度）
            old_unique_id_suffix = f"_{old_longitude}_{old_latitude}"
            if entity.unique_id and old_unique_id_suffix in entity.unique_id:
                entities_to_remove.append(entity_id)
    
    # 删除旧实体
    for entity_id in entities_to_remove:
        _LOGGER.info(f"Removing old entity: {entity_id}")
        entity_registry.async_remove(entity_id)
    
    if entities_to_remove:
        _LOGGER.info(f"Cleaned up {len(entities_to_remove)} old entities")

async def cleanup_duplicate_entities(hass, config_entry):
    """清理重复的实体，保留最新的"""
    entity_registry = er.async_get(hass)
    
    # 获取所有与此集成相关的实体，按传感器类型分组
    entities_by_type = {}
    
    for entity_id, entity in entity_registry.entities.items():
        if entity.config_entry_id == config_entry.entry_id and entity.platform == DOMAIN:
            if entity.unique_id:
                # 提取传感器类型（unique_id的第一部分）
                sensor_type = entity.unique_id.split('_')[0] + '_' + entity.unique_id.split('_')[1]
                if sensor_type not in entities_by_type:
                    entities_by_type[sensor_type] = []
                entities_by_type[sensor_type].append((entity_id, entity))
    
    # 检查每种传感器类型是否有重复
    entities_to_remove = []
    for sensor_type, entities in entities_by_type.items():
        if len(entities) > 1:
            # 有重复实体，保留最新的（通过entity_id排序，通常较新的ID会更大）
            entities.sort(key=lambda x: x[0])  # 按entity_id排序
            # 删除除最后一个之外的所有实体
            for entity_id, entity in entities[:-1]:
                entities_to_remove.append(entity_id)
                _LOGGER.info(f"Found duplicate entity for {sensor_type}: {entity_id}")
    
    # 删除重复实体
    for entity_id in entities_to_remove:
        _LOGGER.info(f"Removing duplicate entity: {entity_id}")
        entity_registry.async_remove(entity_id)
    
    if entities_to_remove:
        _LOGGER.info(f"Cleaned up {len(entities_to_remove)} duplicate entities")

def validate_longitude(lon: str) -> bool:
    try:
        lon_float = float(lon)
        return -180 <= lon_float <= 180
    except ValueError:
        return False

def validate_latitude(lat: str) -> bool:
    try:
        lat_float = float(lat)
        return -90 <= lat_float <= 90
    except ValueError:
        return False

class HeWeatherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1
    SUPPORT_MULTIPLE_ENTRIES = True

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return HeWeatherOptionsFlow(config_entry)
    _main_loop: asyncio.AbstractEventLoop
    _heweather_cert: HeWeatherCert

    _storage_path: str
    _auth_method: str
    _host: str
    _key: str
    _jwt_pubkey: str
    _jwt_sub: str
    _jwt_kid: str
    _longitude: str
    _latitude: str

    _disasterlevel: str
    _disastermsg: str

    def __init__(self):
        self._main_loop = asyncio.get_running_loop()
        self._storage_path = ''
        self._auth_method = DEFAULT_AUTH_METHOD
        self._host = DEFAULT_HOST
        self._key = ''
        self._jwt_pubkey = ''
        self._jwt_sub = ''
        self._jwt_kid = ''

        self._longitude = ''
        self._latitude = ''

        self._disasterlevel = DEFAULT_DISASTER_LEVEL_CONF
        self._disastermsg = DEFAULT_DISASTER_MSG

    async def async_step_user(
        self, user_input: Optional[dict] = None
    ):
        #if self._async_current_entries():
        #    return self.async_abort(reason="single_instance_allowed")

        self.hass.data.setdefault(DOMAIN, {})
        if not self._storage_path:
            self._storage_path = self.hass.config.path('.storage', DOMAIN)
        # HeWeather Certification
        self._heweather_cert = self.hass.data[DOMAIN].get('heweather_cert', None)
        if not self._heweather_cert:
            self._heweather_cert = HeWeatherCert(
                root_path=self._storage_path,
                loop=self._main_loop)
            self.hass.data[DOMAIN]['heweather_cert'] = self._heweather_cert
            _LOGGER.info(
                'async_step_user, create heweather cert, %s', self._storage_path)
            
        return await self.async_step_auth_method_config(user_input)

    async def async_step_auth_method_config(
        self, user_input: Optional[dict] = None
    ):
        if user_input:
            self._auth_method = user_input.get("auth_method", self._auth_method)
            if self._auth_method == "key":
                return await self.async_step_auth_apikey_config()
            else:
                return await self.async_step_auth_jwt_config()
        return await self.__show_auth_method_config_form("")

    async def __show_auth_method_config_form(self, reason: str):
        return self.async_show_form(
            step_id="auth_method_config",
            data_schema=vol.Schema({
                vol.Required(
                    "auth_method",
                    default=self._auth_method
                ): vol.In(AUTH_METHOD)
            }),
            errors={'base': reason},
            last_step=False
        )

    async def async_step_auth_apikey_config(
        self, user_input: Optional[dict] = None
    ):
        if user_input:
            if user_input.get("key", self._key) == "":
                return await self.__show_auth_apikey_config_form("key is empty")
            elif user_input.get("host", None) == "":
                return await self.__show_auth_apikey_config_form("host is empty")
            else:
                self._key = user_input.get("key", self._key)
                self._host = user_input.get("host", self._host)
                return await self.async_step_location_config()
        return await self.__show_auth_apikey_config_form("")

    async def __show_auth_apikey_config_form(self, reason: str):
        return self.async_show_form(
            step_id="auth_apikey_config",
            data_schema=vol.Schema({
                vol.Required(
                    "key",
                    default=self._key
                ): str,
                vol.Required(
                    "host",
                    default=self._host
                ): str
            }),
            errors={'base': reason},
            last_step=False
        )

    async def async_step_auth_jwt_config(
        self, user_input: Optional[dict] = None
    ):
        if user_input:
            if user_input.get("jwt_sub", self._key) == "":
                return await self.__show_auth_apikey_config_form("jwt_sub is empty")
            elif user_input.get("jwt_kid", None) == "":
                return await self.__show_auth_apikey_config_form("jwt_kid is empty")
            elif user_input.get("host", None) == "":
                return await self.__show_auth_apikey_config_form("host is empty")
            else:
                self._jwt_sub = user_input.get("jwt_sub", self._jwt_sub)
                self._jwt_kid = user_input.get("jwt_kid", self._jwt_kid)
                self._host = user_input.get("host", self._host)
                return await self.async_step_location_config()
        await self._heweather_cert.gen_key_async()
        self._jwt_pubkey = await self._heweather_cert.get_pub_key_async()
        return await self.__show_auth_jwt_config_form("")

    async def __show_auth_jwt_config_form(self, reason: str):
        return self.async_show_form(
            step_id="auth_jwt_config",
            data_schema=vol.Schema({
                vol.Required(
                    "jwt_sub",
                    default=self._jwt_sub
                ): str,
                vol.Required(
                    "jwt_kid",
                    default=self._jwt_kid
                ): str,
                vol.Required(
                    "host",
                    default=self._host
                ): str
            }),
            description_placeholders={
                "jwt_pubkey": self._jwt_pubkey,
            },
            errors={'base': reason},
            last_step=False
        )

    async def async_step_location_config(
        self, user_input: Optional[dict] = None
    ):
        if user_input:
            longitude = user_input.get("longitude", "")
            latitude = user_input.get("latitude", "")

            if not longitude or not latitude:
                return await self.__show_location_config_form("empty_location")
            
            if not validate_longitude(longitude):
                return await self.__show_location_config_form("invalid_longitude")
            
            if not validate_latitude(latitude):
                return await self.__show_location_config_form("invalid_latitude")

            self._longitude = f"{float(longitude):.4f}"
            self._latitude = f"{float(latitude):.4f}"
            return await self.async_step_disaster_config()
        return await self.__show_location_config_form("")

    async def __show_location_config_form(self, reason: str):
        return self.async_show_form(
            step_id="location_config",
            data_schema=vol.Schema({
                vol.Required(
                    "longitude",
                    default=self._longitude
                ): str,
                vol.Required(
                    "latitude",
                    default=self._latitude
                ): str,
            }),
            errors={'base': reason},
            last_step=False
        )

    async def async_step_disaster_config(
        self, user_input: Optional[dict] = None
    ):
        if user_input:
            self._disasterlevel = user_input.get("disasterlevel", self._disasterlevel)
            self._disastermsg = user_input.get("disastermsg", self._disastermsg)
            return await self.config_flow_done()
        return await self.__show_disaster_config_form("")
    
    async def __show_disaster_config_form(self, reason: str):
        return self.async_show_form(
            step_id="disaster_config",
            data_schema=vol.Schema({
                vol.Required(
                    "disasterlevel",
                    default=self._disasterlevel
                ): vol.In(DISASTER_LEVEL_CONF),
                vol.Required(
                    "disastermsg",
                    default=self._disastermsg
                ): vol.In(DISASTER_MSG),
            }),
            errors={'base': reason},
            last_step=False
        )

    async def config_flow_done(self):
        return self.async_create_entry(
            title=DEFAULT_NAME,
            data={
                CONF_AUTH_METHOD: self._auth_method,
                CONF_KEY: self._key,
                CONF_STORAGE_PATH: self._storage_path,
                CONF_JWT_SUB: self._jwt_sub,
                CONF_JWT_KID: self._jwt_kid,
                CONF_HOST: self._host,
                CONF_LONGITUDE: self._longitude,
                CONF_LATITUDE: self._latitude,
                CONF_DISASTERLEVEL: self._disasterlevel,
                CONF_DISASTERMSG: self._disastermsg,
            })


class HeWeatherOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HeWeather."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._auth_method = config_entry.data.get(CONF_AUTH_METHOD, DEFAULT_AUTH_METHOD)
        self._jwt_pubkey = ""
        self._heweather_cert = None
        
        # Initialize variables for different auth methods
        self._key = config_entry.data.get(CONF_KEY, "")
        self._host = config_entry.data.get(CONF_HOST, DEFAULT_HOST)
        self._jwt_sub = config_entry.data.get(CONF_JWT_SUB, "")
        self._jwt_kid = config_entry.data.get(CONF_JWT_KID, "")
        
        # Initialize location and disaster config
        self._longitude = config_entry.data.get(CONF_LONGITUDE, "")
        self._latitude = config_entry.data.get(CONF_LATITUDE, "")
        self._disasterlevel = config_entry.data.get(CONF_DISASTERLEVEL, DEFAULT_DISASTER_LEVEL_CONF)
        self._disastermsg = config_entry.data.get(CONF_DISASTERMSG, DEFAULT_DISASTER_MSG)

    async def async_step_init(self, user_input: Optional[dict] = None):
        """Manage the options."""
        return await self.async_step_auth_method_config()

    async def async_step_auth_method_config(self, user_input: Optional[dict] = None):
        """Handle authentication method configuration."""
        if user_input is not None:
            self._auth_method = user_input.get("auth_method", self._auth_method)
            if self._auth_method == "key":
                return await self.async_step_auth_apikey_config()
            else:
                return await self.async_step_auth_jwt_config()

        return self.async_show_form(
            step_id="auth_method_config",
            data_schema=vol.Schema({
                vol.Required(
                    "auth_method",
                    default=self._auth_method
                ): vol.In(AUTH_METHOD)
            }),
        )

    async def async_step_auth_apikey_config(self, user_input: Optional[dict] = None):
        """Handle API key authentication configuration."""
        if user_input is not None:
            # Validate inputs
            if not user_input.get("key", "").strip():
                return self.async_show_form(
                    step_id="auth_apikey_config",
                    data_schema=self._get_apikey_schema(),
                    errors={"base": "key is empty"}
                )
            if not user_input.get("host", "").strip():
                return self.async_show_form(
                    step_id="auth_apikey_config",
                    data_schema=self._get_apikey_schema(),
                    errors={"base": "host is empty"}
                )
            
            # Store auth data and proceed to location config
            self._key = user_input.get("key", "")
            self._host = user_input.get("host", DEFAULT_HOST)
            return await self.async_step_location_config()

        return self.async_show_form(
            step_id="auth_apikey_config",
            data_schema=self._get_apikey_schema(),
        )

    def _get_apikey_schema(self):
        """Get API key configuration schema."""
        current_key = self._config_entry.data.get(CONF_KEY, "")
        current_host = self._config_entry.data.get(CONF_HOST, DEFAULT_HOST)
        
        return vol.Schema({
            vol.Required(
                "key",
                default=current_key
            ): str,
            vol.Required(
                "host",
                default=current_host
            ): str
        })

    async def async_step_auth_jwt_config(self, user_input: Optional[dict] = None):
        """Handle JWT authentication configuration."""
        if user_input is not None:
            # Validate inputs
            if not user_input.get("jwt_sub", "").strip():
                return self.async_show_form(
                    step_id="auth_jwt_config",
                    data_schema=self._get_jwt_schema(),
                    description_placeholders={"jwt_pubkey": self._jwt_pubkey},
                    errors={"base": "jwt_sub is empty"}
                )
            if not user_input.get("jwt_kid", "").strip():
                return self.async_show_form(
                    step_id="auth_jwt_config",
                    data_schema=self._get_jwt_schema(),
                    description_placeholders={"jwt_pubkey": self._jwt_pubkey},
                    errors={"base": "jwt_kid is empty"}
                )
            if not user_input.get("host", "").strip():
                return self.async_show_form(
                    step_id="auth_jwt_config",
                    data_schema=self._get_jwt_schema(),
                    description_placeholders={"jwt_pubkey": self._jwt_pubkey},
                    errors={"base": "host is empty"}
                )
            
            # Store auth data and proceed to location config
            self._jwt_sub = user_input.get("jwt_sub", "")
            self._jwt_kid = user_input.get("jwt_kid", "")
            self._host = user_input.get("host", DEFAULT_HOST)
            return await self.async_step_location_config()

        # Get HeWeather cert instance and public key
        if not self._heweather_cert:
            # Get the cert instance from hass data
            storage_path = self._config_entry.data.get(CONF_STORAGE_PATH)
            if storage_path:
                self.hass.data.setdefault(DOMAIN, {})
                self._heweather_cert = self.hass.data[DOMAIN].get('heweather_cert', None)
                if not self._heweather_cert:
                    import asyncio
                    loop = asyncio.get_running_loop()
                    self._heweather_cert = HeWeatherCert(root_path=storage_path, loop=loop)
                    self.hass.data[DOMAIN]['heweather_cert'] = self._heweather_cert

        # Get existing public key (don't regenerate)
        if self._heweather_cert:
            self._jwt_pubkey = await self._heweather_cert.get_pub_key_async()
            # Only generate new key if no existing key found
            if not self._jwt_pubkey:
                await self._heweather_cert.gen_key_async()
                self._jwt_pubkey = await self._heweather_cert.get_pub_key_async()

        return self.async_show_form(
            step_id="auth_jwt_config",
            data_schema=self._get_jwt_schema(),
            description_placeholders={"jwt_pubkey": self._jwt_pubkey},
        )

    def _get_jwt_schema(self):
        """Get JWT configuration schema."""
        current_jwt_sub = self._config_entry.data.get(CONF_JWT_SUB, "")
        current_jwt_kid = self._config_entry.data.get(CONF_JWT_KID, "")
        current_host = self._config_entry.data.get(CONF_HOST, DEFAULT_HOST)
        
        return vol.Schema({
            vol.Required(
                "jwt_sub",
                default=current_jwt_sub
            ): str,
            vol.Required(
                "jwt_kid",
                default=current_jwt_kid
            ): str,
            vol.Required(
                "host",
                default=current_host
            ): str
        })

    async def async_step_location_config(self, user_input: Optional[dict] = None):
        """Handle location configuration."""
        if user_input is not None:
            longitude = user_input.get("longitude", "")
            latitude = user_input.get("latitude", "")

            # Validate location inputs
            if not longitude or not latitude:
                return self.async_show_form(
                    step_id="location_config",
                    data_schema=self._get_location_schema(),
                    errors={"base": "empty_location"}
                )
            
            if not validate_longitude(longitude):
                return self.async_show_form(
                    step_id="location_config",
                    data_schema=self._get_location_schema(),
                    errors={"base": "invalid_longitude"}
                )
            
            if not validate_latitude(latitude):
                return self.async_show_form(
                    step_id="location_config",
                    data_schema=self._get_location_schema(),
                    errors={"base": "invalid_latitude"}
                )

            self._longitude = f"{float(longitude):.4f}"
            self._latitude = f"{float(latitude):.4f}"
            return await self.async_step_disaster_config()

        return self.async_show_form(
            step_id="location_config",
            data_schema=self._get_location_schema(),
        )

    def _get_location_schema(self):
        """Get location configuration schema."""
        current_longitude = self._config_entry.data.get(CONF_LONGITUDE, "")
        current_latitude = self._config_entry.data.get(CONF_LATITUDE, "")
        
        return vol.Schema({
            vol.Required(
                "longitude",
                default=current_longitude
            ): str,
            vol.Required(
                "latitude",
                default=current_latitude
            ): str,
        })

    async def async_step_disaster_config(self, user_input: Optional[dict] = None):
        """Handle disaster configuration."""
        if user_input is not None:
            self._disasterlevel = user_input.get("disasterlevel", DEFAULT_DISASTER_LEVEL_CONF)
            self._disastermsg = user_input.get("disastermsg", DEFAULT_DISASTER_MSG)
            return await self.options_flow_done()

        return self.async_show_form(
            step_id="disaster_config",
            data_schema=self._get_disaster_schema(),
        )

    def _get_disaster_schema(self):
        """Get disaster configuration schema."""
        current_disasterlevel = self._config_entry.data.get(CONF_DISASTERLEVEL, DEFAULT_DISASTER_LEVEL_CONF)
        current_disastermsg = self._config_entry.data.get(CONF_DISASTERMSG, DEFAULT_DISASTER_MSG)
        
        return vol.Schema({
            vol.Required(
                "disasterlevel",
                default=current_disasterlevel
            ): vol.In(DISASTER_LEVEL_CONF),
            vol.Required(
                "disastermsg",
                default=current_disastermsg
            ): vol.In(DISASTER_MSG),
        })

    async def options_flow_done(self):
        """Create the updated config entry."""
        # Get old location data for cleanup
        old_longitude = self._config_entry.data.get(CONF_LONGITUDE)
        old_latitude = self._config_entry.data.get(CONF_LATITUDE)
        
        # Check if location has changed
        location_changed = (
            old_longitude != self._longitude or
            old_latitude != self._latitude
        )
        
        # Build the updated data based on auth method
        # Preserve existing auth data when switching methods
        updated_data = {
            CONF_AUTH_METHOD: self._auth_method,
            CONF_STORAGE_PATH: self._config_entry.data.get(CONF_STORAGE_PATH),
            CONF_LONGITUDE: self._longitude,
            CONF_LATITUDE: self._latitude,
            CONF_DISASTERLEVEL: self._disasterlevel,
            CONF_DISASTERMSG: self._disastermsg,
        }

        if self._auth_method == "key":
            # Update API key settings, preserve existing JWT settings
            updated_data.update({
                CONF_KEY: self._key,
                CONF_HOST: self._host,
                CONF_JWT_SUB: self._config_entry.data.get(CONF_JWT_SUB, ""),
                CONF_JWT_KID: self._config_entry.data.get(CONF_JWT_KID, ""),
            })
        else:
            # Update JWT settings, preserve existing API key settings
            updated_data.update({
                CONF_KEY: self._config_entry.data.get(CONF_KEY, ""),
                CONF_HOST: self._host,
                CONF_JWT_SUB: self._jwt_sub,
                CONF_JWT_KID: self._jwt_kid,
            })

        # Migrate entities if location changed (更平滑的实体迁移)
        if location_changed and old_longitude and old_latitude:
            _LOGGER.info(f"Location changed from ({old_longitude}, {old_latitude}) to ({self._longitude}, {self._latitude})")
            # 先尝试迁移实体
            await migrate_entities_for_location_change(
                self.hass, self._config_entry,
                old_longitude, old_latitude,
                self._longitude, self._latitude
            )
        
        # Always check for and clean up duplicate entities
        await cleanup_duplicate_entities(self.hass, self._config_entry)

        # Update the config entry data directly
        self.hass.config_entries.async_update_entry(
            self._config_entry, data=updated_data
        )
        
        # For options flow, we should reload the entry to apply changes
        # 重新加载会创建新实体（如果迁移失败的话）
        await self.hass.config_entries.async_reload(self._config_entry.entry_id)
        
        # Return empty result to indicate successful update
        return self.async_create_entry(title="", data={})
