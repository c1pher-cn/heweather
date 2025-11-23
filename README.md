
![GitHub Repo stars](https://img.shields.io/github/stars/c1pher-cn/heweather?style=for-the-badge&label=Stars&color=green)
![GitHub forks](https://img.shields.io/github/forks/c1pher-cn/heweather?style=for-the-badge&label=Forks&color=green)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/c1pher-cn/heweather?style=for-the-badge&color=green)
![GitHub release (latest by date)](https://img.shields.io/github/downloads/c1pher-cn/heweather/total?style=for-the-badge&color=green)
![GitHub release (latest by date)](https://img.shields.io/github/downloads/c1pher-cn/heweather/latest/total?style=for-the-badge&color=green)



# 和风天气 homeassistant插件

  
  如果觉得对你有帮助，就来b站支持一波吧：[_小愚_](https://space.bilibili.com/15856864)

## 配置说明：

1.使用和风官方最新api版本

2.必须申请开发者账号里的免费api，请务必升级到开发者账号（免费，api权限会比普通用户高一些）https://console.qweather.com/#/console

3.appkey申请需要先[创建项目](https://console.qweather.com/project?lang=zh),后选创建凭据，建议选择 JSON Web Token (JWT) ,公钥见第5步

4.在HACS商店中搜索heweather,找到本插件并下载
<img width="1671" height="299" alt="image" src="https://github.com/user-attachments/assets/45aa3754-4c9b-411e-b168-603835d58b9a" />

5.设置->设备与服务->添加集成->搜索heweather->选择本插件
<img width="581" height="350" alt="image" src="https://github.com/user-attachments/assets/2f7c4f00-894a-4bc1-8fab-6b295c57accc" />

  建议使用JWT凭证，（API模式将在2027年废弃）
  项目id点击已创建的项目后可见。
  凭据id在创建凭据后可见，创建JWT凭据时粘贴ha页面显示的公钥即可。
  <img width="1610" height="653" alt="image" src="https://github.com/user-attachments/assets/47748808-b52c-4980-b38d-df42a4b17277" />
  HOST地址见设置页面
  <img width="1086" height="345" alt="image" src="https://github.com/user-attachments/assets/5ab678ab-09d0-4a83-8635-9a32432606dd" />
  国内的城市区域location、经纬度关系：
  https://github.com/qwd/LocationList/blob/master/China-City-List-latest.csv

6. 关注的自然灾害等级，1-6为从轻微到严重， 代表在灾害预警里你关注的灾害等级。
   
    "Standard": "标准的",
    "Minor": "次要的",
    "Moderate": "中等的",
    "Major": "主要",
    "Severe": "严重",
    "Extreme": "极端"
   
   只显示标题即只在灾害预警text中透出灾害标题，显示标题+明细信息则会在text中透出全部信息（会比较长）



## 自动化配置实例

https://www.bilibili.com/read/cv18078640

