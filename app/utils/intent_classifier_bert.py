from enum import Enum
import torch
from transformers import BertTokenizer

# 意图类型
class InterviewIntent(Enum):
    TECHNICAL = "technical"                # 技术意图
    PROCESS = "process"                    # 流程意图
    INTERACTIVE = "interactive"            # 交互意图
    ANALYSIS = "analysis"                  # 分析意图
    GENERAL = "general"                    # 通用意图

# 意图详细说明
INTENT_DESCRIPTIONS = {
    InterviewIntent.TECHNICAL: "技术意图，包括代码技术、原理解释、性能优化、设计模式等。",
    InterviewIntent.PROCESS: "流程意图，包括面试步骤、时间安排、HR技巧等。",
    InterviewIntent.INTERACTIVE: "交互意图，包括追问、反馈、模拟对话。",
    InterviewIntent.ANALYSIS: "分析意图，包括技术对比、案例分析。",
    InterviewIntent.GENERAL: "通用意图，适用于无法明确分类的情况。"
}

# 意图分类服务
class IntentClassificationService:
    def __init__(self):

        # 加载预训练的BERT模型和tokenizer
        self.model = torch.load('model.pth')
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
        self.device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
        # 定义类别映射
        self.labels_map = {
                                InterviewIntent.TECHNICAL: 0,
                                InterviewIntent.PROCESS: 1, 
                                InterviewIntent.INTERACTIVE: 2, 
                                InterviewIntent.ANALYSIS: 3, 
                                InterviewIntent.GENERAL: 4
                                }
        self.reverse_labels_map = {v: k for k, v in self.labels_map.items()}
        
    async def classify_intent(self, text: str) -> InterviewIntent:

        encoded_text = self.tokenizer.encode_plus(text, add_special_tokens=True, max_length=64, padding='max_length', truncation=True, return_tensors='pt')

        # 模型推理
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(input_ids=encoded_text['input_ids'].to(self.device), attention_mask=encoded_text['attention_mask'].to(self.device))
            predicted_label = torch.argmax(outputs.logits, dim=1).item()

            # 解码预测的类别
            intent = self.reverse_labels_map[predicted_label]
            return intent
