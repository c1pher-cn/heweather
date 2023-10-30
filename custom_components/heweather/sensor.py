import logging
from datetime import timedelta

# 此处引入了几个异步处理的库
import asyncio
import async_timeout
import aiohttp

import voluptuous as vol

# aiohttp_client将aiohttp的session与hass关联起来
# track_time_interval需要使用对应的异步的版本
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION, ATTR_FRIENDLY_NAME,
    TEMP_CELSIUS,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    PRECIPITATION_MILLIMETERS_PER_HOUR,
    SPEED_KILOMETERS_PER_HOUR,
    PRESSURE_HPA,
    LENGTH_KILOMETERS
)
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util


_LOGGER = logging.getLogger(__name__)

WEATHER_TIME_BETWEEN_UPDATES = timedelta(seconds=600)
LIFESUGGESTION_TIME_BETWEEN_UPDATES = timedelta(seconds=7200)

CONF_OPTIONS = "options"
CONF_LOCATION = "location"
CONF_KEY = "key"
CONF_DISASTERLEVEL = "disasterlevel"
CONF_DISASTERMSG = "disastermsg"
CONF_SENSOR_LIST = ["air","comf","cw","drsg","flu","sport","trav","uv","sunglass","guomin","liangshai","jiaotong","fangshai","kongtiao","disaster_warn","temprature","humidity","category","feelsLike","text","windDir","windScale","windSpeed","pressure","vis","cloud","dew","precip","qlty","level","primary","pm25","pm10","co","so2","no2","o3"]

OPTIONS = {
    "temprature": ["Heweather_temperature", "室外温度", "mdi:thermometer", TEMP_CELSIUS],
    "humidity": ["Heweather_humidity", "室外湿度", "mdi:water-percent", PERCENTAGE],
    "feelsLike": ["Heweather_feelsLike", "体感温度", "mdi:thermometer", TEMP_CELSIUS],
    "text": ["Heweather_text", "天气描述", "mdi:thermometer", ' '],
    "precip": ["Heweather_precip", "小时降水量", "mdi:weather-rainy", PRECIPITATION_MILLIMETERS_PER_HOUR],
    "windDir": ["Heweather_windDir", "风向", "mdi:windsock", ' '],
    "windScale": ["Heweather_windScale", "风力等级", "mdi:weather-windy", ' '],
    "windSpeed": ["Heweather_windSpeed", "风速", "mdi:weather-windy", SPEED_KILOMETERS_PER_HOUR],
    "dew": ["Heweather_dew", "露点温度", "mdi:thermometer-water", ' '],
    "pressure": ["Heweather_pressure", "大气压强", "mdi:thermometer", PRESSURE_HPA],
    "vis": ["Heweather_vis", "能见度", "mdi:thermometer", LENGTH_KILOMETERS],
    "cloud": ["Heweather_cloud", "云量", "mdi:cloud-percent", PERCENTAGE],
    "primary": ["Heweather_primary", "空气质量的主要污染物", "mdi:weather-dust", " "],
    "category": ["Heweather_category", "空气质量指数级别", "mdi:walk", " "],
    "level": ["Heweather_level", "空气质量指数等级", "mdi:walk", " "],
    "pm25": ["Heweather_pm25", "PM2.5", "mdi:walk", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER],
    "pm10": ["Heweather_pm10", "PM10", "mdi:walk", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER],
    "no2": ["Heweather_no2", "二氧化氮", "mdi:emoticon-dead", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER],
    "so2": ["Heweather_so2", "二氧化硫", "mdi:emoticon-dead", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER],
    "co": ["Heweather_co", "一氧化碳", "mdi:molecule-co", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER],
    "o3": ["Heweather_o3", "臭氧", "mdi:weather-cloudy", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER],
    "qlty": ["Heweather_qlty", "综合空气质量", "mdi:quality-high", " "],
    "disaster_warn": ["Heweather_disaster_warn", "灾害预警", "mdi:alert", " "],

    "air": ["suggestion_air", "空气污染扩散条件指数", "mdi:air-conditioner", " "],
    "comf": ["suggestion_comf", "舒适度指数", "mdi:human-greeting", " "],
    "cw": ["suggestion_cw", "洗车指数", "mdi:car", " "],
    "drsg": ["suggestion_drsg", "穿衣指数", "mdi:hanger", " "],
    "flu": ["suggestion_flu", "感冒指数", "mdi:biohazard", " "],
    "sport": ["suggestion_sport", "运动指数", "mdi:badminton", " "],
    "trav": ["suggestion_trav", "旅行指数", "mdi:wallet-travel", " "],
    "uv": ["suggestion_uv", "紫外线指数", "mdi:weather-sun-wireless", " "],
    "guomin": ["suggestion_guomin", "过敏指数", "mdi:sunglasses", " "],
    "kongtiao": ["suggestion_kongtiao", "空调开启指数", "mdi:air-conditioner", " "],
    "sunglass": ["suggestion_sunglass", "太阳镜指数", "mdi:sunglasses", " "],
    "fangshai": ["suggestion_fangshai", "防晒指数", "mdi:sun-protection-outline", " "],
    "liangshai": ["suggestion_liangshai", "晾晒指数", "mdi:tshirt-crew-outline", " "],

    "jiaotong": ["suggestion_jiaotong", "交通指数", "mdi:train-car", " "],

}

DISASTER_LEVEL = {
        "Cancel":0,
        "None":0,
        "Unknown":0,
        "Standard":1,
        "Minor":2,
        "Moderate":3,
        "Major":4,
        "Severe":5,
        "Extreme":6
        }
