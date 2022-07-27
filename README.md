# heweather  alert-outline
和风天气 homeassistant插件

我使用的插件最早引用自[瀚思彼岸智能家居技术论坛](https://bbs.hassbian.com/) Golden_Soap大佬的[插件](https://bbs.hassbian.com/thread-3971-1-1.html),但大佬一直没有更新过配置，导致我的环境一直无法运行，正好借着这个机会再学习一边插件，哈哈哈
自己肝的原因主要是懒得改之前的参数配置，换插件全得改一遍，有的数据还没了。如果对你有帮助，就来b站支持一波吧[_小愚_](https://space.bilibili.com/15856864)嘿嘿

## 主要修改点：

1.从原来的京东万象平台，升级到了和风官方apiv7版本（京东平台的账号我找不到了，所以就索性替换到了和风官方api，和风v6版本api已经停止维护并计划在2022年底下线）

2.我是用的是开发者账号里的免费api，请务必升级到开发者账号（免费，但要提交身份证审核，api权限会比普通用户高一些）https://console.qweather.com/#/console

3.appkey申请需要先[创建应用](https://console.qweather.com/#/apps),后选添加数据key，选wabapi即可

4.原本的文件结构、参数变量基本未做改变，主要包括当前天气，当前空气质量，小时天气预报，七日天气预报，生活指数建议，在此基础上增加了极端天气预警（sensor.heweather_disaster_warn）


## 配置方法

1.heweather_forecast(七日天气预报)
```
  - platform: heweather_forecast
    location: 101210106    # 城市区域代码，api平台有查询接口查询
    key: ABCDE             # api平台申请的key
```   
    
2.lifesuggestion(生活指数建议)    
```
  - platform: lifesuggestion
    location: 101210106    # 城市区域代码，api平台有查询接口查询
    key: ABCDE             # api平台申请的key
    options:
      - air
      - comf
      - cw
      - drsg
      - flu
      - sport
      - trav
      - uv
      - sunglass
      - guomin
      - liangshai
      - fangshai
      - kongtiao
```      
      
3.heweather（天气情况、空气质量、自然灾害预警）

  disasterlevel的数字表示关注的自然灾害等级，配置3表示关注 >=3级的灾害
  
    Standard    标准的   1
    Minor       次要的   2
    Moderate    中等的   3
    Major       主要     4
    Severe      严重     5
    Extreme     极端     6

  disastermsg表示灾害预警是否显示灾害的明细信息
  
    title  只显示标题
    allmsg 显示标题+明细信息
    
```
  - platform: heweather
    location: 101210106     # 城市区域代码，api平台有查询接口查询
    key: ABCDE              # api平台申请的key
    disasterlevel: 3
    disastermsg: allmsg
    options:
      - disaster_warn
      - temprature
      - humidity
      - category
      - feelsLike
      - text
      - windDir
      - windScale
      - windSpeed
      - pressure
      - vis
      - cloud
      - dew
      - precip
      - qlty
      - level
      - primary
      - pm25
      - pm10
      - co
      - so2
      - no2
      - o3
 ```    
      
4.heweather_hourlyforecast（小时天气预报、1小时天气预警）
```
  - platform: heweather_hourlyforecast
    location: 101210106    # 城市代码，api平台有查询接口查询
    key: ABCDE             # api平台申请的key
    options:
      - remind
      - 1hour
      - 3hour
      - 6hour
      - 9hour
```




