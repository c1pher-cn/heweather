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
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util


_LOGGER = logging.getLogger(__name__)

TIME_BETWEEN_UPDATES = timedelta(seconds=1800)

CONF_OPTIONS = "options"
CONF_LOCATION = "location"
CONF_KEY = "key"

CONDITION_CLASSES = {
    'sunny': ["晴"],
    'cloudy': ["多云"],
    'partlycloudy': ["少云", "晴间多云", "阴"],
    'windy': ["有风", "微风", "和风", "清风"],
    'windy-variant': ["强风", "疾风", "大风", "烈风"],
    'hurricane': ["飓风", "龙卷风", "热带风暴", "狂暴风", "风暴"],
    'rainy': ["毛毛雨", "小雨", "中雨", "大雨", "极端降雨"],
    'pouring': ["暴雨", "大暴雨", "特大暴雨", "阵雨", "强阵雨"],
    'lightning-rainy': ["雷阵雨", "强雷阵雨"],
    'fog': ["雾", "薄雾"],
    'hail': ["雷阵雨伴有冰雹"],
    'snowy': ["小雪", "中雪", "大雪", "暴雪", "阵雪"],
    'snowy-rainy': ["雨夹雪", "雨雪天气", "阵雨夹雪"],
}


OPTIONS = {
    "remind": ["remind", "不良天气提醒"],
    "1hour": ["hourly_forcast_1", "未来1小时"],
    "3hour": ["hourly_forcast_3", "未来3小时"],
    "6hour": ["hourly_forcast_6", "未来6小时"],
    "9hour": ["hourly_forcast_9", "未来9小时"],
    "12hour": ["hourly_forcast_12", "未来12小时"],
    "15hour": ["hourly_forcast_15", "未来15小时"],
    "18hour": ["hourly_forcast_18", "未来18小时"],
    "21hour": ["hourly_forcast_21", "未来21小时"],
    "24hour": ["hourly_forcast_24", "未来一天"],
}

ATTR_UPDATE_TIME = "更新时间"
ATTRIBUTION = "来自和风天气的天气数据"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_LOCATION): cv.string,
    vol.Required(CONF_KEY): cv.string,
    vol.Required(CONF_OPTIONS,
                 default=[]): vol.All(cv.ensure_list, [vol.In(OPTIONS)]),
})


#@asyncio.coroutine
async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """这个协程是程序的入口，其中add_devices函数也变成了异步版本."""
    _LOGGER.info("setup platform sensor.Heweather...")

    location = config.get(CONF_LOCATION)
    key = config.get(CONF_KEY)
    # 这里通过 data 实例化class weatherdata，并传入调用API所需信息
    data = WeatherData(hass, location, key)  
    # 调用data实例中的异步更新函数，yield 现在我简单的理解为将后面函数变成一个生成器，减小内存占用？
    #yield from 
    await data.async_update(dt_util.now()) 
    async_track_time_interval(hass, data.async_update, TIME_BETWEEN_UPDATES)

    # 根据配置文件options中的内容，添加若干个设备
    dev = []
    for option in config[CONF_OPTIONS]:
        dev.append(HeweatherWeatherSensor(data,option,location))
    async_add_devices(dev, True)


