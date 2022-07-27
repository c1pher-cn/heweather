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
    ATTR_ATTRIBUTION)
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util


_LOGGER = logging.getLogger(__name__)

TIME_BETWEEN_UPDATES = timedelta(seconds=3600)

CONF_OPTIONS = "options"
CONF_LOCATION = "location"
CONF_KEY = "key"

# 定义多个建议选项
OPTIONS = {
    "air": ["suggestion_air", "空气质量", "mdi:air-conditioner"],
    "comf": ["suggestion_comf", "体感", "mdi:human-greeting"],
    "cw": ["suggestion_cw", "洗车建议", "mdi:car"],
    "drsg": ["suggestion_drsg", "衣着建议", "mdi:hanger"],
    "flu": ["suggestion_flu", "感冒概率", "mdi:biohazard"],
    "sport": ["suggestion_sport", "运动建议", "mdi:badminton"],
    "trav": ["suggestion_trav", "旅行建议", "mdi:wallet-travel"],
    "uv": ["suggestion_uv", "紫外线建议", "mdi:weather-sun-wireless"],
    "guomin": ["suggestion_guomin", "过敏建议", "mdi:sunglasses"],
    "kongtiao": ["suggestion_kongtiao", "空调建议", "mdi:air-conditioner"],
    "sunglass": ["suggestion_sunglass", "太阳镜建议", "mdi:sunglasses"],
    "fangshai": ["suggestion_fangshai", "防晒建议", "mdi:sun-protection-outline"],
    "liangshai": ["suggestion_liangshai", "晾晒建议", "mdi:wb-sunny"],

}

ATTR_UPDATE_TIME = "更新时间"
ATTR_SUGGESTION = "建议"
ATTRIBUTION = "来自和风天气的天气数据"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_LOCATION): cv.string,
    vol.Required(CONF_KEY): cv.string,
    vol.Required(CONF_OPTIONS,
                 default=[]): vol.All(cv.ensure_list, [vol.In(OPTIONS)]),
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """这个协程是程序的入口，其中add_devices函数也变成了异步版本."""
    _LOGGER.info("setup platform sensor.Heweather...")

    location = config.get(CONF_LOCATION)
    key = config.get(CONF_KEY)
    # 这里通过 data 实例化class SuggestionData，并传入调用API所需信息
    data = SuggestionData(hass, location, key)  
    # 调用data实例中的异步更新函数，yield 现在我简单的理解为将后面函数变成一个生成器，减小内存占用？
    yield from data.async_update(dt_util.now()) 
    async_track_time_interval(hass, data.async_update, TIME_BETWEEN_UPDATES)

    # 根据配置文件options中的内容，添加若干个设备
    dev = []
    for option in config[CONF_OPTIONS]:
        dev.append(LifeSuggestion(data, option))
    async_add_devices(dev, True)


class LifeSuggestion(Entity):
    """定义一个温度传感器的类，继承自HomeAssistant的Entity类."""

    def __init__(self, data, option):
        """初始化."""
        self._data = data
        self._object_id = OPTIONS[option][0]
        self._friendly_name = OPTIONS[option][1]
        self._icon = OPTIONS[option][2]

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
    def device_state_attributes(self):
        """设置其它一些属性值."""
        if self._state is not None:
            sgt = ''
            if self._type == "air":
                sgt = self._data.air[1]
            elif self._type == "comf":
                sgt = self._data.comf[1]
            elif self._type == "cw":
                sgt = self._data.cw[1]
            elif self._type == "drsg":
                sgt = self._data.drsg[1]
            elif self._type == "flu":
                sgt = self._data.flu[1]
            elif self._type == "sport":
                sgt = self._data.sport[1]
            elif self._type == "trav":
                sgt = self._data.trav[1]
            elif self._type == "uv":
                sgt = self._data.uv[1]
            elif self._type == "guomin":
                sgt = self._data.guomin[1]
            elif self._type == "kongtiao":
                sgt = self._data.kongtiao[1]
            elif self._type == "sunglass":
                sgt = self._data.sunglass[1]
            elif self._type == "liangshai":
                sgt = self._data.liangshai[1]
            elif self._type == "fangshai":
                sgt = self._data.fangshai[1]
            return {
                ATTR_ATTRIBUTION: ATTRIBUTION,
                ATTR_UPDATE_TIME: self._updatetime,
                ATTR_SUGGESTION: "{}".format(sgt)
            }

    @asyncio.coroutine
    def async_update(self):
        """update函数变成了async_update."""
        self._updatetime = self._data.updatetime

        if self._type == "air":
            self._state = self._data.air[0]
        elif self._type == "comf":
            self._state = self._data.comf[0]
        elif self._type == "cw":
            self._state = self._data.cw[0]
        elif self._type == "drsg":
            self._state = self._data.drsg[0]
        elif self._type == "flu":
            self._state = self._data.flu[0]
        elif self._type == "sport":
            self._state = self._data.sport[0]
        elif self._type == "trav":
            self._state = self._data.trav[0]
        elif self._type == "uv":
            self._state = self._data.uv[0]
        elif self._type == "guomin":
            self._state = self._data.guomin[0]
        elif self._type == "kongtiao":
            self._state = self._data.kongtiao[0]
        elif self._type == "liangshai":
            self._state = self._data.liangshai[0]
        elif self._type == "fangshai":
            self._state = self._data.fangshai[0]
        elif self._type == "sunglass":
            self._state = self._data.uv[0]


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

    @property
    def updatetime(self):
        """更新时间."""
        return self._updatetime

    @property
    def air(self):
        """通风建议."""
        return self._air
    
    @property
    def comf(self):
        """人体舒适度建议"""
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

    @asyncio.coroutine
    def async_update(self, now):
        """从远程更新信息."""
        try:
            session = async_get_clientsession(self._hass)
            with async_timeout.timeout(15):
            #with async_timeout.timeout(15, loop=self._hass.loop):
                response = yield from session.get(
                    self._url)

        except(asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Error while accessing: %s", self._url)
            return

        if response.status != 200:
            _LOGGER.error("Error while accessing: %s, status=%d",
                          self._url,
                          response.status)
            return

        result = yield from response.json()

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

            if i["type"] == "16":
                self._fangshai = [i["category"], i["text"]]
