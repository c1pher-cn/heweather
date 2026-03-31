import logging
from datetime import timedelta
import time

# 此处引入了几个异步处理的库
import asyncio
import async_timeout
import aiohttp

import voluptuous as vol

# aiohttp_client将aiohttp的session与hass关联起来
# track_time_interval需要使用对应的异步的版本
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION, ATTR_FRIENDLY_NAME,
    #TEMP_CELSIUS,
    UnitOfTemperature,
    PERCENTAGE,
    #PRECIPITATION_MILLIMETERS_PER_HOUR,
    UnitOfVolumetricFlux,
    #SPEED_KILOMETERS_PER_HOUR,
    UnitOfSpeed,
    #PRESSURE_HPA,
    UnitOfPressure,
    #LENGTH_KILOMETERS
    UnitOfLength
)
from homeassistant.helpers.entity import Entity, DeviceInfo
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util

from .heweather.const import (
    DOMAIN,
    CONF_AUTH_METHOD,
    CONF_OPTIONS,
    CONF_LONGITUDE,
    CONF_LATITUDE,
    CONF_HOST,
    CONF_KEY,
    CONF_JWT_SUB,
    CONF_JWT_KID,
    DEFAULT_HOST,
    CONF_DISASTERLEVEL,
    CONF_DISASTERMSG,
    CONF_SENSOR_LIST,
    DISASTER_LEVEL,
    ATTR_UPDATE_TIME,
    ATTR_SUGGESTION,
    ATTRIBUTION
)

_LOGGER = logging.getLogger(__name__)

WEATHER_TIME_BETWEEN_UPDATES = timedelta(seconds=600)
LIFESUGGESTION_TIME_BETWEEN_UPDATES = timedelta(seconds=7200)

