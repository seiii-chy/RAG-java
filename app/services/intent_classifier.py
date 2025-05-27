from enum import Enum

from app.api.dependency import get_llm_service_dependency


# 意图类型
class InterviewIntent(Enum):
    TECHNICAL = "technical"                # 技术意图
    PROCESS = "process"                    # 流程意图
    INTERACTIVE = "interactive"            # 交互意图
    ANALYTICAL = "analytical"              # 分析意图

# 意图详细说明
INTENT_DESCRIPTIONS = {
    InterviewIntent.TECHNICAL: "技术意图，包括代码技术、原理解释、性能优化、设计模式等。",
    InterviewIntent.PROCESS: "流程意图，包括面试步骤、时间安排、HR技巧等。",
    InterviewIntent.INTERACTIVE: "交互意图，包括追问、反馈、模拟对话。",
    InterviewIntent.ANALYTICAL: "分析意图，包括技术对比、案例分析。"
}

# 意图分类服务
class IntentClassificationService:
    def __init__(self, provider: str = 'deepseek'):
        self.llm_service = get_llm_service_dependency(provider)
    
    async def classify_intent(self, text: str) -> InterviewIntent:
        # 更可靠的提示，要求模型返回完整的意图名称而非数字
        prompt = f"""请根据以下文本识别意图：{text}，请将其分类为以下四种意图之一，直接返回意图名称（不要添加任何额外解释）：
            - TECHNICAL（技术意图：包括代码技术、原理解释、性能优化、设计模式等）
            - PROCESS（流程意图：包括面试步骤、时间安排、HR技巧等）
            - INTERACTIVE（交互意图：包括追问、反馈、模拟对话等）
            - ANALYTICAL（分析意图：包括技术对比、案例分析等）
            你的回答应该只包含一个意图名称。"""
        
        response = await self.llm_service.agenerate(prompt)
        intent_str = response.strip().upper()
        
        # 使用文本相似度匹配意图
        intent_keywords = {
            InterviewIntent.TECHNICAL: ["TECHNICAL", "技术", "代码", "原理", "优化", "设计模式"],
            InterviewIntent.PROCESS: ["PROCESS", "流程", "步骤", "时间安排", "HR技巧"],
            InterviewIntent.INTERACTIVE: ["INTERACTIVE", "交互", "追问", "反馈", "对话"],
            InterviewIntent.ANALYTICAL: ["ANALYTICAL", "分析", "对比", "案例"]
        }
        
        # 计算匹配分数
        best_intent = InterviewIntent.TECHNICAL  # 默认意图
        best_score = 0
        
        for intent, keywords in intent_keywords.items():
            # 计算关键词匹配分数
            score = sum(1 for keyword in keywords if keyword in intent_str)
            if score > best_score:
                best_score = score
                best_intent = intent
        
        # 直接匹配完整意图名称（最高优先级）
        if "TECHNICAL" in intent_str or "技术意图" in intent_str:
            return InterviewIntent.TECHNICAL
        elif "PROCESS" in intent_str or "流程意图" in intent_str:
            return InterviewIntent.PROCESS
        elif "INTERACTIVE" in intent_str or "交互意图" in intent_str:
            return InterviewIntent.INTERACTIVE
        elif "ANALYTICAL" in intent_str or "分析意图" in intent_str:
            return InterviewIntent.ANALYTICAL
        
        # 如果没有直接匹配，返回基于关键词的最佳匹配
        return best_intent