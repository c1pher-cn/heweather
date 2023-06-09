import logging
from datetime import datetime, timedelta

import asyncio
import async_timeout
import aiohttp

import voluptuous as vol

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from homeassistant.components.weather import (
    WeatherEntity, 
    ATTR_FORECAST_CONDITION, 
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_TIME, 
    PLATFORM_SCHEMA)
from homeassistant.const import (
    ATTR_ATTRIBUTION, 
    CONF_MODE,
    LENGTH_KILOMETERS,
    PRESSURE_HPA,
    SPEED_KILOMETERS_PER_HOUR,
    PRECIPITATION_MILLIMETERS_PER_HOUR,
    TEMP_CELSIUS
)

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

TIME_BETWEEN_UPDATES = timedelta(seconds=600)

DEFAULT_TIME = dt_util.now()

CONF_LOCATION = "location"
CONF_KEY = "key"

CONDITION_CLASSES = {
    'sunny': ["晴"],
    'cloudy': ["多云"],
    'partlycloudy': ["少云", "晴间多云", "阴"],
    'windy': ["有风", "微风", "和风", "清风"],
    'windy-variant': ["强风", "劲风", "疾风", "大风", "烈风"],
    'hurricane': ["飓风", "龙卷风", "热带风暴", "狂暴风", "风暴"],
    'rainy': ["雨", "毛毛雨", "细雨", "小雨", "小到中雨", "中雨", "中到大雨", "大雨", "大到暴雨", "阵雨", "极端降雨", "冻雨"],
    'pouring': ["暴雨", "暴雨到大暴雨", "大暴雨", "大暴雨到特大暴雨", "特大暴雨", "强阵雨"],
    'lightning-rainy': ["雷阵雨", "强雷阵雨"],
    'fog': ["雾", "薄雾", "霾", "浓雾", "强浓雾", "中度霾", "重度霾", "严重霾", "大雾", "特强浓雾"],
    'hail': ["雷阵雨伴有冰雹"],
    'snowy': ["小雪", "小到中雪", "中雪", "中到大雪", "大雪", "大到暴雪", "暴雪", "阵雪"],
    'snowy-rainy': ["雨夹雪", "雨雪天气", "阵雨夹雪"],
    'exceptional': ["扬沙", "浮尘", "沙尘暴", "强沙尘暴", "未知"],
}

ATTR_UPDATE_TIME = "更新时间"
ATTRIBUTION = "来自和风天气的天气数据"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_LOCATION): cv.string,
    vol.Required(CONF_KEY): cv.string,
})


