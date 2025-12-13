import asyncio
import logging
from typing import Optional
from .heweather.heweather_cert import HeWeatherCert
from .heweather.const import (
    DOMAIN,
    CONF_STORAGE_PATH,
)


from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er

SUPPORTED_PLATFORMS = [Platform.WEATHER, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def cleanup_duplicate_entities_on_startup(hass: HomeAssistant, config_entry: ConfigEntry):
    """在启动时清理重复的实体"""
    entity_registry = er.async_get(hass)
    
    # 获取所有与此集成相关的实体，按传感器类型分组
    entities_by_type = {}
    
    for entity_id, entity in entity_registry.entities.items():
        if entity.config_entry_id == config_entry.entry_id and entity.platform == DOMAIN:
            if entity.unique_id:
                # 提取传感器类型（unique_id的第一部分）
                try:
                    sensor_type = entity.unique_id.split('_')[0] + '_' + entity.unique_id.split('_')[1]
                    if sensor_type not in entities_by_type:
                        entities_by_type[sensor_type] = []
                    entities_by_type[sensor_type].append((entity_id, entity))
                except IndexError:
                    # 如果unique_id格式不符合预期，跳过
                    continue
    
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
        _LOGGER.info(f"Removing duplicate entity on startup: {entity_id}")
        entity_registry.async_remove(entity_id)
    
    if entities_to_remove:
        _LOGGER.info(f"Cleaned up {len(entities_to_remove)} duplicate entities on startup")


async def async_setup(hass: HomeAssistant, hass_config: dict) -> bool:
    # pylint: disable=unused-argument
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    # Get running loop
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    if not loop:
        raise Exception('loop is None')
    # HeWeather Certification
    cert: Optional[HeWeatherCert] = hass.data[DOMAIN].get("heweather_cert", None)
    if not cert:
        cert = HeWeatherCert(root_path=config_entry.data.get(CONF_STORAGE_PATH), loop=loop)
        hass.data[DOMAIN]["heweather_cert"] = cert
        _LOGGER.info("create heweather cert instance")

    await hass.config_entries.async_forward_entry_setups(config_entry, SUPPORTED_PLATFORMS)
    
    # 清理重复的实体（在平台设置完成后）
    await cleanup_duplicate_entities_on_startup(hass, config_entry)

    return True


async def async_update_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Update a given config entry."""
    await hass.config_entries.async_reload(config_entry.entry_id)
    
    # 在重新加载后清理重复实体
    await cleanup_duplicate_entities_on_startup(hass, config_entry)
    
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, SUPPORTED_PLATFORMS
    )

    return unload_ok

async def async_remove_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    heweather_cert: HeWeatherCert = hass.data[DOMAIN]['heweather_cert']
    
    await heweather_cert.del_key_async()

    hass.data.pop(DOMAIN, None)

    return True
