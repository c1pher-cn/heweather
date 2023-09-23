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
    WeatherEntityFeature,
    Forecast,
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
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

TIME_BETWEEN_UPDATES = timedelta(seconds=1800)
HOURLY_TIME_BETWEEN_UPDATES = timedelta(seconds=1800)

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
# # 集成安装
# async def async_setup_entry(hass, config_entry, async_add_entities):
#     _LOGGER.debug(f"register_static_path: {ROOT_PATH + ':custom_components/qweather/local'}")
#     hass.http.register_static_path(ROOT_PATH, hass.config.path('custom_components/qweather/local'), False)
#     hass.components.frontend.add_extra_js_url(hass, ROOT_PATH + '/qweather-card/qweather-card.js?ver=' + VERSION)
#     hass.components.frontend.add_extra_js_url(hass, ROOT_PATH + '/qweather-card/qweather-more-info.js?ver=' + VERSION)
#
#     _LOGGER.info("setup platform weather.Heweather...")
#
#     name = config_entry.data.get(CONF_NAME)
#     key = config_entry.data[CONF_API_KEY]
#     location = config_entry.data[CONF_LOCATION]
#     #unique_id = config_entry.unique_id
#     longitude = round(config_entry.data[CONF_LONGITUDE],2)
#     latitude = round(config_entry.data[CONF_LATITUDE],2)
#     update_interval_minutes = config_entry.options.get(CONF_UPDATE_INTERVAL, 10)
#     dailysteps = config_entry.options.get(CONF_DAILYSTEPS, 7)
#     if dailysteps != 7 and dailysteps !=3:
#         dailysteps = 7
#     hourlysteps = config_entry.options.get(CONF_HOURLYSTEPS, 24)
#     if hourlysteps != 24:
#         hourlysteps = 24
#     alert = config_entry.options.get(CONF_ALERT, True)
#     life = config_entry.options.get(CONF_LIFEINDEX, True)
#     starttime = config_entry.options.get(CONF_STARTTIME, 0)
#     gird_weather = config_entry.options.get(CONF_GIRD, False)
#
#     #data = WeatherData(hass, name, unique_id, api_key, longitude, latitude, dailysteps ,hourlysteps, alert, life, starttime, gird_weather)
#     #location = config.get(CONF_LOCATION)
#     #key = config.get(CONF_KEY)
#     data = WeatherData(hass, location, key)
#     await data.async_update(dt_util.now())
#     async_track_time_interval(hass, data.async_update, timedelta(minutes = update_interval_minutes))
#     _LOGGER.debug('[%s]刷新间隔时间: %s 分钟', name, update_interval_minutes)
#     async_add_entities([HeWeather(data, location)], True)

#@asyncio.coroutine
async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
   """Set up the hefeng weather."""
   _LOGGER.info("setup platform weather.Heweather...")

   location = config.get(CONF_LOCATION)
   key = config.get(CONF_KEY)
   data = WeatherData(hass, location, key)
   await data.async_update(dt_util.now())
   async_track_time_interval(hass, data.async_update, TIME_BETWEEN_UPDATES)

   async_add_devices([HeWeather(data, location)], True)


class HeWeather(WeatherEntity):
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
        self._forecast_hourly = None
        self._dew = None
        self._feelslike = None
        self._cloud =None

        self._data = data
        self._updatetime = None
        self._attr_unique_id = 'localweather_'+location

        self._attr_supported_features = 0
        self._attr_supported_features = WeatherEntityFeature.FORECAST_DAILY
        self._attr_supported_features |= WeatherEntityFeature.FORECAST_HOURLY


    @property
    def name(self):
        """返回实体的名字."""
        return '和风天气'

    @property
    def should_poll(self):
        """attention No polling needed for a demo weather condition."""
        return True



    @property
    def native_dew_point(self):
        """Return the native_dew_point."""
        return self._dew

    @property
    def native_apparent_temperature(self):
        """Return the native_apparent_temperature."""
        return self._feelslike

    @property
    def cloud_coverage(self):
        """Return the cloud_coverage."""
        return self._cloud


    @property
    def native_temperature(self):
        """Return the temperature."""
        return self._temperature

    @property
    def native_temperature_unit(self):
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

#    @property
#    def attribution(self):
#        """Return the attribution."""
#        return 'Powered by Home Assistant'

