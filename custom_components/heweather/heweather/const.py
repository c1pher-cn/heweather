DOMAIN: str = 'heweather'
DEFAULT_NAME: str = '和风天气'

# config platform
CONF_AUTH_METHOD = "auth_method"
CONF_OPTIONS = "options"
CONF_LONGITUDE = "longitude"
CONF_LATITUDE = "latitude"
CONF_HOST = "host"
CONF_KEY = "key"
CONF_STORAGE_PATH = "storage_path"
CONF_JWT_SUB = "auth_jwt_sub"
CONF_JWT_KID = "auth_jwt_kid"

DEFAULT_HOST = "devapi.qweather.com"

CONF_DISASTERLEVEL = "disasterlevel"
CONF_DISASTERMSG = "disastermsg"
CONF_SENSOR_LIST = ["air","comf","cw","drsg","flu","sport","trav","uv","sunglass","guomin","liangshai","jiaotong","fangshai","kongtiao","disaster_warn","temprature","humidity","category","feelsLike","text","windDir","windScale","windSpeed","pressure","vis","cloud","dew","precip","qlty","level","primary","pm2p5","pm10","co","so2","no2","o3"]

# config flow
DEFAULT_AUTH_METHOD: str = "key"
AUTH_METHOD: dict = {
    "key": "API KEY",
    "jwt": "JSON Web Token (Alpha)"
}

DEFAULT_DISASTER_MSG: str = "allmsg"
DISASTER_MSG: dict = {
    "title": "仅标题",
    "allmsg": "所有信息"
}

DEFAULT_DISASTER_LEVEL_CONF: str = "3"
DISASTER_LEVEL_CONF: dict = {
    "1": "标准的",
    "2": "次要的",
    "3": "中等的",
    "4": "主要",
    "5": "严重",
    "6": "极端"
}


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

DISASTER_LEVEL = {
    "cancel":0,
    "none":0,
    "unknown":0,
    "standard":1,
    "minor":2,
    "moderate":3,
    "major":4,
    "severe":5,
    "extreme":6,
    "white":0,
    "blue":1,
    "green":2,
    "yellow":3,
    "orange":4,
    "red":5,
    "black":6
}

ATTR_UPDATE_TIME = "更新时间"
ATTR_SUGGESTION = "建议"
ATTRIBUTION = "来自和风天气的天气数据"

CERT_NAME_PREFIX = "heweather_ed25519_"
