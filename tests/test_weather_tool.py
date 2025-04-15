import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools import get_weather

def test_weather_tool():
    """测试天气查询工具"""
    print("开始测试天气查询工具...")
    
    # 测试用例1：正常查询北京
    test_input1 = "北京,today"
    print(f"\n测试用例1 - 查询北京天气:")
    print(f"输入: {test_input1}")
    result1 = get_weather.invoke(test_input1)
    print(f"输出: {result1}")
    
    # 测试用例2：查询上海明天
    test_input2 = "上海,tomorrow"
    print(f"\n测试用例2 - 查询上海明天天气:")
    print(f"输入: {test_input2}")
    result2 = get_weather.invoke(test_input2)
    print(f"输出: {result2}")
    
    # 测试用例3：查询成都
    test_input3 = "成都,today"
    print(f"\n测试用例3 - 查询成都天气:")
    print(f"输入: {test_input3}")
    result3 = get_weather.invoke(test_input3)
    print(f"输出: {result3}")
    
    # 测试用例4：查询杭州后天
    test_input4 = "杭州,after_tomorrow"
    print(f"\n测试用例4 - 查询杭州后天天气:")
    print(f"输入: {test_input4}")
    result4 = get_weather.invoke(test_input4)
    print(f"输出: {result4}")
    
    # 测试用例5：查询武汉
    test_input5 = "武汉,today"
    print(f"\n测试用例5 - 查询武汉天气:")
    print(f"输入: {test_input5}")
    result5 = get_weather.invoke(test_input5)
    print(f"输出: {result5}")
    
    # 测试用例6：错误地点
    test_input6 = "不存在的地方,today"
    print(f"\n测试用例6 - 错误地点:")
    print(f"输入: {test_input6}")
    result6 = get_weather.invoke(test_input6)
    print(f"输出: {result6}")
    
    # 测试用例7：错误日期
    test_input7 = "南京,invalid_date"
    print(f"\n测试用例7 - 错误日期:")
    print(f"输入: {test_input7}")
    result7 = get_weather.invoke(test_input7)
    print(f"输出: {result7}")
    
    # 测试用例8：空输入
    test_input8 = ""
    print(f"\n测试用例8 - 空输入:")
    print(f"输入: {test_input8}")
    result8 = get_weather.invoke(test_input8)
    print(f"输出: {result8}")

if __name__ == "__main__":
    test_weather_tool() 