#    @property
#    def device_state_attributes(self):
#        """设置其它一些属性值."""
#        if self._condition is not None:
#            return {
#                ATTR_ATTRIBUTION: ATTRIBUTION,
#                ATTR_UPDATE_TIME: self._updatetime
#            }

    async def async_forecast_daily(self) -> list[Forecast]:
        """Return the daily forecast."""
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

    async def async_forecast_hourly(self) -> list[Forecast]:
        """Return the daily forecast."""
        reftime = datetime.now()

        forecast_hourly_data = []
        for entry in self._forecast_hourly:
            data_dict = {
                ATTR_FORECAST_TIME: reftime.isoformat(),
                ATTR_FORECAST_CONDITION: entry[0],
                ATTR_FORECAST_NATIVE_TEMP: entry[1],
                ATTR_FORECAST_HUMIDITY: entry[2],
                #"native_precipitation": entry[3],
                ATTR_FORECAST_WIND_BEARING: entry[4],
                ATTR_FORECAST_NATIVE_WIND_SPEED: entry[5],
                "precipitation_probability": entry[6]


            }
            #[forecast_hourly[0], float(hourlymsg[0]["temp"]), float(hourlymsg[0]["humidity"]), float(hourlymsg[0]["precip"]), hourlymsg[0]["windDir"], int(hourlymsg[0]["windSpeed"])],

            reftime = reftime + timedelta(hours=1)
            forecast_hourly_data.append(data_dict)

        return forecast_hourly_data


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
        self._dew = self._data.dew
        self._feelslike = self._data.feelslike
        self._cloud = self._data.cloud

        self._forecast = self._data.forecast
        self._forecast_hourly = self._data.forecast_hourly
        _LOGGER.info("success to update informations")