ATTR_UPDATE_TIME = "更新时间"
ATTR_SUGGESTION = "建议"
ATTRIBUTION = "来自和风天气的天气数据"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_LOCATION): cv.string,
    vol.Required(CONF_KEY): cv.string,
    vol.Required(CONF_DISASTERLEVEL): cv.string,
    vol.Required(CONF_DISASTERMSG): cv.string,

})


#@asyncio.coroutine
async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """这个协程是程序的入口，其中add_devices函数也变成了异步版本."""
    _LOGGER.info("setup platform sensor.Heweather...")

    location = config.get(CONF_LOCATION)
    key = config.get(CONF_KEY)
    disastermsg = config.get(CONF_DISASTERMSG)
    disasterlevel = config.get(CONF_DISASTERLEVEL)
    # 这里通过 data 实例化class weatherdata，并传入调用API所需信息
    weather_data = WeatherData(hass, location, key, disastermsg, disasterlevel)
    suggestion_data = SuggestionData(hass, location, key)

    await weather_data.async_update(dt_util.now())
    async_track_time_interval(hass, weather_data.async_update, WEATHER_TIME_BETWEEN_UPDATES)

    await suggestion_data.async_update(dt_util.now())
    async_track_time_interval(hass, suggestion_data.async_update, LIFESUGGESTION_TIME_BETWEEN_UPDATES)

    dev = []
    for option in CONF_SENSOR_LIST:
        dev.append(HeweatherWeatherSensor(weather_data,suggestion_data, option,location))
    async_add_devices(dev, True)


class HeweatherWeatherSensor(Entity):
    """定义一个温度传感器的类，继承自HomeAssistant的Entity类."""

    def __init__(self, weather_data,suggestion_data, option,location):
        """初始化."""
        self._weather_data = weather_data
        self._suggestion_data = suggestion_data
        self._object_id = OPTIONS[option][0]
        self._name = OPTIONS[option][1]
        self._icon = OPTIONS[option][2]
        self._unit_of_measurement = OPTIONS[option][3]

        self._type = option
        self._state = None
        self._attributes = {"states":"null"}
        self._updatetime = None
        self._attr_unique_id = OPTIONS[option][0] + location

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        return self._attributes

    @property
    def name(self):
        """返回实体的名字."""
        return self._name

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
        elif self._type == "pm25":
            self._state = self._weather_data.pm25
        elif self._type == "no2":
            self._state = self._weather_data.no2
        elif self._type == "so2":
            self._state = self._weather_data.so2
        elif self._type == "co":
            self._state = self._weather_data.co
        elif self._type == "o3":
            self._state = self._weather_data.o3
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

class WeatherData(object):
    """天气相关的数据，存储在这个类中."""

    def __init__(self, hass, location, key, disastermsg, disasterlevel):
        """初始化函数."""
        self._hass = hass
        self._disastermsg = disastermsg
        self._disasterlevel = disasterlevel
        #disastermsg, disasterlevel

       # self._url = "https://free-api.heweather.com/s6/weather/now"
        self._weather_now_url = "https://devapi.qweather.com/v7/weather/now?location="+location+"&key="+key
        self._air_now_url = "https://devapi.qweather.com/v7/air/now?location="+location+"&key="+key
        self._disaster_warn_url = "https://devapi.qweather.com/v7/warning/now?location="+location+"&key="+key
        self._params = {"location": location,
                        "key": key}
        self._temprature = None
        self._humidity = None


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



        self._pm25 = None
        self._no2 = None
        self._so2 = None
        self._co = None
        self._o3 = None
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
    def pm25(self):
        """pm2.5"""
        return self._pm25

    @property
    def pm10(self):
        """pm10"""
        return self._pm10

    @property
    def qlty(self):
        """(aqi)空气质量指数"""
        return self._qlty

    @property
    def no2(self):
        """no2"""
        return self._no2

    @property
    def co(self):
        """co"""
        return self._co

    @property
    def so2(self):
        """so2"""
        return self._so2

    @property
    def o3(self):
        """o3"""
        return self._o3

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
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(self._weather_now_url) as response:
                    json_data = await response.json()
                    weather = json_data["now"]
                async with session.get(self._air_now_url) as response:
                    json_data = await response.json()
                    air = json_data["now"]
                async with session.get(self._disaster_warn_url) as response:
                    json_data = await response.json()
                    disaster_warn = json_data["warning"]


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
        self._category = air["category"]
        self._pm25 = air["pm2p5"]
        self._pm10 = air["pm10"]
        self._primary = air["primary"]
        self._level = air["level"]
        self._no2 = air["no2"]
        self._so2 = air["so2"]
        self._co = air["co"]
        self._o3 = air["o3"]
        self._qlty = air["aqi"]


        allmsg=''
        titlemsg=''
        for i in disaster_warn:
            #if DISASTER_LEVEL[i["severity"]] >= 订阅等级:
            if (DISASTER_LEVEL[i["severity"]] >= int(self._disasterlevel)):
                allmsg = allmsg +i["title"] + ':' + i["text"] + '||'
                titlemsg = titlemsg + i["title"] + '||'

        if(len(titlemsg)<5):
            self._disaster_warn =  '近日无'+ self._disasterlevel +'级及以上灾害'
        #if(订阅标题)
        elif(self._disastermsg=='title'):
            self._disaster_warn =  titlemsg
        else:
            self._disaster_warn =  allmsg

class SuggestionData(object):
    """天气相关建议的数据，存储在这个类中."""

    def __init__(self, hass, location, key):
        """初始化函数."""
        self._hass = hass

        self._url = "https://devapi.qweather.com/v7/indices/1d?location="+location+"&key="+key+"&type=0"
        self._params = {"location": location,
                        "key": key,
                        "type": 0
                    }

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
            with async_timeout.timeout(15):
            #with async_timeout.timeout(15, loop=self._hass.loop):
                response = await session.get(
                    self._url)

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
