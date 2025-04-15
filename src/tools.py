import requests, json, hashlib, hmac, base64, time
from datetime import datetime
from langchain_core.tools import tool
from src.utils import Config, setup_logger
from bs4 import BeautifulSoup
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class WeatherTool:
    def __init__(self):
        self.cfg = Config().get('weather_api') # 获取天气API配置
        self.logger = setup_logger('log')
        self.city_code_map = {
            "北京": "101010100", "上海": "101020100", "广州": "101280101", 
            "深圳": "101280601", "杭州": "101210101", "成都": "101270101",
            "重庆": "101040100", "武汉": "101200101", "南京": "101190101", 
            "西安": "101110101", "苏州": "101190401", "天津": "101030100",
            "长沙": "101250101", "青岛": "101120201", "大连": "101070201",
            "宁波": "101210401", "厦门": "101230201", "郑州": "101180101",
            "济南": "101120101"
        } # 城市代码映射表
        
    def get_weather(self, location, date='today'):
        """查询指定地点的天气情况"""
        # 支持字符串输入格式"城市,日期"
        if isinstance(location, str) and ',' in location:
            parts = location.split(',')
            location = parts[0].strip()
            if len(parts) > 1:
                date = parts[1].strip()
                
        self.logger.info(f"查询天气: 地点={location}, 日期={date}")
        
        try:
            api_key = self.cfg['key']
            api_type = self.cfg.get('type', 'weather_cn')  # 默认使用中国天气网
            
            # 如果没有配置API密钥或者选择mock数据，使用模拟数据
            if api_key == 'dummy_key' or api_type == 'mock':
                return self._get_mock_weather(location, date)
                
            # 根据API类型选择不同的处理方法
            if api_type == 'weather_cn':
                return self._get_weather_cn(location, date)
            elif api_type == 'seniverse':
                return self._get_seniverse_weather(location, date, api_key)
            elif api_type == 'qweather':
                return self._get_qweather(location, date, api_key)
            else:
                return self._get_weatherapi(location, date, api_key)
                
        except Exception as e:
            self.logger.error(f"查询天气失败: {e}")
            return {"error": str(e)}
            
    def _get_weather_cn(self, location, date):
        """使用中国天气网获取天气数据"""
        try:
            # 获取城市代码
            city_code = self.city_code_map.get(location)
            if not city_code:
                return {"error": f"未找到城市 {location} 的代码"}
            
            # 获取当前日期
            today = datetime.now().strftime("%d日")
            tomorrow = (datetime.now().day + 1) % 31
            tomorrow = f"{tomorrow}日"
            
            # 根据日期选择不同的URL
            if date == 'today':
                url = f"http://www.weather.com.cn/weather/{city_code}.shtml"
                date_str = f"今天（{today}）"
            else: # tomorrow
                url = f"http://www.weather.com.cn/weather/{city_code}.shtml"
                date_str = f"明天（{tomorrow}）"
            
            # 发送请求获取网页内容
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            weather_data = []
            
            # 查找天气数据
            weather_div = soup.find('div', {'id': '7d'})
            if weather_div:
                lis = weather_div.find('ul', class_='t clearfix').find_all('li')
                for i, li in enumerate(lis):
                    # 只处理今天或明天的数据
                    if (date == 'today' and i == 0) or (date == 'tomorrow' and i == 1):
                        weather_condition = li.find('p', class_='wea').text
                        temperature = li.find('p', class_='tem')
                        max_temp = temperature.find('span').text if temperature.find('span') else ''
                        min_temp = temperature.find('i').text
                        wind = li.find('p', class_='win').find('i').text
                        
                        # 提取数值
                        max_temp = re.findall(r'\d+', max_temp)[0] if max_temp and re.findall(r'\d+', max_temp) else ''
                        min_temp = re.findall(r'\d+', min_temp)[0] if min_temp and re.findall(r'\d+', min_temp) else ''
                        
                        if max_temp and min_temp:
                            temp_str = f"{max_temp}/{min_temp}℃"
                        elif max_temp:
                            temp_str = f"{max_temp}℃"
                        elif min_temp:
                            temp_str = f"{min_temp}℃"
                        else:
                            temp_str = "温度未知"
                        
                        # 格式化天气字符串
                        weather_str = f"{location}{date_str}天气：{weather_condition}，温度{temp_str}，{wind}"
                        return weather_str
            
            # 如果没有找到数据，返回错误
            return f"未能找到{location}的天气数据"
                
        except Exception as e:
            self.logger.error(f"中国天气网请求失败: {e}")
            return f"获取{location}天气数据失败: {str(e)}"
            
    def _get_seniverse_weather(self, location, date, api_key):
        """使用心知天气API获取天气数据"""
        # 获取公钥和私钥
        public_key = api_key
        private_key = self.cfg.get('private_key', '')
        
        # 设置接口参数
        if date == 'today':
            # 实时天气接口
            api_url = 'https://api.seniverse.com/v4'
            endpoint = '/weather/now.json'
        else:
            # 天气预报接口 
            api_url = 'https://api.seniverse.com/v4'
            endpoint = '/weather/daily.json'
            
        params = {
            'location': location,
            'public_key': public_key,
            'ts': str(int(time.time())),
            'language': 'zh-Hans',
            'unit': 'c',
        }
        
        # 如果有私钥，添加签名验证
        if private_key:
            params_str = '&'.join([f'{key}={params[key]}' for key in sorted(params.keys())])
            signature = self._generate_signature(params_str, endpoint, private_key)
            params['signature'] = signature
        
        # 发送请求
        url = f"{api_url}{endpoint}"
        response = requests.get(url, params=params, timeout=self.cfg['timeout'])
        
        if response.status_code == 200:
            data = response.json()
            
            # 处理返回数据
            if date == 'today':
                # 处理实时天气
                weather = data.get('results', [{}])[0].get('now', {})
                temp = weather.get('temperature', '未知')
                condition = weather.get('text', '未知')
                weather_str = f"{condition}，{temp}℃"
                return {"location": location, "date": date, "weather": weather_str}
            else:
                # 处理天气预报 (取明天的数据)
                daily = data.get('results', [{}])[0].get('daily', [{}])
                tomorrow = daily[1] if len(daily) > 1 else daily[0]
                temp_min = tomorrow.get('low', '未知')
                temp_max = tomorrow.get('high', '未知')
                condition = tomorrow.get('text_day', '未知')
                weather_str = f"{condition}，{temp_min}~{temp_max}℃"
                return {"location": location, "date": date, "weather": weather_str}
        else:
            error_msg = f"API请求失败: {response.status_code}"
            self.logger.error(f"{error_msg}, {response.text}")
            return {"error": error_msg}
            
    def _generate_signature(self, params_str, endpoint, private_key):
        """生成心知天气API签名"""
        sig_str = f"GET{endpoint}?{params_str}"
        sig_hash = hmac.new(
            private_key.encode('utf-8'),
            sig_str.encode('utf-8'),
            hashlib.sha1
        ).digest()
        return base64.b64encode(sig_hash).decode('utf-8')
    
    def _get_weatherapi(self, location, date, api_key):
        """使用WeatherAPI.com获取天气数据"""
        # 转换日期参数
        date_param = "forecast.json" if date == "tomorrow" else "current.json"
        days_param = 1 if date == "tomorrow" else None
        
        # 构建API请求
        url = f"https://api.weatherapi.com/v1/{date_param}"
        params = {
            'q': location,
            'key': api_key,
            'lang': 'zh',
            'days': days_param,
            'aqi': 'no'
        }
        
        # 移除None值参数
        params = {k: v for k, v in params.items() if v is not None}
        
        # 发送请求
        response = requests.get(url, params=params, timeout=self.cfg['timeout'])
        
        if response.status_code == 200:
            data = response.json()
            
            # 处理返回数据，根据日期返回不同格式
            if date == "today":
                temp = data['current']['temp_c']
                condition = data['current']['condition']['text']
                weather_str = f"{condition}，{temp}℃"
                return {"location": location, "date": date, "weather": weather_str}
                
            elif date == "tomorrow":
                forecast = data['forecast']['forecastday'][0]
                temp = forecast['day']['avgtemp_c']
                condition = forecast['day']['condition']['text']
                weather_str = f"{condition}，{temp}℃"
                return {"location": location, "date": date, "weather": weather_str}
        else:
            error_msg = f"API请求失败: {response.status_code}"
            self.logger.error(f"{error_msg}, {response.text}")
            return {"error": error_msg}
            
    def _get_qweather(self, location, date, api_key):
        """使用和风天气API获取天气数据"""
        # 设置请求参数
        if date == "today":
            # 实时天气API
            url = "https://devapi.qweather.com/v7/weather/now"
        else:
            # 3天预报API
            url = "https://devapi.qweather.com/v7/weather/3d"
            
        params = {
            'location': location,
            'key': api_key,
            'lang': 'zh'
        }
        
        # 发送请求
        response = requests.get(url, params=params, timeout=self.cfg['timeout'])
        
        if response.status_code == 200:
            data = response.json()
            
            # 检查API返回状态码
            if data['code'] != '200':
                error_msg = f"和风天气API错误: {data['code']}"
                self.logger.error(error_msg)
                return {"error": error_msg}
                
            # 处理返回数据，根据日期返回不同格式
            if date == "today":
                # 处理实时天气
                temp = data['now']['temp']
                condition = data['now']['text']
                weather_str = f"{condition}，{temp}℃"
                return {"location": location, "date": date, "weather": weather_str}
                
            elif date == "tomorrow":
                # 处理明天天气预报 (3天预报中的第二天)
                forecast = data['daily'][1]  # 索引0为今天，1为明天
                temp_min = forecast['tempMin']
                temp_max = forecast['tempMax']
                condition = forecast['textDay']
                weather_str = f"{condition}，{temp_min}~{temp_max}℃"
                return {"location": location, "date": date, "weather": weather_str}
        else:
            error_msg = f"API请求失败: {response.status_code}"
            self.logger.error(f"{error_msg}, {response.text}")
            return {"error": error_msg}
            
    def _get_mock_weather(self, location, date):
        """获取模拟天气数据"""
        weather_data = {
            "北京": {"today": "晴，25℃", "tomorrow": "多云，22℃"},
            "上海": {"today": "阴，20℃", "tomorrow": "小雨，19℃"},
            "广州": {"today": "晴，30℃", "tomorrow": "晴，31℃"},
            "深圳": {"today": "多云，28℃", "tomorrow": "阵雨，26℃"},
            "杭州": {"today": "小雨，19℃", "tomorrow": "阴，21℃"},
            "成都": {"today": "多云，22℃", "tomorrow": "晴，24℃"},
        }
        
        if location in weather_data and date in weather_data[location]:
            return {"location": location, "date": date, "weather": weather_data[location][date]}
        
        # 对于未知城市，返回随机天气
        return {"location": location, "date": date, "weather": "未知，数据暂缺"}