OPTIONS = {
    "temprature": ["heweather_temperature", "室外温度", "mdi:thermometer", UnitOfTemperature.CELSIUS],
    "humidity": ["heweather_humidity", "室外湿度", "mdi:water-percent", PERCENTAGE],
    "feelsLike": ["heweather_feelsLike", "体感温度", "mdi:thermometer", UnitOfTemperature.CELSIUS],
    "text": ["heweather_text", "天气描述", "mdi:thermometer", ' '],
    "precip": ["heweather_precip", "小时降水量", "mdi:weather-rainy", UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR],
    "windDir": ["heweather_windDir", "风向", "mdi:windsock", ' '],
    "windScale": ["heweather_windScale", "风力等级", "mdi:weather-windy", ' '],
    "windSpeed": ["heweather_windSpeed", "风速", "mdi:weather-windy", UnitOfSpeed.KILOMETERS_PER_HOUR],
    "dew": ["heweather_dew", "露点温度", "mdi:thermometer-water", ' '],
    "pressure": ["heweather_pressure", "大气压强", "mdi:thermometer", UnitOfPressure.HPA],
    "vis": ["heweather_vis", "能见度", "mdi:thermometer", UnitOfLength.KILOMETERS],
    "cloud": ["heweather_cloud", "云量", "mdi:cloud-percent", PERCENTAGE],
    "primary": ["heweather_primary", "空气质量的主要污染物", "mdi:weather-dust", " "],
    "category": ["heweather_category", "空气质量指数级别", "mdi:walk", " "],
    "level": ["heweather_level", "空气质量指数等级", "mdi:walk", " "],
    "pm2p5": ["heweather_pm25", "PM2.5", "mdi:walk", " "],
    "pm10": ["heweather_pm10", "PM10", "mdi:walk", " "],
    "no2": ["heweather_no2", "二氧化氮", "mdi:emoticon-dead", " "],
    "so2": ["heweather_so2", "二氧化硫", "mdi:emoticon-dead", " "],
    "co": ["heweather_co", "一氧化碳", "mdi:molecule-co", " "],
    "o3": ["heweather_o3", "臭氧", "mdi:weather-cloudy", " "],
    "no": ["heweather_no", "一氧化氮", "mdi:emoticon-dead", " "],
    "nmhc": ["heweather_nmhc", "非甲烷总烃", "mdi:emoticon-dead", " "],
    "qlty": ["heweather_qlty", "综合空气质量", "mdi:quality-high", " "],
    "disaster_warn": ["heweather_disaster_warn", "灾害预警", "mdi:alert", " "],

    "air": ["suggestion_air", "空气污染扩散条件指数", "mdi:air-conditioner", " "],
    "comf": ["suggestion_comf", "舒适度指数", "mdi:human-greeting", " "],
    "cw": ["suggestion_cw", "洗车指数", "mdi:car", " "],
    "drsg": ["suggestion_drsg", "穿衣指数", "mdi:hanger", " "],
    "flu": ["suggestion_flu", "感冒指数", "mdi:biohazard", " "],
    "sport": ["suggestion_sport", "运动指数", "mdi:badminton", " "],
    "trav": ["suggestion_trav", "旅行指数", "mdi:wallet-travel", " "],
    "uv": ["suggestion_uv", "紫外线指数", "mdi:sun-wireless", " "],
    "guomin": ["suggestion_guomin", "过敏指数", "mdi:sunglasses", " "],
    "kongtiao": ["suggestion_kongtiao", "空调开启指数", "mdi:air-conditioner", " "],
    "sunglass": ["suggestion_sunglass", "太阳镜指数", "mdi:sunglasses", " "],
    "fangshai": ["suggestion_fangshai", "防晒指数", "mdi:shield-sun-outline", " "],
    "liangshai": ["suggestion_liangshai", "晾晒指数", "mdi:tshirt-crew-outline", " "],

    "jiaotong": ["suggestion_jiaotong", "交通指数", "mdi:train-car", " "],

}


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_LONGITUDE): cv.string,
    vol.Required(CONF_LATITUDE): cv.string,
    vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
    vol.Required(CONF_KEY): cv.string,
    vol.Required(CONF_DISASTERLEVEL): cv.string,
    vol.Required(CONF_DISASTERMSG): cv.string,

})


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """这个协程是程序的入口，其中add_devices函数也变成了异步版本."""
    _LOGGER.info("setup platform sensor.Heweather...")

    longitude = config_entry.data.get(CONF_LONGITUDE)
    latitude = config_entry.data.get(CONF_LATITUDE)
    host = config_entry.data.get(CONF_HOST)
    key = config_entry.data.get(CONF_KEY)
    disastermsg = config_entry.data.get(CONF_DISASTERMSG)
    disasterlevel = config_entry.data.get(CONF_DISASTERLEVEL)
    # 这里通过 data 实例化class weatherdata，并传入调用API所需信息
    auth_method = config_entry.data.get(CONF_AUTH_METHOD)
    if auth_method == "key":
        key = config_entry.data.get(CONF_KEY)
        suggestion_data = SuggestionData(hass, longitude, latitude, host, key=key)
        weather_data = WeatherData(hass, longitude, latitude, host, disastermsg, disasterlevel, key=key)
    else:
        # HeWeather Certification
        heweather_cert = hass.data[DOMAIN].get('heweather_cert', None)
        jwt_sub = config_entry.data.get(CONF_JWT_SUB)
        jwt_kid = config_entry.data.get(CONF_JWT_KID)
        suggestion_data = SuggestionData(hass, longitude, latitude, host, heweather_cert=heweather_cert, jwt_sub=jwt_sub, jwt_kid=jwt_kid)
        weather_data = WeatherData(hass, longitude, latitude, host, disastermsg, disasterlevel, heweather_cert=heweather_cert, jwt_sub=jwt_sub, jwt_kid=jwt_kid)

    await weather_data.async_update(dt_util.now())
    config_entry.async_on_unload(async_track_time_interval(hass, weather_data.async_update, WEATHER_TIME_BETWEEN_UPDATES, cancel_on_shutdown=True))

    await suggestion_data.async_update(dt_util.now())
    config_entry.async_on_unload(async_track_time_interval(hass, suggestion_data.async_update, LIFESUGGESTION_TIME_BETWEEN_UPDATES, cancel_on_shutdown=True))

    dev = []
    for option in CONF_SENSOR_LIST:
        dev.append(HeweatherWeatherSensor(weather_data, suggestion_data, option, longitude, latitude))
    async_add_entities(dev, True)


