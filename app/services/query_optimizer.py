from enum import Enum
from typing import Dict, List, Tuple

import importlib
import os

# 意图类型
class InterviewIntent(Enum):
    DEFAULT = "default"                # 默认意图，无法归类时使用
    SUMMARY = "summary"                # 总结/摘要类请求
    COMPARISON = "comparison"          # 比较/对比类请求
    CLARIFICATION = "clarification"    # 澄清/追问类请求
    SUGGESTION = "suggestion"          # 建议/优化类请求
    INTERVIEW_FLOW = "interview_flow"  # 面试流程相关
    FEEDBACK = "feedback"              # 反馈/评价类请求
    CODE_TECH = "code_tech"            # 代码/技术（Java基础+框架）
    HR = "hr"                          # HR面试/软技能
    OTHER = "other"                    # 其他未归类意图

# 意图详细说明
INTENT_DESCRIPTIONS = {
    InterviewIntent.DEFAULT: "默认意图，未能明确分类的请求。",
    InterviewIntent.SUMMARY: "用户请求对内容进行总结或生成摘要。",
    InterviewIntent.COMPARISON: "用户要求对两个或多个对象进行比较。",
    InterviewIntent.CLARIFICATION: "用户对先前内容提出澄清或追问。",
    InterviewIntent.SUGGESTION: "用户请求建议、优化或改进方案。",
    InterviewIntent.INTERVIEW_FLOW: "涉及面试流程、步骤、安排等相关内容。",
    InterviewIntent.FEEDBACK: "用户对系统或内容进行反馈或评价。",
    InterviewIntent.CODE_TECH: "Java、主流框架、代码分析、计网、操作系统、分布式等技术问题。",
    InterviewIntent.HR: "HR面试、职业规划、沟通表达等软技能。",
    InterviewIntent.OTHER: "其他无法归类的意图。"
}

# 意图关键词模块映射
INTENT_KEYWORDS_MODULES = {
    InterviewIntent.SUMMARY: "summary",
    InterviewIntent.COMPARISON: "comparison",
    InterviewIntent.CLARIFICATION: "clarification",
    InterviewIntent.SUGGESTION: "suggestion",
    InterviewIntent.INTERVIEW_FLOW: "interview_flow",
    InterviewIntent.FEEDBACK: "feedback",
    InterviewIntent.CODE_TECH: "code_tech",
    InterviewIntent.HR: "hr",
}

class BM25IntentMatcher:
    def __init__(self, intent_modules_map):
        self.intent_keywords = self._load_keywords(intent_modules_map)
        # TODO: 集成BM25算法

    def _load_keywords(self, intent_modules_map):
        keywords_map = {}
        base_path = os.path.dirname(__file__)
        for intent, module_name in intent_modules_map.items():
            try:
                module = importlib.import_module(f".intent_keywords.{module_name}", package=__package__)
                keywords_map[intent] = getattr(module, "keywords", [])
            except Exception as e:
                keywords_map[intent] = []
        return keywords_map

    def match(self, text: str) -> Tuple[InterviewIntent, float]:
        lower_text = text.lower()
        best_intent = InterviewIntent.DEFAULT
        best_score = 0
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for k in keywords if k in lower_text)
            if score > best_score:
                best_score = score
                best_intent = intent
        return best_intent, best_score


# 意图识别主入口
bm25_matcher = BM25IntentMatcher(INTENT_KEYWORDS_MODULES)
def recognize_intent(text: str) -> InterviewIntent:
    if not text or not isinstance(text, str):
        return InterviewIntent.DEFAULT
    intent, score = bm25_matcher.match(text)
    if score > 0:
        return intent
    return InterviewIntent.DEFAULT