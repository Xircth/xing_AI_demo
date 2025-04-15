import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm_service import LLMService
from src.middleware import LangchainMiddleware

def test_llm_weather_query():
    """测试大模型天气查询功能"""
    print("开始测试大模型天气查询功能...")
    
    # 初始化服务
    llm_service = LLMService()
    middleware = LangchainMiddleware(llm_service)
    
    # 测试用例列表
    test_cases = [
        {
            "query": "北京今天天气怎么样？",
            "expected_location": "北京",
            "expected_date": "today"
        },
        {
            "query": "明天上海会下雨吗？",
            "expected_location": "上海",
            "expected_date": "tomorrow"
        },
        {
            "query": "后天成都温度多少度？",
            "expected_location": "成都",
            "expected_date": "after_tomorrow"
        },
        {
            "query": "深圳现在热不热？",
            "expected_location": "深圳",
            "expected_date": "today"
        },
        {
            "query": "杭州明天适合出门吗？",
            "expected_location": "杭州",
            "expected_date": "tomorrow"
        }
    ]
    
    # 执行测试
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected_location = test_case["expected_location"]
        expected_date = test_case["expected_date"]
        
        print(f"\n测试用例{i}:")
        print(f"用户问题: {query}")
        print(f"期望解析: 地点={expected_location}, 日期={expected_date}")
        
        try:
            # 使用中间件处理查询
            response = middleware.process_query(query)
            print(f"系统回答: {response}")
            
            # 检查回答是否包含关键信息
            if expected_location in response and ("天气" in response or "温度" in response):
                print("✅ 测试通过：成功返回天气信息")
            else:
                print("❌ 测试失败：回答可能不完整或不准确")
                
        except Exception as e:
            print(f"❌ 测试出错: {str(e)}")
            
    print("\n所有测试完成")

if __name__ == "__main__":
    test_llm_weather_query() 