# 注册工具函数
@tool
def get_weather(input_str: str) -> str:
    """查询指定地点的天气情况。输入格式：地点,日期。日期可选值：today/tomorrow/after_tomorrow"""
    logger.info(f"查询天气: {input_str}")
    
    # 参数验证
    if not input_str or ',' not in input_str:
        return "参数错误：请提供正确的查询格式，如'北京,today'"
    
    # 解析参数
    location, date = input_str.split(',', 1)
    location = location.strip()
    date = date.strip().lower()
    
    # 验证地点
    if not location:
        return "参数错误：地点不能为空"
    
    # 验证日期
    valid_dates = ['today', 'tomorrow', 'after_tomorrow']
    if date not in valid_dates:
        return f"参数错误：日期必须是 {'/'.join(valid_dates)} 之一"
    
    # 使用WeatherTool类的city_code_map
    weather_tool = WeatherTool()
    city_codes = weather_tool.city_code_map
    
    # 检查城市是否支持
    if location not in city_codes:
        return f"暂不支持查询该地区，当前支持的城市: {', '.join(sorted(city_codes.keys()))}"
    
    try:
        # 构建URL
        url = f'http://www.weather.com.cn/weather/{city_codes[location]}.shtml'
        
        # 发送请求
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        
        if response.status_code != 200:
            return f"获取天气数据失败，HTTP状态码: {response.status_code}"
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        weather_div = soup.find('div', {'id': '7d'})
        if not weather_div:
            return "解析天气数据失败：找不到天气信息"
        
        # 获取天气数据
        weather_list = weather_div.find('ul').find_all('li')
        
        # 根据日期选择数据
        day_index = {'today': 0, 'tomorrow': 1, 'after_tomorrow': 2}
        weather_data = weather_list[day_index[date]]
        
        # 提取信息
        date_text = weather_data.find('h1').text
        weather_text = weather_data.find('p', {'class': 'wea'}).text
        temperature = weather_data.find('p', {'class': 'tem'}).text.strip()
        wind = weather_data.find('p', {'class': 'win'}).text.strip()
        
        # 格式化返回结果
        result = f"{location}{date_text}天气：{weather_text}，温度{temperature}，{wind}"
        logger.info(f"天气查询结果: {result}")
        return result
        
    except requests.RequestException as e:
        error_msg = f"请求天气数据失败: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"处理天气数据时出错: {str(e)}"
        logger.error(error_msg)
        return error_msg

