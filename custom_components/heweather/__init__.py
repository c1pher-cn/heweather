import asyncio
import logging
from typing import Optional
from .heweather.heweather_cert import HeWeatherCert
from .heweather.const import (
    DOMAIN,
    CONF_LOCATION,
)


from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

PLATFORMS = [Platform.WEATHER, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


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
        cert = HeWeatherCert(root_path=config_entry.data.get(CONF_LOCATION), loop=loop)
        hass.data[DOMAIN]["heweather_cert"] = cert
        _LOGGER.info("create heweather cert instance")

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    return unload_ok

async def async_remove_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    heweather_cert: HeWeatherCert = hass.data[DOMAIN]['heweather_cert']
    
    await heweather_cert.del_key_async()

    return True
