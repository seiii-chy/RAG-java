import jieba
import jieba.analyse
from collections import defaultdict

from jieba import posseg


class ChineseTokenizer:
    def __init__(self, tech_terms=None, synonyms=None, stopwords=None):
        """
        :param tech_terms: 技术术语列表，如["SpringBoot", "JVM调优"]
        :param synonyms: 同义词字典，如{"JVM": ["Java虚拟机"]}
        :param stopwords: 补充停用词列表
        """
        self.tech_terms = tech_terms or []
        self.synonyms = synonyms or {}
        self.stopwords = stopwords or set()

        # 初始化流程
        self._init_jieba()
        self._init_stopwords()
        self._init_jieba_config()

    def _init_jieba(self):
        """动态构建词典"""
        # 自动识别技术术语（如果没有提供）
        if not self.tech_terms:
            self.tech_terms = self._auto_detect_tech_terms()

        # 动态加载到分词器
        for term in self.tech_terms:
            jieba.add_word(term, freq=1000)

        jieba.initialize()

    def _auto_detect_tech_terms(self, top_n=50):
        """从文档中自动提取技术术语"""
        sample_text = """
            Java虚拟机(JVM)的垃圾回收(GC)机制是SpringBoot应用调优的重点，
            Kafka和RabbitMQ在分布式系统中扮演重要角色...
        """
        tags = jieba.analyse.extract_tags(sample_text, topK=top_n)
        return [t for t in tags if len(t) >= 2]

    def _init_stopwords(self):
        """基础停用词+自动补充"""
        self.base_stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "他", "不", "人", "这", "要", "也", "说",
                               "都"}
        self.full_stopwords = self.base_stopwords | self.stopwords

    def _init_jieba_config(self):
        """配置jieba参数"""
        jieba.initialize()
        jieba.setLogLevel(jieba.logging.INFO)

    def tokenize(self, text, use_pos=False):
        """
        核心分词方法
        :param text: 输入文本
        :param use_pos: 是否保留词性
        :return: 处理后的词列表
        """
        # 首次分词
        words = posseg.lcut(text)

        # 停用词过滤
        filtered = [w for w in words if w not in self.full_stopwords]

        # 同义词替换
        replaced = []
        for word in filtered:
            replaced.extend(self.synonyms.get(word, [word]))

        # 词性过滤（可选）
        if use_pos:
            pos_words = jieba.lcut(text)
            return [
                (w.word, w.flag)
                for w in pos_words
                if w.word not in self.full_stopwords
            ]

        return list(set(replaced))  # 去重后返回

    def extract_keywords(self, text, top_k=10):
        """基于TF-IDF的关键词提取"""
        return jieba.analyse.extract_tags(
            text,
            topK=top_k,
            withWeight=True,
            allowPOS=('n', 'vn', 'ns', 'eng')
        )

    def extract_keywords_without_weight(self, text, top_k=10):
        return jieba.analyse.extract_tags(
            text,
            topK=top_k,
            withWeight=False,
            allowPOS=('n', 'vn', 'ns', 'eng')
        )

    def named_entity_recognition(self, text):
        """命名实体识别"""
        # 使用jieba的词性标注来识别命名实体
        words = posseg.cut(text)
        entities = defaultdict(list)

        for word, flag in words:
            if flag in ('nr', 'ns', 'nt'):
                entities[flag].append(word)
        return dict(entities)