#@asyncio.coroutine
async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """这个协程是程序的入口，其中add_devices函数也变成了异步版本."""
    _LOGGER.info("setup platform sensor.Heweather...")

    longitude = config.get(CONF_LONGITUDE)
    latitude = config.get(CONF_LATITUDE)
    host = config.get(CONF_HOST)
    key = config.get(CONF_KEY)
    disastermsg = config.get(CONF_DISASTERMSG)
    disasterlevel = config.get(CONF_DISASTERLEVEL)
    # 这里通过 data 实例化class weatherdata，并传入调用API所需信息
    weather_data = WeatherData(hass, longitude, latitude, host, disastermsg, disasterlevel, key=key)
    suggestion_data = SuggestionData(hass, longitude, latitude, host, key=key)

    await weather_data.async_update(dt_util.now())
    async_track_time_interval(hass, weather_data.async_update, WEATHER_TIME_BETWEEN_UPDATES, cancel_on_shutdown=True)

    await suggestion_data.async_update(dt_util.now())
    async_track_time_interval(hass, suggestion_data.async_update, LIFESUGGESTION_TIME_BETWEEN_UPDATES, cancel_on_shutdown=True)

    dev = []
    for option in CONF_SENSOR_LIST:
        dev.append(HeweatherWeatherSensor(weather_data, suggestion_data, option, longitude, latitude))
    async_add_devices(dev, True)