class HeweatherWeatherSensor(Entity):
    """定义一个温度传感器的类，继承自HomeAssistant的Entity类."""

    def __init__(self,data,option,location):
        """初始化."""
        self._data = data
        self._object_id = OPTIONS[option][0]
        self._friendly_name = OPTIONS[option][1]
        self._icon = 'mdi:weather-'+'sunny'

        self._type = option
        self._state = None
        self._updatetime = None
        self._attr_unique_id = OPTIONS[option][0] + location

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
        self._updatetime = self._data.updatetime

        if self._type == "1hour":
            self._state = self._data.hour_1[1]+' '+self._data.hour_1[2]+'℃ '+self._data.hour_1[4]+' '+ self._data.hour_1[5] + '级'
            
            for i, j in CONDITION_CLASSES.items():
                if self._data.hour_1[1] in j:
                    self._icon = 'mdi:weather-'+i

        elif self._type == "3hour":
            self._state = self._data.hour_3[1]+' '+self._data.hour_3[2]+'℃ '+self._data.hour_3[4]+' '+ self._data.hour_3[5] + '级'
            
            for i, j in CONDITION_CLASSES.items():
                if self._data.hour_3[1] in j:
                    self._icon = 'mdi:weather-'+i

        elif self._type == "6hour":
            self._state = self._data.hour_6[1]+' '+self._data.hour_6[2]+'℃ '+self._data.hour_6[4]+' '+ self._data.hour_6[5] + '级'

            for i, j in CONDITION_CLASSES.items():
                if self._data.hour_6[1] in j:
                    self._icon = 'mdi:weather-'+i

        elif self._type == "9hour":
            self._state = self._data.hour_9[1]+' '+self._data.hour_9[2]+'℃ '+self._data.hour_9[4]+' '+ self._data.hour_9[5] + '级'

            for i, j in CONDITION_CLASSES.items():
                if self._data.hour_9[1] in j:
                    self._icon = 'mdi:weather-'+i

        elif self._type == "12hour":
            self._state = self._data.hour_12[1]+' '+self._data.hour_12[2]+'℃ '+self._data.hour_12[4]+' '+ self._data.hour_12[5] + '级'

            for i, j in CONDITION_CLASSES.items():
                if self._data.hour_12[1] in j:
                    self._icon = 'mdi:weather-'+i

        elif self._type == "15hour":
            self._state = self._data.hour_15[1]+' '+self._data.hour_15[2]+'℃  '+self._data.hour_15[4]+' '+ self._data.hour_15[5] + '级'

            for i, j in CONDITION_CLASSES.items():
                if self._data.hour_15[1] in j:
                    self._icon = 'mdi:weather-'+i

        elif self._type == "18hour":
            self._state = self._data.hour_18[1]+' '+self._data.hour_18[2]+'℃  '+self._data.hour_18[4]+' '+ self._data.hour_18[5] + '级'

            for i, j in CONDITION_CLASSES.items():
                if self._data.hour_18[1] in j:
                    self._icon = 'mdi:weather-'+i

        elif self._type == "21hour":
            self._state = self._data.hour_21[1]+' '+self._data.hour_21[2]+'℃  '+self._data.hour_21[4]+' '+ self._data.hour_21[5] + '级'

            for i, j in CONDITION_CLASSES.items():
                if self._data.hour_21[1] in j:
                    self._icon = 'mdi:weather-'+i

        elif self._type == "24hour":
            self._state = self._data.hour_24[1]+' '+self._data.hour_24[2]+'℃  '+self._data.hour_24[4]+' '+ self._data.hour_24[5] + '级'

            for i, j in CONDITION_CLASSES.items():
                if self._data.hour_24[1] in j:
                    self._icon = 'mdi:weather-'+i

        elif self._type == "remind":
            for i, j in CONDITION_CLASSES.items():
                if self._data.hour_1[1] in j:
                    if i not in ['sunny','cloudy','partlycloudy','windy']:
                        self._state = self._data.hour_1[0]+'降雨概率为'+self._data.hour_1[2]+'%'+'可能'+self._data.hour_1[1]+'请多加注意'
                    else:
                        self._state = '未来1小时内无不良天气'
                    self._icon = 'mdi:weather-'+i



