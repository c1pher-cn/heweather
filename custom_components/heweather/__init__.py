from .heweather.const import DOMAIN

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

async def async_setup(hass: HomeAssistant, config: ConfigEntry) -> bool:
    
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(
            config_entry, [
                "sensor",
                "weather",
            ])

    return True