class HeweatherWeatherSensor(Entity):
    """定义一个温度传感器的类，继承自HomeAssistant的Entity类."""
    _attr_has_entity_name = True
    
    def __init__(self, weather_data, suggestion_data, option, longitude, latitude):
        """初始化."""
        self._weather_data = weather_data
        self._suggestion_data = suggestion_data
        self._object_id = OPTIONS[option][0]
        
        # 【修改重点】直接使用 OPTIONS 里的中文名称作为实体名
        # OPTIONS[option][1] 对应代码最上面的字典里的 "舒适度指数"、"洗车指数" 等中文
        self._attr_name = OPTIONS[option][0] 
        
        self._icon = OPTIONS[option][2]
        self._unit_of_measurement = OPTIONS[option][3]

        self._type = option
        self._state = None
        self._attributes = {"states":"null"}
        self._updatetime = None
        self._attr_unique_id = f"{OPTIONS[option][0]}_{longitude}_{latitude}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._weather_data._params['location']}")},
            name="和风天气",
            manufacturer="QWeather",
            model="API v7",
            entry_type=None,
        )

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        return self._attributes
        
    @property
    def translation_key(self):
        """Return the translation key to translate the entity's name and states."""
        return self._object_id
    
    #@property
    #def name(self):
    #    """返回实体的名字."""
    #    return self._name

    #@property
    #def registry_name(self):
    #    """返回实体的friendly_name属性."""
    #    return self._friendly_name

    @property
    def state(self):
        """返回当前的状态."""
        return self._state

    @property
    def icon(self):
        """返回icon属性."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """返回unit_of_measuremeng属性."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """设置其它一些属性值."""
        if self._state is not None:
            return {
                ATTR_ATTRIBUTION: ATTRIBUTION,
                ATTR_UPDATE_TIME: self._updatetime
            }

    #@asyncio.coroutine
    async def async_update(self):
        """update函数变成了async_update."""
        self._updatetime = self._weather_data.updatetime

        if self._type == "temprature":
            self._state = self._weather_data.temprature
        elif self._type == "humidity":
            self._state = self._weather_data.humidity
        elif self._type == "feelsLike":
            self._state = self._weather_data.feelsLike
        elif self._type == "text":
            self._state = self._weather_data.text
        elif self._type == "windDir":
            self._state = self._weather_data.windDir
        elif self._type == "windScale":
            self._state = self._weather_data.windScale
        elif self._type == "windSpeed":
            self._state = self._weather_data.windSpeed
        elif self._type == "precip":
            self._state = self._weather_data.precip
        elif self._type == "pressure":
            self._state = self._weather_data.pressure
        elif self._type == "vis":
            self._state = self._weather_data.vis
        elif self._type == "dew":
            self._state = self._weather_data.dew
        elif self._type == "cloud":
            self._state = self._weather_data.cloud
        elif self._type == "category":
            self._state = self._weather_data.category
        elif self._type == "primary":
            self._state = self._weather_data.primary
        elif self._type == "level":
            self._state = self._weather_data.level
        elif self._type == "pm10":
            self._state = self._weather_data.pm10
        elif self._type == "pm2p5":
            self._state = self._weather_data.pm2p5
        elif self._type == "no2":
            self._state = self._weather_data.no2
        elif self._type == "so2":
            self._state = self._weather_data.so2
        elif self._type == "co":
            self._state = self._weather_data.co
        elif self._type == "o3":
            self._state = self._weather_data.o3
        elif self._type == "no":
            self._state = self._weather_data.no
        elif self._type == "nmhc":
            self._state = self._weather_data.nmhc
        elif self._type == "qlty":
            self._state = self._weather_data.qlty
        elif self._type == "disaster_warn":
            if len(self._weather_data.disaster_warn) > 10:
                self._state = 'on'
                self._attributes["states"] = self._weather_data.disaster_warn
            else:
                self._state = 'off'
                self._attributes["states"] = self._weather_data.disaster_warn
        #lifesuggestion
        elif self._type == "air":
            self._state = self._suggestion_data.air[0]
            self._attributes["states"] = self._suggestion_data.air[1]
        elif self._type == "comf":
            self._state = self._suggestion_data.comf[0]
            self._attributes["states"] = self._suggestion_data.comf[1]
        elif self._type == "cw":
            self._state = self._suggestion_data.cw[0]
            self._attributes["states"] = self._suggestion_data.cw[1]
        elif self._type == "drsg":
            self._state = self._suggestion_data.drsg[0]
            self._attributes["states"] = self._suggestion_data.drsg[1]
        elif self._type == "flu":
            self._state = self._suggestion_data.flu[0]
            self._attributes["states"] = self._suggestion_data.flu[1]
        elif self._type == "sport":
            self._state = self._suggestion_data.sport[0]
            self._attributes["states"] = self._suggestion_data.sport[1]
        elif self._type == "trav":
            self._state = self._suggestion_data.trav[0]
            self._attributes["states"] = self._suggestion_data.trav[1]
        elif self._type == "uv":
            self._state = self._suggestion_data.uv[0]
            self._attributes["states"] = self._suggestion_data.uv[1]
        elif self._type == "guomin":
            self._state = self._suggestion_data.guomin[0]
            self._attributes["states"] = self._suggestion_data.guomin[1]
        elif self._type == "kongtiao":
            self._state = self._suggestion_data.kongtiao[0]
            self._attributes["states"] = self._suggestion_data.kongtiao[1]
        elif self._type == "liangshai":
            self._state = self._suggestion_data.liangshai[0]
            self._attributes["states"] = self._suggestion_data.liangshai[1]
        elif self._type == "fangshai":
            self._state = self._suggestion_data.fangshai[0]
            self._attributes["states"] = self._suggestion_data.fangshai[1]
        elif self._type == "sunglass":
            self._state = self._suggestion_data.uv[0]
            self._attributes["states"] = self._suggestion_data.uv[1]
        elif self._type == "jiaotong":
            self._state = self._suggestion_data.jiaotong[0]
            self._attributes["states"] = self._suggestion_data.jiaotong[1]

        # 设置污染物单位
        pollutant_types = {"pm10", "pm2p5", "no2", "so2", "co", "o3", "no", "nmhc"}
        if self._type in pollutant_types:
            unit = getattr(self._weather_data, f"{self._type}_unit", None)
            if unit:
                self._unit_of_measurement = unit

class WeatherData(object):
    """天气相关的数据，存储在这个类中."""

    def __init__(self, hass, longitude, latitude, host, disastermsg, disasterlevel, key=None, heweather_cert=None, jwt_sub=None, jwt_kid=None):
        """初始化函数."""
        self._hass = hass
        location = f"{longitude},{latitude}"
        self._disastermsg = disastermsg
        self._disasterlevel = disasterlevel
        #disastermsg, disasterlevel

        self._temprature = None
        self._humidity = None

        if key is not None:
            self._is_jwt = False
            self._weather_now_url = "https://"+host+"/v7/weather/now?location="+location+"&key="+key
            self._air_now_url = "https://"+host+"/airquality/v1/current/"+latitude+"/"+longitude+"?key="+key
            self._disaster_warn_url = "https://"+host+"/weatheralert/v1/current/"+latitude+"/"+longitude+"?key="+key
            self._params = {"location": location,
                            "key": key}
        else:
            self._is_jwt = True
            self._weather_now_url = "https://"+host+"/v7/weather/now?location="+location
            self._air_now_url = "https://"+host+"/airquality/v1/current/"+latitude+"/"+longitude
            self._disaster_warn_url = "https://"+host+"/weatheralert/v1/current/"+latitude+"/"+longitude
            self._params = {"location": location}
            self._heweather_cert = heweather_cert
            self._jwt_sub = jwt_sub
            self._jwt_kid = jwt_kid

        self._feelsLike = None
        self._text = None
        self._windDir = None
        self._windScale = None
        self._windSpeed = None
        self._precip = None
        self._pressure = None
        self._vis = None
        self._cloud = None
        self._dew = None
        self._updatetime = None

        self._category = None
        self._pm10 = None
        self._primary = None
        self._level = None



        self._pm2p5 = None
        self._no2 = None
        self._so2 = None
        self._co = None
        self._o3 = None
        self._no = None
        self._nmhc = None
        # 新 API 单位不固定，动态获取
        self._pm10_unit = None
        self._pm2p5_unit = None
        self._no2_unit = None
        self._so2_unit = None
        self._co_unit = None
        self._o3_unit = None
        self._no_unit = None
        self._nmhc_unit = None
        self._qlty = None
        self._disaster_warn = None
        self._updatetime = None

    @property
    def temprature(self):
        """温度."""
        return self._temprature

    @property
    def humidity(self):
        """湿度."""
        return self._humidity

    @property
    def feelsLike(self):
        """体感温度"""
        return self._feelsLike

    @property
    def text(self):
        """天气状况的文字描述，包括阴晴雨雪等天气状态的描述"""
        return self._text

    @property
    def windDir(self):
        """风向"""
        return self._windDir

    @property
    def category(self):
        """空气质量指数级别"""
        return self._category

    @property
    def level(self):
        """空气质量指数等级"""
        return self._level

    @property
    def primary(self):
        """空气质量的主要污染物，空气质量为优时，返回值为NA"""
        return self._primary

    @property
    def windScale(self):
        """风力等级"""
        return self._windScale

    @property
    def windSpeed(self):
        """风速，公里/小时"""
        return self._windSpeed

    @property
    def precip(self):
        """当前小时累计降水量，默认单位：毫米"""
        return self._precip

    @property
    def pressure(self):
        """大气压强，默认单位：百帕"""
        return self._pressure

    @property
    def vis(self):
        """能见度，默认单位：公里"""
        return self._vis

    @property
    def cloud(self):
        """云量，百分比数值。可能为空"""
        return self._cloud

    @property
    def dew(self):
        """露点温度。可能为空"""
        return self._dew

    @property
    def pm2p5(self):
        """pm2.5"""
        return self._pm2p5

    @property
    def pm2p5_unit(self):
        return self._pm2p5_unit

    @property
    def pm10(self):
        """pm10"""
        return self._pm10

    @property
    def pm10_unit(self):
        return self._pm10_unit

    @property
    def qlty(self):
        """(aqi)空气质量指数"""
        return self._qlty

    @property
    def no2(self):
        """no2"""
        return self._no2

    @property
    def no2_unit(self):
        return self._no2_unit

    @property
    def co(self):
        """co"""
        return self._co

    @property
    def co_unit(self):
        return self._co_unit

    @property
    def so2(self):
        """so2"""
        return self._so2

    @property
    def so2_unit(self):
        return self._so2_unit

    @property
    def o3(self):
        """o3"""
        return self._o3

    @property
    def o3_unit(self):
        return self._o3_unit

    @property
    def no(self):
        """no"""
        return self._no

    @property
    def no_unit(self):
        return self._no_unit

    @property
    def nmhc(self):
        """nmhc"""
        return self._nmhc

    @property
    def nmhc_unit(self):
        return self._nmhc_unit

    @property
    def disaster_warn(self):
        """灾害预警"""
        return self._disaster_warn


    @property
    def updatetime(self):
        """更新时间."""
        return self._updatetime

    #@asyncio.coroutine
    async def async_update(self, now):
        """从远程更新信息."""
        _LOGGER.info("Update from JingdongWangxiang's OpenAPI...")

        # 通过HTTP访问，获取需要的信息
        # 此处使用了基于aiohttp库的async_get_clientsession
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            connector = aiohttp.TCPConnector(limit=10)
            headers = None
            if self._is_jwt:
                jwt_token = await self._heweather_cert.get_jwt_token_heweather_async(self._jwt_sub, self._jwt_kid, int(time.time()) - 30, int(time.time()) + 180)
                headers = {'Authorization': f'Bearer {jwt_token}'}
            async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=headers) as session:
                async with session.get(self._weather_now_url) as response:
                    json_data = await response.json()
                    weather = json_data["now"]
                async with session.get(self._air_now_url) as response:
                    json_data = await response.json()
                    # AQI (CN) code: cn-mee
                    air_index = next((item for item in json_data["indexes"] if item["code"] == "cn-mee"), None)
                    air_pollutants = json_data["pollutants"]
                async with session.get(self._disaster_warn_url) as response:
                    json_data = await response.json()
                    disaster_warn = json_data["alerts"]


        except(asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Error while accessing: %s", self._weather_now_url)
            return

        # 根据http返回的结果，更新数据
        self._temprature = weather["temp"]
        self._humidity = weather["humidity"]
        self._feelsLike = weather["feelsLike"]
        self._text = weather["text"]
        self._windDir = weather["windDir"]
        self._windScale = weather["windScale"]
        self._windSpeed = weather["windSpeed"]
        self._precip = weather["precip"]
        self._pressure = weather["pressure"]
        self._vis = weather["vis"]
        self._cloud = weather["cloud"]
        self._dew = weather["dew"]
        self._updatetime = weather["obsTime"]
        self._qlty = air_index["aqiDisplay"]
        self._level = air_index["level"]
        self._category = air_index["category"]
        primary_pollutant = air_index["primaryPollutant"]
        if primary_pollutant is not None and "name" in primary_pollutant:
            self._primary = primary_pollutant["name"]

        supported_codes = {"pm10", "pm2p5", "co", "no", "no2", "so2", "o3", "nmhc"}
        for pollutant in air_pollutants:
            code = pollutant["code"]
            if code in supported_codes:
                setattr(self, f"_{code}", pollutant["concentration"]["value"])
                setattr(self, f"_{code}_unit", pollutant["concentration"]["unit"])


        allmsg=''
        titlemsg=''
        # Normalize disaster_warn into a list for safe iteration
        if disaster_warn is None:
            alerts = []
        elif isinstance(disaster_warn, dict):
            alerts = [disaster_warn]
        elif isinstance(disaster_warn, list):
            alerts = disaster_warn
        else:
            # Unexpected type: try to coerce to list if possible, else empty
            try:
                alerts = list(disaster_warn)
            except Exception:
                alerts = []

        for i in alerts:
            #if DISASTER_LEVEL[i["severity"]] >= 订阅等级:
            severity = i.get("severity", "").lower()
            if severity in DISASTER_LEVEL and (DISASTER_LEVEL[severity] >= int(self._disasterlevel)):
                allmsg = allmsg +i["headline"] + ':' + i["description"] + '||'
                titlemsg = titlemsg + i["headline"] + '||'

        if(len(titlemsg)<5):
            self._disaster_warn =  '近日无'+ self._disasterlevel +'级及以上灾害'
        #if(订阅标题)
        elif(self._disastermsg=='title'):
            self._disaster_warn =  titlemsg
        else:
            self._disaster_warn =  allmsg

class SuggestionData(object):
    """天气相关建议的数据，存储在这个类中."""

    def __init__(self, hass, longitude, latitude, host, key=None, heweather_cert=None, jwt_sub=None, jwt_kid=None):
        """初始化函数."""
        self._hass = hass
        location = f"{longitude},{latitude}"

        if key is not None:
            self._url = "https://"+host+"/v7/indices/1d?location="+location+"&key="+key+"&type=0"
            self._params = {"location": location,
                            "key": key,
                            "type": 0
                        }
            self._is_jwt = False
        else:
            self._url = "https://"+host+"/v7/indices/1d?location="+location+"&type=0"
            self._params = {"location": location,
                            "type": 0
                        }
            self._is_jwt = True
            self._heweather_cert = heweather_cert
            self._jwt_sub = jwt_sub
            self._jwt_kid = jwt_kid

        self._updatetime = ["1","1"]
        self._air = ["1","1"]
        self._comf = ["1","1"]
        self._cw = ["1","1"]
        self._drsg = ["1","1"]
        self._flu = ["1","1"]
        self._sport = ["1","1"]
        self._trav = ["1","1"]
        self._uv = ["1","1"]
        self._guomin = None
        self._kongtiao = None
        self._sunglass = None
        self._liangshai = None
        self._fangshai = None
        self._jiaotong = None

    @property
    def updatetime(self):
        """更新时间."""
        return self._updatetime

    @property
    def air(self):
        """空气污染扩散条件指数"""
        return self._air

    @property
    def comf(self):
        """舒适度指数"""
        return self._comf

    @property
    def cw(self):
        """洗车建议"""
        return self._cw

    @property
    def drsg(self):
        """穿着建议"""
        return self._drsg

    @property
    def flu(self):
        """流感提示"""
        return self._flu

    @property
    def sport(self):
        """运动建议"""
        return self._sport

    @property
    def trav(self):
        """旅游指南"""
        return self._trav

    @property
    def uv(self):
        """紫外线"""
        return self._uv

    @property
    def guomin(self):
        """过敏指数"""
        return self._guomin

    @property
    def kongtiao(self):
        """空调指数"""
        return self._kongtiao

    @property
    def sunglass(self):
        """太阳镜指数"""
        return self._sunglass

    @property
    def liangshai(self):
        """晾晒指数"""
        return self._liangshai

    @property
    def fangshai(self):
        """防晒指数"""
        return self._fangshai

    @property
    def jiaotong(self):
        """交通指数"""
        return self._jiaotong


    #@asyncio.coroutine
    async def async_update(self, now):
        """从远程更新信息."""
        try:
            session = async_get_clientsession(self._hass)
            headers = None
            if self._is_jwt:
                jwt_token = await self._heweather_cert.get_jwt_token_heweather_async(self._jwt_sub, self._jwt_kid, int(time.time()) - 30, int(time.time()) + 180)
                headers = {'Authorization': f'Bearer {jwt_token}'}
            with async_timeout.timeout(15):
            #with async_timeout.timeout(15, loop=self._hass.loop):
                response = await session.get(
                    self._url, headers=headers)

        except(asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Error while accessing: %s", self._url)
            return

        if response.status != 200:
            _LOGGER.error("Error while accessing: %s, status=%d",
                          self._url,
                          response.status)
            return

        result = await response.json()

        if result is None:
            _LOGGER.error("Request api Error")
            return
        elif result["code"] != "200":
            _LOGGER.error("Error API return, code=%s,url=%s",
                          result["code"],self._url)
            return

        # 根据http返回的结果，更新数据
        all_result = result["daily"]
        self._updatetime = result["updateTime"]
        for i in all_result:
            if i["type"] == "1":
                self._sport = [i["category"], i["text"]]

            if i["type"] == "10":
                self._air = [i["category"], i["text"]]

            if i["type"] == "8":
                self._comf = [i["category"], i["text"]]

            if i["type"] == "2":
                self._cw = [i["category"], i["text"]]

            if i["type"] == "3":
                self._drsg = [i["category"], i["text"]]

            if i["type"] == "9":
                self._flu = [i["category"], i["text"]]

            if i["type"] == "6":
                self._trav = [i["category"], i["text"]]

            if i["type"] == "5":
                self._uv = [i["category"], i["text"]]

            if i["type"] == "7":
                self._guomin = [i["category"], i["text"]]

            if i["type"] == "11":
                self._kongtiao = [i["category"], i["text"]]

            if i["type"] == "12":
                self._sunglass = [i["category"], i["text"]]

            if i["type"] == "14":
                self._liangshai = [i["category"], i["text"]]

            if i["type"] == "15":
                self._jiaotong = [i["category"], i["text"]]

            if i["type"] == "16":
                self._fangshai = [i["category"], i["text"]]
