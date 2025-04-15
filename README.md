# 和风天气 homeassistant插件

  我使用的插件最早引用自[瀚思彼岸智能家居技术论坛](https://bbs.hassbian.com/) Golden_Soap大佬的[插件](https://bbs.hassbian.com/thread-3971-1-1.html),但该插件很久没有更新过配置，导致我的环境一直无法运行，自己肝的原因主要是懒得改之前的参数配置，换插件全得改一遍，有的数据还没了，又正好借着这个机会能再学习下插件的逻辑，哈哈哈。
  
  如果觉得对你有帮助，就来b站支持一波吧：[_小愚_](https://space.bilibili.com/15856864)

## 使用说明：

1.使用和风官方apiv7版本

2.必须申请开发者账号里的免费api，请务必升级到开发者账号（免费，api权限会比普通用户高一些）https://console.qweather.com/#/console

3.appkey申请需要先[创建项目](https://console.qweather.com/project?lang=zh),后选创建凭据，选API KEY即可

    国内的城市区域location关系：https://github.com/qwd/LocationList/blob/master/China-City-List-latest.csv

4.新版本整合优化了sensor以及相关中文名字，图标。将原有的24小时天天气预报从sensor中转移到weather里



## 配置方法

1.天气预报，默认支持7天和24小时预报，放在weather里，

```
weather:
  - platform: heweather
    location: 101210106        # 填写你所在区域代码Location_ID,https://github.com/qwd/LocationList/blob/master/China-City-List-latest.csv
    host: devapi.qweather.com  # 开发者信息中的API Host
    key: ABCDE                 # api平台申请的key
```   
         
2.天气情况、空气质量、自然灾害预警、各种生活指数，放在sensor里

```
sensor:
  - platform: heweather
    location: 101210106        # 填写你所在区域代码Location_ID,https://github.com/qwd/LocationList/blob/master/China-City-List-latest.csv
    host: devapi.qweather.com  # 开发者信息中的API Host
    key: ABCDE                 # api平台申请的key
    disasterlevel: 3
    disastermsg: allmsg
 ```    
两个参数：

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
    


## 自动化配置实例

https://www.bilibili.com/read/cv18078640