class WeatherData(object):
    """天气相关的数据，存储在这个类中."""

    def __init__(self, hass, location, key):
        """初始化函数."""
        self._hass = hass
        self._url = "https://devapi.qweather.com/v7/weather/24h?location="+location+"&key="+key
        self._params = {"location": location,
                        "key": key}
        self._hour_1 = None
        self._hour_3 = None
        self._hour_6 = None
        self._hour_9 = None
        self._hour_12 = None
        self._hour_15 = None
        self._hour_18 = None
        self._hour_21 = None
        self._hour_24 = None
        self._updatetime = None

    @property
    def hour_1(self):
        """1小时预报"""
        return self._hour_1
    
    @property
    def hour_3(self):
        """3小时预报"""
        return self._hour_3

    @property
    def hour_6(self):
        """湿度."""
        return self._hour_6

    @property
    def hour_9(self):
        """pm2.5."""
        return self._hour_9

    @property
    def hour_12(self):
        """hour_12."""
        return self._hour_12
    
    @property
    def hour_15(self):
        """hour_15."""
        return self._hour_15
    
    @property
    def hour_18(self):
        """hour_18."""
        return self._hour_18

    @property
    def hour_21(self):
        """hour_21."""
        return self._hour_21

    @property
    def hour_24(self):
        """hour_21."""
        return self._hour_24

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
            session = async_get_clientsession(self._hass)
            with async_timeout.timeout(15):
            #with async_timeout.timeout(15, loop=self._hass.loop):
                #response = yield from session.get(self._url)
                response = await session.get(self._url)

        except(asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Error while accessing: %s", self._url)
            return

        if response.status != 200:
            _LOGGER.error("Error while accessing: %s, status=%d",
                          self._url,
                          response.status)
            return

        #result = yield from response.json()
        result = await response.json()
        
        if result is None:
            _LOGGER.error("Request api Error")
            return
        elif result["code"] != "200":
            _LOGGER.error("Error API return, code=%s, msg=%s",
                          result["code"],
                          result["msg"])
            return

        # 根据http返回的结果，更新数据
        hourlymsg = result["hourly"]
        self._hour_1 = [hourlymsg[0]["fxTime"][-11:-6], hourlymsg[0]["text"], hourlymsg[0]["temp"], hourlymsg[0]["pop"], hourlymsg[0]["windDir"], hourlymsg[0]["windScale"]]
        self._hour_3 = [hourlymsg[2]["fxTime"][-11:-6], hourlymsg[2]["text"], hourlymsg[2]["temp"], hourlymsg[2]["pop"], hourlymsg[2]["windDir"], hourlymsg[2]["windScale"]]
        self._hour_6 = [hourlymsg[5]["fxTime"][-11:-6], hourlymsg[5]["text"], hourlymsg[5]["temp"], hourlymsg[5]["pop"], hourlymsg[5]["windDir"], hourlymsg[5]["windScale"]]
        self._hour_9 = [hourlymsg[8]["fxTime"][-11:-6], hourlymsg[8]["text"], hourlymsg[8]["temp"], hourlymsg[8]["pop"], hourlymsg[8]["windDir"], hourlymsg[8]["windScale"]]
        self._hour_12 = [hourlymsg[11]["fxTime"][-5:], hourlymsg[11]["text"], hourlymsg[11]["temp"], hourlymsg[11]["pop"], hourlymsg[11]["windDir"], hourlymsg[11]["windScale"]]
        self._hour_15 = [hourlymsg[14]["fxTime"][-5:], hourlymsg[14]["text"], hourlymsg[14]["temp"], hourlymsg[14]["pop"], hourlymsg[14]["windDir"], hourlymsg[14]["windScale"]]
        self._hour_18 = [hourlymsg[17]["fxTime"][-5:], hourlymsg[17]["text"], hourlymsg[17]["temp"], hourlymsg[17]["pop"], hourlymsg[17]["windDir"], hourlymsg[17]["windScale"]]
        self._hour_21 = [hourlymsg[20]["fxTime"][-5:], hourlymsg[20]["text"], hourlymsg[20]["temp"], hourlymsg[20]["pop"], hourlymsg[20]["windDir"], hourlymsg[20]["windScale"]]
        self._hour_24 = [hourlymsg[23]["fxTime"][-5:], hourlymsg[23]["text"], hourlymsg[23]["temp"], hourlymsg[23]["pop"], hourlymsg[23]["windDir"], hourlymsg[23]["windScale"]]
        self._updatetime = result["updateTime"]
