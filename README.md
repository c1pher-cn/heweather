
![GitHub Repo stars](https://img.shields.io/github/stars/c1pher-cn/heweather?style=for-the-badge&label=Stars&color=green)
![GitHub forks](https://img.shields.io/github/forks/c1pher-cn/heweather?style=for-the-badge&label=Forks&color=green)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/c1pher-cn/heweather?style=for-the-badge&color=green)
![GitHub release (latest by date)](https://img.shields.io/github/downloads/c1pher-cn/heweather/latest/total?style=for-the-badge&color=green)



# 和风天气 homeassistant插件

  
  如果觉得对你有帮助，就来b站支持一波吧：[_小愚_](https://space.bilibili.com/15856864)

## 使用说明：

1.使用和风官方apiv7版本

2.必须申请开发者账号里的免费api，请务必升级到开发者账号（免费，api权限会比普通用户高一些）https://console.qweather.com/#/console

3.appkey申请需要先[创建项目](https://console.qweather.com/project?lang=zh),后选创建凭据，选API KEY即可

    国内的城市区域location关系：https://github.com/qwd/LocationList/blob/master/China-City-List-latest.csv
    
4.在和风控制台的设置页面查看自己分配的API host：https://console.qweather.com/setting?lang=zh

5.新版本整合优化了sensor以及相关中文名字，图标。将原有的24小时天天气预报从sensor中转移到weather里



## 配置方法
### 建议使用webui的配置流程
  依照流程配置即可，不了解的参数参考下面手工配置说明来获取/配置
### 手工配置和参数说明
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
sensor里的其他两个参数：

  disasterlevel：表示关注的自然灾害等级，1-6为从轻微到严重
  
  配置3表示关注 >=3级的灾害，下为不同等级的英文描述
```
  Standard           1  最轻微
  Minor              2
  Moderate           3  
  Major              4
  Severe             5
  Extreme            6  最严重
```
    
  disastermsg：表示灾害预警是否显示灾害的明细信息
    
    title  只显示标题
    
    allmsg 显示标题+明细信息
    


## 自动化配置实例

https://www.bilibili.com/read/cv18078640