class WeatherData():
    """天气相关的数据，存储在这个类中."""

    def __init__(self, hass, location, key):
        """初始化函数."""
        self._hass = hass

        #self._url = "https://free-api.heweather.com/s6/weather/forecast?location="+location+"&key="+key
        self._forecast_url = "https://devapi.qweather.com/v7/weather/7d?location="+location+"&key="+key
        self._weather_now_url = "https://devapi.qweather.com/v7/weather/now?location="+location+"&key="+key
        self._forecast_hourly_url = "https://devapi.qweather.com/v7/weather/24h?location="+location+"&key="+key
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
        self._dew = None
        self._feelslike = None
        self._cloud =None

        self._forecast = None
        self._forecast_hourly = None
        self._updatetime = None


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
    def dew(self):
        """露点温度"""
        return self._dew

    @property
    def feelslike(self):
        """体感温度"""
        return self._feelslike

    @property
    def cloud(self):
        """云量"""
        return self._cloud


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
        """天预报."""
        return self._forecast

    @property
    def forecast_hourly(self):
        """小时预报."""
        return self._forecast_hourly

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
                async with session.get(self._forecast_hourly_url) as response:
                    json_data = await response.json()
                    forecast_hourly = json_data

        except(asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Error while accessing: %s", self._weather_now_url)
            _LOGGER.error("Error while accessing: %s", self._forecast_url)
            _LOGGER.error("Error while accessing: %s", self._forecast_hourly_url)
            return




        self._temperature = float(weather["temp"])
        self._humidity = float(weather["humidity"])
        self._pressure = weather["pressure"]
        self._condition = weather["text"]
        self._wind_speed = weather["windSpeed"]
        self._wind_bearing = weather["windDir"]
        self._visibility = weather["vis"]
        self._precipitation =  float(weather["precip"])

        self._feelslike = float(weather["feelsLike"])
        self._dew = float(weather["dew"])
        self._cloud = int(weather["cloud"])



       # self._windScale = weather["windScale"]
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

        hourlymsg = forecast_hourly["hourly"]
        forecast_hourly = []
        for n in range(24):
            for i, j in CONDITION_CLASSES.items():
                if hourlymsg[n]["text"] in j:
                    forecast_hourly.append(i)

        self._forecast_hourly = [
            [forecast_hourly[0], float(hourlymsg[0]["temp"]), float(hourlymsg[0]["humidity"]), float(hourlymsg[0]["precip"]), hourlymsg[0]["windDir"], int(hourlymsg[0]["windSpeed"]), float(hourlymsg[0]["pop"])],
            [forecast_hourly[1], float(hourlymsg[1]["temp"]), float(hourlymsg[1]["humidity"]), float(hourlymsg[1]["precip"]), hourlymsg[1]["windDir"], int(hourlymsg[1]["windSpeed"]), float(hourlymsg[1]["pop"])],
            [forecast_hourly[2], float(hourlymsg[2]["temp"]), float(hourlymsg[2]["humidity"]), float(hourlymsg[2]["precip"]), hourlymsg[2]["windDir"], int(hourlymsg[2]["windSpeed"]), float(hourlymsg[2]["pop"])],
            [forecast_hourly[3], float(hourlymsg[3]["temp"]), float(hourlymsg[3]["humidity"]), float(hourlymsg[3]["precip"]), hourlymsg[3]["windDir"], int(hourlymsg[3]["windSpeed"]), float(hourlymsg[3]["pop"])],
            [forecast_hourly[4], float(hourlymsg[4]["temp"]), float(hourlymsg[4]["humidity"]), float(hourlymsg[4]["precip"]), hourlymsg[4]["windDir"], int(hourlymsg[4]["windSpeed"]), float(hourlymsg[4]["pop"])],
            [forecast_hourly[5], float(hourlymsg[5]["temp"]), float(hourlymsg[5]["humidity"]), float(hourlymsg[5]["precip"]), hourlymsg[5]["windDir"], int(hourlymsg[5]["windSpeed"]), float(hourlymsg[5]["pop"])],
            [forecast_hourly[6], float(hourlymsg[6]["temp"]), float(hourlymsg[6]["humidity"]), float(hourlymsg[6]["precip"]), hourlymsg[6]["windDir"], int(hourlymsg[6]["windSpeed"]), float(hourlymsg[6]["pop"])],
            [forecast_hourly[7], float(hourlymsg[7]["temp"]), float(hourlymsg[7]["humidity"]), float(hourlymsg[7]["precip"]), hourlymsg[7]["windDir"], int(hourlymsg[7]["windSpeed"]), float(hourlymsg[7]["pop"])],
            [forecast_hourly[8], float(hourlymsg[8]["temp"]), float(hourlymsg[8]["humidity"]), float(hourlymsg[8]["precip"]), hourlymsg[8]["windDir"], int(hourlymsg[8]["windSpeed"]), float(hourlymsg[8]["pop"])],
            [forecast_hourly[9], float(hourlymsg[9]["temp"]), float(hourlymsg[9]["humidity"]), float(hourlymsg[9]["precip"]), hourlymsg[9]["windDir"], int(hourlymsg[9]["windSpeed"]), float(hourlymsg[9]["pop"])],
            [forecast_hourly[10], float(hourlymsg[10]["temp"]), float(hourlymsg[10]["humidity"]), float(hourlymsg[10]["precip"]), hourlymsg[10]["windDir"], int(hourlymsg[10]["windSpeed"]), float(hourlymsg[10]["pop"])],
            [forecast_hourly[11], float(hourlymsg[11]["temp"]), float(hourlymsg[11]["humidity"]), float(hourlymsg[11]["precip"]), hourlymsg[11]["windDir"], int(hourlymsg[11]["windSpeed"]), float(hourlymsg[11]["pop"])],
            [forecast_hourly[12], float(hourlymsg[12]["temp"]), float(hourlymsg[12]["humidity"]), float(hourlymsg[12]["precip"]), hourlymsg[12]["windDir"], int(hourlymsg[12]["windSpeed"]), float(hourlymsg[12]["pop"])],
            [forecast_hourly[13], float(hourlymsg[13]["temp"]), float(hourlymsg[13]["humidity"]), float(hourlymsg[13]["precip"]), hourlymsg[13]["windDir"], int(hourlymsg[13]["windSpeed"]), float(hourlymsg[13]["pop"])],
            [forecast_hourly[14], float(hourlymsg[14]["temp"]), float(hourlymsg[14]["humidity"]), float(hourlymsg[14]["precip"]), hourlymsg[14]["windDir"], int(hourlymsg[14]["windSpeed"]), float(hourlymsg[14]["pop"])],
            [forecast_hourly[15], float(hourlymsg[15]["temp"]), float(hourlymsg[15]["humidity"]), float(hourlymsg[15]["precip"]), hourlymsg[15]["windDir"], int(hourlymsg[15]["windSpeed"]), float(hourlymsg[15]["pop"])],
            [forecast_hourly[16], float(hourlymsg[16]["temp"]), float(hourlymsg[16]["humidity"]), float(hourlymsg[16]["precip"]), hourlymsg[16]["windDir"], int(hourlymsg[16]["windSpeed"]), float(hourlymsg[16]["pop"])],
            [forecast_hourly[17], float(hourlymsg[17]["temp"]), float(hourlymsg[17]["humidity"]), float(hourlymsg[17]["precip"]), hourlymsg[17]["windDir"], int(hourlymsg[17]["windSpeed"]), float(hourlymsg[17]["pop"])],
            [forecast_hourly[18], float(hourlymsg[18]["temp"]), float(hourlymsg[18]["humidity"]), float(hourlymsg[18]["precip"]), hourlymsg[18]["windDir"], int(hourlymsg[18]["windSpeed"]), float(hourlymsg[18]["pop"])],
            [forecast_hourly[19], float(hourlymsg[19]["temp"]), float(hourlymsg[19]["humidity"]), float(hourlymsg[19]["precip"]), hourlymsg[19]["windDir"], int(hourlymsg[19]["windSpeed"]), float(hourlymsg[19]["pop"])],
            [forecast_hourly[20], float(hourlymsg[20]["temp"]), float(hourlymsg[20]["humidity"]), float(hourlymsg[20]["precip"]), hourlymsg[20]["windDir"], int(hourlymsg[20]["windSpeed"]), float(hourlymsg[20]["pop"])],
            [forecast_hourly[21], float(hourlymsg[21]["temp"]), float(hourlymsg[21]["humidity"]), float(hourlymsg[21]["precip"]), hourlymsg[21]["windDir"], int(hourlymsg[21]["windSpeed"]), float(hourlymsg[21]["pop"])],
            [forecast_hourly[22], float(hourlymsg[22]["temp"]), float(hourlymsg[22]["humidity"]), float(hourlymsg[22]["precip"]), hourlymsg[22]["windDir"], int(hourlymsg[22]["windSpeed"]), float(hourlymsg[22]["pop"])],
            [forecast_hourly[23], float(hourlymsg[23]["temp"]), float(hourlymsg[23]["humidity"]), float(hourlymsg[23]["precip"]), hourlymsg[23]["windDir"], int(hourlymsg[23]["windSpeed"]), float(hourlymsg[23]["pop"])]




        ]
        _LOGGER.info("success to load local informations")