#@asyncio.coroutine
async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the hefeng weather."""
    _LOGGER.info("setup platform weather.Heweather...")

    location = config.get(CONF_LOCATION)
    key = config.get(CONF_KEY)
    

    data = WeatherData(hass, location, key)

    #yield from 
    await data.async_update(dt_util.now())
    async_track_time_interval(hass, data.async_update, TIME_BETWEEN_UPDATES)

    async_add_devices([LocalWeather(data, location)], True)


class LocalWeather(WeatherEntity):
    """Representation of a weather condition."""

    _attr_native_temperature_unit = TEMP_CELSIUS
    _attr_native_precipitation_unit = PRECIPITATION_MILLIMETERS_PER_HOUR
    _attr_native_pressure_unit = PRESSURE_HPA
    _attr_native_wind_speed_unit = SPEED_KILOMETERS_PER_HOUR
    _attr_native_visibility_unit = LENGTH_KILOMETERS
    
    def __init__(self, data, location):
        """Initialize the  weather."""
        #self._name = None
        self._object_id = 'localweather'
        self._condition = None
        self._temperature = None
        self._humidity = None
        self._pressure = None
        self._wind_speed = None
        self._wind_bearing = None
        self._visibility = None
        self._precipitation = None
        self._forecast = None

        self._data = data
        self._updatetime = None
        self._attr_unique_id = 'localweather_'+location

    #@property
    #def name(self):
    #    """Return the name of the sensor."""
    #    return self._object_id

    @property
    def registry_name(self):
        """返回实体的friendly_name属性."""
        return '{} {}'.format('和风天气', self._name)

    @property
    def should_poll(self):
        """attention No polling needed for a demo weather condition."""
        return True

    @property
    def native_temperature(self):
        """Return the temperature."""
        return self._temperature

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._attr_native_temperature_unit

    @property
    def humidity(self):
        """Return the humidity."""
        return self._humidity

    @property
    def native_wind_speed(self):
        """Return the wind speed."""
        return self._wind_speed
    
    @property
    def wind_bearing(self):
        """Return the wind speed."""
        return self._wind_bearing

    @property
    def native_pressure(self):
        """Return the pressure."""
        return self._pressure
    
    @property
    def native_visibility(self):
        """Return the visibility."""
        return self._visibility
    
    @property
    def native_precipitation(self):
        """Return the precipitation."""
        return self._precipitation   
    
    @property
    def condition(self):
        """Return the weather condition."""
        return [k for k, v in CONDITION_CLASSES.items() if
                self._condition in v][0]

    @property
    def attribution(self):
        """Return the attribution."""
        return 'Powered by Home Assistant'

    @property
    def device_state_attributes(self):
        """设置其它一些属性值."""
        if self._condition is not None:
            return {
                ATTR_ATTRIBUTION: ATTRIBUTION,
                ATTR_UPDATE_TIME: self._updatetime
            }

    @property
    def forecast(self):
        """Return the forecast."""

        reftime = datetime.now()

        forecast_data = []
        for entry in self._forecast:

            data_dict = {
                ATTR_FORECAST_TIME: reftime.isoformat(),
                ATTR_FORECAST_CONDITION: entry[0],
                ATTR_FORECAST_NATIVE_TEMP: entry[1],
                ATTR_FORECAST_NATIVE_TEMP_LOW: entry[2]
            }
            reftime = reftime + timedelta(days=1)
            forecast_data.append(data_dict)

        return forecast_data

    #@asyncio.coroutine
    async def async_update(self, now=DEFAULT_TIME):
        """update函数变成了async_update."""
        self._updatetime = self._data.updatetime
        #self._name = self._data.name
        self._condition = self._data.condition
        self._temperature = self._data.temperature
        _attr_native_temperature_unit  = self._data.temperature_unit
        self._humidity = self._data.humidity
        self._pressure = self._data.pressure
        self._wind_speed = self._data.wind_speed
        self._wind_bearing = self._data.wind_bearing
        self._visibility = self._data.visibility
        self._precipitation = self._data.precipitation

        self._forecast = self._data.forecast
        _LOGGER.info("success to update informations")


class WeatherData():
    """天气相关的数据，存储在这个类中."""

    def __init__(self, hass, location, key):
        """初始化函数."""
        self._hass = hass

        #self._url = "https://free-api.heweather.com/s6/weather/forecast?location="+location+"&key="+key
        self._forecast_url = "https://devapi.qweather.com/v7/weather/7d?location="+location+"&key="+key
        self._weather_now_url = "https://devapi.qweather.com/v7/weather/now?location="+location+"&key="+key
        self._params = {"location": location,
                        "key": key}

        #self._name = None
        self._condition = None
        self._temperature = None
        self._temperature_unit = None
        self._humidity = None
        self._pressure = None
        self._wind_speed = None
        self._wind_bearing = None
        self._visibility = None
        self._precipitation = None
    
        self._forecast = None
        self._updatetime = None

    #@property
    #def name(self):
    #    """地点."""
    #    return self._name

    @property
    def condition(self):
        """天气情况."""
        return self._condition

    @property
    def temperature(self):
        """温度."""
        return self._temperature

    @property
    def temperature_unit(self):
        """温度单位."""
        return TEMP_CELSIUS

    @property
    def humidity(self):
        """湿度."""
        return self._humidity

    @property
    def pressure(self):
        """气压."""
        return self._pressure

    @property
    def wind_speed(self):
        """风速."""
        return self._wind_speed
    
    @property
    def wind_bearing(self):
        """风向."""
        return self._wind_bearing
    
    @property
    def visibility(self):
        """能见度."""
        return self._visibility
    
    @property
    def precipitation (self):
        """当前小时累计降水量."""
        return self._precipitation    
    
    
    @property
    def forecast(self):
        """预报."""
        return self._forecast

    @property
    def updatetime(self):
        """更新时间."""
        return self._updatetime

    #@asyncio.coroutine
    async def async_update(self, now):
        """从远程更新信息."""
        _LOGGER.info("Update from JingdongWangxiang's OpenAPI...")

        """
        # 异步模式的测试代码
        import time
        _LOGGER.info("before time.sleep")
        time.sleep(40)
        _LOGGER.info("after time.sleep and before asyncio.sleep")
        asyncio.sleep(40)
        _LOGGER.info("after asyncio.sleep and before yield from asyncio.sleep")
        #yield from 
	await asyncio.sleep(40)
        _LOGGER.info("after yield from asyncio.sleep")
        """

        # 通过HTTP访问，获取需要的信息
        # 此处使用了基于aiohttp库的async_get_clientsession
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            connector = aiohttp.TCPConnector(limit=10)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(self._weather_now_url) as response:
                    json_data = await response.json()
                    weather = json_data["now"]
                async with session.get(self._forecast_url) as response:
                    json_data = await response.json()
                    forecast = json_data

        except(asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Error while accessing: %s", self._weather_now_url)
            _LOGGER.error("Error while accessing: %s", self._forecast_url)
            return
        
        
       # try:
       #     session = async_get_clientsession(self._hass)
       #     with async_timeout.timeout(15):
       #         response = yield from session.get(
       #             self._url)

        #except(asyncio.TimeoutError, aiohttp.ClientError):
        #    _LOGGER.error("Error while accessing: %s", self._url)
        #    return

        #if response.status != 200:
        #    _LOGGER.error("Error while accessing: %s, status=%d",
        #                  self._url,
        #                  response.status)
        #    return

        #result = yield from response.json()
#
#        if result is None:
#            _LOGGER.error("Request api Error")
#            return
#        elif result["code"] != "200":
#            _LOGGER.error("Error API return, code=%s, msg=%s",
#                          result["code"],
#                          result["msg"])
#            return

        # 根据http返回的结果，更新数据
#        all_result = result["daily"]
#        self._temperature = float(all_result[0]["tempMax"])
#        self._humidity = int(all_result[0]["humidity"])
#        self._condition = all_result[0]["textDay"]
#        self._pressure = int(all_result[0]["pressure"])
#        self._wind_speed = float(all_result[0]["windSpeedDay"])
#        self._updatetime = result["updateTime"]
        
        self._temperature = float(weather["temp"])
        self._humidity = float(weather["humidity"])
        self._pressure = weather["pressure"]
        self._condition = weather["text"]
        self._wind_speed = weather["windSpeed"]
        self._wind_bearing = weather["windDir"]
        self._visibility = weather["vis"]
        self._precipitation =  float(weather["precip"])


        #self._windDir = weather["windDir"]
       # self._windScale = weather["windScale"]
       # self._windSpeed = weather["windSpeed"]
        self._updatetime = weather["obsTime"]

        
        
        
        
        
        datemsg = forecast["daily"]
        
        forec_cond = []
        for n in range(7):
            for i, j in CONDITION_CLASSES.items():
                if datemsg[n]["textDay"] in j:
                    forec_cond.append(i)

        self._forecast = [
            [forec_cond[0], int(datemsg[0]["tempMax"]), int(datemsg[0]["tempMin"])],
            [forec_cond[1], int(datemsg[1]["tempMax"]), int(datemsg[1]["tempMin"])],
            [forec_cond[2], int(datemsg[2]["tempMax"]), int(datemsg[2]["tempMin"])],
            [forec_cond[3], int(datemsg[3]["tempMax"]), int(datemsg[3]["tempMin"])],
            [forec_cond[4], int(datemsg[4]["tempMax"]), int(datemsg[4]["tempMin"])],
            [forec_cond[5], int(datemsg[5]["tempMax"]), int(datemsg[5]["tempMin"])],
            [forec_cond[6], int(datemsg[6]["tempMax"]), int(datemsg[6]["tempMin"])]
        ]
        _LOGGER.info("success to load local informations")