# 添加单元测试
if __name__ == "__main__":
    import unittest
    
    class TestWeatherTool(unittest.TestCase):
        def setUp(self):
            self.weather_tool = WeatherTool()
            
        def test_mock_weather(self):
            """测试模拟天气数据"""
            result = self.weather_tool._get_mock_weather("北京", "today")
            self.assertEqual(result["location"], "北京")
            self.assertEqual(result["date"], "today")
            self.assertTrue("晴" in result["weather"])
            
            result = self.weather_tool._get_mock_weather("上海", "tomorrow")
            self.assertEqual(result["location"], "上海")
            self.assertEqual(result["date"], "tomorrow")
            self.assertTrue("小雨" in result["weather"])
            
            # 测试未知城市
            result = self.weather_tool._get_mock_weather("纽约", "today")
            self.assertEqual(result["location"], "纽约")
            self.assertEqual(result["date"], "today")
            self.assertTrue("未知" in result["weather"])
        
        def test_get_weather(self):
            """测试天气查询主方法"""
            # 使用模拟数据
            result = self.weather_tool.get_weather("北京,today")
            self.assertEqual(result["location"], "北京")
            self.assertEqual(result["date"], "today")
            self.assertFalse("error" in result)
            
            # 测试API调用(如果配置了有效的API密钥)
            if self.weather_tool.cfg["key"] != "dummy_key":
                result = self.weather_tool.get_weather("北京,today")
                self.assertEqual(result["location"], "北京")
                self.assertEqual(result["date"], "today")
                self.assertFalse("error" in result)
                print(f"API调用结果: {result['weather']}")
            else:
                print("使用模拟数据，跳过API测试")
    
    # 运行测试
    unittest.main() 