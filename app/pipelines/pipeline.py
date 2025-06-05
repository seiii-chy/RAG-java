import os

from app.pipelines.Embedding import VectorDB, EmbeddingGenerator
from app.pipelines.chunk import AdvancedChunker
from app.pipelines.tokenizer import ChineseTokenizer
from app.config import Settings


class ProcessingPipeline:
    def __init__(self):
        self.chunker = AdvancedChunker()
        self.tokenizer = ChineseTokenizer()
        self.VectorDB = VectorDB(milvus_uri=Settings.MILVUS_URL,token=Settings.MILVUS_TOKEN)
        self.embedding = EmbeddingGenerator(model_name='BAAI/bge-small-zh-v1.5')


    def process_file_path(self,file_path:str)->str:
        #extract name out of path
        file_name = os.path.basename(file_path)
        return file_name


    def process_document(self, file_stream, file_name, user_id):
        """完整处理流水线"""
        # 分块处理
        if file_name.endswith(".pdf"):
            chunks = self.chunker.process_pdf(file_stream)
        else:
            chunks = self.chunker.process_markdown(file_stream)
        print("-------------chunking ready-------------")
        # 并行分词
        tokenized_chunks = [self._process_chunk(chunk) for chunk in chunks]
        print("--------------token and embedding ready---------------")
        #添加chunk元数据
        for idx, chunk in enumerate(tokenized_chunks):
            chunk.update({
                "file_name": file_name,
                "chunk_index": idx,
                "user_id": user_id
            })

        self.VectorDB.add_documents(tokenized_chunks)
        print("--------------vectorized done--------------")
        return tokenized_chunks

    def _process_chunk(self, chunk):
        """单个分块处理"""

        # 预处理：生成摘要和关键词
        # summary = self.pre_process(chunk)
        return {
            "raw_text": chunk,
            # "tokens": self.tokenizer.tokenize(chunk),
            "chunk_vector": self.embedding.generate(chunk),
            "keywords": self.tokenizer.extract_keywords(chunk),
            "is_valid": True
        }

    # def pre_process(self, chunk):
    #     """判断chunk是否有效"""
    #     # llm_service = ChatOpenAI(model_name="hunyuan-lite",api_key=Settings.HUNYUAN_API_KEY, base_url="https://api.hunyuan.cloud.tencent.com/v1")
    #     # prompt = f"""请对以下内容生成总结：\n\n{chunk}\n\n请回答总结内容。"""
    #     # message = [HumanMessage(content=prompt)]
    #     # summary =  llm_service.invoke(message).content
    #     return None


if __name__ == "__main__":
    # 测试代码
    pipe = ProcessingPipeline()
#     chunk = """2.1 虚拟化 CPU
# 第第 22 章章 操操作作系系统统介介绍绍
# 如果你正在读本科操作系统课程，那么应该已经初步了解了计算机程序运行时做的事 情。如果不了解，这本书（和相应的课程）对你来说会很困难：你应该停止阅读本书，或 跑到最近的书店，在继续读本书之前快速学习必要的背景知识（包括 Patt / Patel [PP03 ]，特 别是 Bryant / O’Hallaron 的书[BOH10]，都是相当不错的）。
# 程序运行时会发生什么？ 一个正在运行的程序会做一件非常简单的事情：执行指令。处理器从内存中获取（fetch） 一条指令，对其进行解码（decode）（弄清楚这是哪条指令），然后执行（execute）它（做它 应该做的事情，如两个数相加、访问内存、检查条件、跳转到函数等）。完成这条指令后， 处理器继续执行下一条指令，依此类推，直到程序最终完成①。
# 这样，我们就描述了冯·诺依曼（Von Neumann）计算模型②的基本概念。听起来很简 单，对吧？但在这门课中，我们将了解到在一个程序运行的同时，还有很多其他疯狂的事 情也在同步进行——主要是为了让系统易于使用。
# 实际上，有一类软件负责让程序运行变得容易（甚至允许你同时运行多个程序），允许 程序共享内存，让程序能够与设备交互，以及其他类似的有趣的工作。这些软件称为操作 系统（Operating System，OS）③，因为它们负责确保系统既易于使用又正确高效地运行。
# 关键问题：如何将资源虚拟化
# 我们将在本书中回答一个核心问题：操作系统如何将资源虚拟化？这是关键问题。为什么操作系统
# 这样做？这不是主要问题，因为答案应该很明显：它让系统更易于使用。因此，我们关注如何虚拟化：
# 操作系统通过哪些机制和策略来实现虚拟化？操作系统如何有效地实现虚拟化？需要哪些硬件支持？
# 我们将用这种灰色文本框来突出“关键（crux）问题”，以此引出我们在构建操作系统时试图解决
# 的具体问题。因此，在关于特定主题的说明中，你可能会发现一个或多个关键点（是的，cruces 是正确
# 的复数形式），它突出了问题。当然，该章详细地提供了解决方案，或至少是解决方案的基本参数。"""
#
#     is_valid, summary =  pipe.pre_process(chunk)
#     print(f"Is valid: {is_valid}")
#     print(f"Summary: {summary}")