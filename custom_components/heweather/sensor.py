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
    ATTR_ATTRIBUTION, ATTR_FRIENDLY_NAME, TEMP_CELSIUS)
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util


_LOGGER = logging.getLogger(__name__)

TIME_BETWEEN_UPDATES = timedelta(seconds=600)

CONF_OPTIONS = "options"
CONF_LOCATION = "location"
CONF_KEY = "key"
CONF_DISASTERLEVEL = "disasterlevel"
CONF_DISASTERMSG = "disastermsg"

# 定义三个可选项：温度、湿度、PM2.5
OPTIONS = {
    "temprature": ["Heweather_temperature", "室外温度", "mdi:thermometer", TEMP_CELSIUS],
    "humidity": ["Heweather_humidity", "室外湿度", "mdi:water-percent", "%"],
    "feelsLike": ["Heweather_feelsLike", "体感温度", "mdi:thermometer", TEMP_CELSIUS],
    "text": ["Heweather_text", "天气描述", "mdi:thermometer", ' '],
    "precip": ["Heweather_precip", "小时降水量", "mdi:thermometer", '毫米'],
    "windDir": ["Heweather_windDir", "风向", "mdi:thermometer", ' '],
    "windScale": ["Heweather_windScale", "风力等级", "mdi:thermometer", ' '],
    "windSpeed": ["Heweather_windSpeed", "风速", "mdi:thermometer", '公里/小时'],

    
    "dew": ["Heweather_dew", "露点温度", "mdi:thermometer", ' '],
    "pressure": ["Heweather_pressure", "大气压强", "mdi:thermometer", '百帕'],
    "vis": ["Heweather_vis", "能见度", "mdi:thermometer", 'km'],
    "cloud": ["Heweather_cloud", "云量", "mdi:thermometer", ' '],
    
    
    
    "primary": ["Heweather_primary", "空空气质量的主要污染物", "mdi:walk", " "],
    "category": ["Heweather_category", "空气质量指数级别", "mdi:walk", " "],
    "level": ["Heweather_level", "空气质量指数等级", "mdi:walk", " "],
    "pm25": ["Heweather_pm25", "PM2.5", "mdi:walk", "μg/m3"],
    "pm10": ["Heweather_pm10", "PM10", "mdi:walk", "μg/m3"],
    
    
    "no2": ["Heweather_no2", "二氧化氮", "mdi:emoticon-dead", "μg/m3"],
    "so2": ["Heweather_so2", "二氧化硫", "mdi:emoticon-dead", "μg/m3"],
    "co": ["Heweather_co", "一氧化碳", "mdi:emoticon-dead", "μg/m3"],
    "o3": ["Heweather_o3", "臭氧", "mdi:weather-cloudy", "μg/m3"],
    "qlty": ["Heweather_qlty", "综合空气质量", "mdi:quality-high", " "],
    "disaster_warn": ["Heweather_disaster_warn", "灾害预警", "mdi:warning-outline", " "],

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
ATTRIBUTION = "来自和风天气的天气数据"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_LOCATION): cv.string,
    vol.Required(CONF_KEY): cv.string,
    vol.Required(CONF_DISASTERLEVEL): cv.string,
    vol.Required(CONF_DISASTERMSG): cv.string,
    vol.Required(CONF_OPTIONS,
                 default=[]): vol.All(cv.ensure_list, [vol.In(OPTIONS)]),
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """这个协程是程序的入口，其中add_devices函数也变成了异步版本."""
    _LOGGER.info("setup platform sensor.Heweather...")

    location = config.get(CONF_LOCATION)
    key = config.get(CONF_KEY)
    disastermsg = config.get(CONF_DISASTERMSG)
    disasterlevel = config.get(CONF_DISASTERLEVEL)
    # 这里通过 data 实例化class weatherdata，并传入调用API所需信息
    data = WeatherData(hass, location, key, disastermsg, disasterlevel)  
    # 调用data实例中的异步更新函数，yield 现在我简单的理解为将后面函数变成一个生成器，减小内存占用？
    yield from data.async_update(dt_util.now()) 
    async_track_time_interval(hass, data.async_update, TIME_BETWEEN_UPDATES)

    # 根据配置文件options中的内容，添加若干个设备
    dev = []
    for option in config[CONF_OPTIONS]:
        dev.append(HeweatherWeatherSensor(data, option))
    async_add_devices(dev, True)


class HeweatherWeatherSensor(Entity):
    """定义一个温度传感器的类，继承自HomeAssistant的Entity类."""

    def __init__(self, data, option):
        """初始化."""
        self._data = data
        self._object_id = OPTIONS[option][0]
        self._friendly_name = OPTIONS[option][1]
        self._icon = OPTIONS[option][2]
        self._unit_of_measurement = OPTIONS[option][3]

        self._type = option
        self._state = None
        self._updatetime = None

    @property
    def name(self):
        """返回实体的名字."""
        return self._object_id

    @property
    def registry_name(self):
        """返回实体的friendly_name属性."""
        return self._friendly_name

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

    @asyncio.coroutine
    def async_update(self):
        """update函数变成了async_update."""
        self._updatetime = self._data.updatetime

        if self._type == "temprature":
            self._state = self._data.temprature
        elif self._type == "humidity":
            self._state = self._data.humidity

        elif self._type == "feelsLike":
            self._state = self._data.feelsLike
        elif self._type == "text":
            self._state = self._data.text
        elif self._type == "windDir":
            self._state = self._data.windDir
        elif self._type == "windScale":
            self._state = self._data.windScale
        elif self._type == "windSpeed":
            self._state = self._data.windSpeed
        elif self._type == "precip":
            self._state = self._data.precip
            
        elif self._type == "category":
            self._state = self._data.category
        elif self._type == "primary":
            self._state = self._data.primary
        elif self._type == "level":
            self._state = self._data.level
        elif self._type == "pm10":
            self._state = self._data.pm10
        

        elif self._type == "pm25":
            self._state = self._data.pm25
        elif self._type == "no2":
            self._state = self._data.no2
        elif self._type == "so2":
            self._state = self._data.so2
        elif self._type == "co":
            self._state = self._data.co
        elif self._type == "o3":
            self._state = self._data.o3
        elif self._type == "qlty":
            self._state = self._data.qlty
        elif self._type == "disaster_warn":
            self._state = self._data.disaster_warn



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

    @asyncio.coroutine
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
        yield from asyncio.sleep(40)
        _LOGGER.info("after yield from asyncio.sleep")
        """

        # 通过HTTP访问，获取需要的信息
        # 此处使用了基于aiohttp库的async_get_clientsession
        try:
            timeout = aiohttp.ClientTimeout(total=10)  
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

        #result = yield from response.json()

        #if result is None:
        #    _LOGGER.error("Request api Error")
        #    return
        #elif result["code"] != "200":
        #    _LOGGER.error("Error API return, code=%s, msg=%s",
        #                  result["code"],
        #                  self._url)
        #    return

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
