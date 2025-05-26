import hashlib
import json
import re
from datetime import datetime
from typing import Dict,   Optional
from zoneinfo import ZoneInfo
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from flask import current_app
from app.models.Interview_question import InterviewQuestion
from app.models.answer import Answer
from app.models.interview import Interview
from app.models.question import Question


from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory





class InterviewSession:
    def __init__(self, db_session,user_id: int,provider: str = "deepseek", position: str = "高级开发工程师",first: bool = True,interview_name:str = "模拟面试",cv:str = "java工程师应聘"):
        self._history_store = {}
        self.db = db_session
        self.position = position
        self.user_id = user_id
        self.provider = provider
        self.llm = self._get_llm_by_provider(provider)
        self.redis = current_app.extensions['redis']
        self.interview_name = interview_name
        self.cv = cv

        #创造面试主记录
        self.interview = Interview(
            user_id=user_id,
            position=position,
            llm_provider=provider,
            interview_name = interview_name,
            started_at=datetime.now(ZoneInfo('Asia/Shanghai'))
        )
        if(first):
            self.db.add(self.interview)
            self.db.commit()

        # 配置LangChain
        self.memory = ConversationBufferMemory(
            return_messages=True
        )
        self.session_id = f"interview_{self.interview.id}"
        self.runnable = self._build_chain()


    def _build_chain(self):
        # 定义动态系统消息
        def dynamic_prompt(session_data: Dict):
            prompt=ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        f'''你正在面试{self.position}职位的候选人，当前阶段：{self._get_current_stage()}
                            请：
                            1. 生成专业评价（限100字），尽可能的亲和、关注被面试者的状态
                            2. 请尽可能根据求职人的简历描述进行针对性提问
                            3. 判断是否需要追问
                            4. 如果问题数目到了15个，请结束这次面试，并且给予被面试者一个总结性的评价
                            5. 以下会有你的历史对话记录，请根据上下文进行回答
                            6. 请勿针对一个点提问过多次数，当针对一个方向的问题达到三个时请更换方向提问
                            
                            以下是几个提问示例：
                            “说一下Java的特点” ，“与传统的JDBC相比，MyBatis的优点？”，“介绍一下TCP三次握手的流程”
                            “你在简历里提到xxx（技术点），可以介绍一下关于xxx的ccc吗”
                            
                            返回JSON格式：
                            {{{{"evaluation": "...","next_question": "...","need_followup": bool,"need_end": bool}}}}'''
                    ),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", "{input}")
                ]
            )
            return prompt

        # 创建可运行链
        prompt = dynamic_prompt({})

        runnable = (
                # {"input": RunnablePassthrough(),"history": RunnablePassthrough()}
                prompt
                | self.llm
                # | StrOutputParser()
                # | self._parse_llm_response  # 添加自定义解析
        )

        # 配置带历史记录的链
        return RunnableWithMessageHistory(
            runnable,
            self._get_session_history,
            input_messages_key="input",
            history_messages_key="history"
        )

        # 历史记录管理方法
    def _get_session_history(self, session_id: str) -> ChatMessageHistory:
        """获取当前会话的历史记录"""

        if session_id not in self._history_store:
            # 如果是第一个问题，添加系统提示到历史,并且添加cv的提问记录
            self._history_store[session_id] = ChatMessageHistory()
            self._history_store[session_id].add_ai_message("可以提供一下您的简历吗？")
            self._history_store[session_id].add_user_message(self.cv)
            if len(self._history_store[session_id].messages) == 0:
                self._history_store[session_id].add_ai_message(
                    f"开始{self.position}职位面试，当前阶段：{self._get_current_stage()}"
                )


        return self._history_store[session_id]

    def save_to_redis(self):
        """将会话历史保存到Redis"""
        try:
            # 基本键名, 使用interview ID而不是session_id作为标识更可靠
            interview_id = self.interview.id
            base_key = f"interview:{interview_id}"
            history = self._get_session_history(self.session_id).messages
            # 1. 保存消息历史 - 将消息序列化为JSON格式
            messages_data = []
            for msg in history:
                messages_data.append({
                    "type": msg.type,  # 'human' 或 'ai'
                    "content": msg.content,
                    "timestamp": datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
                })

            history_key = f"{base_key}:history"
            self.redis.set(
                history_key,
                json.dumps(messages_data),
                ex=86400  # 24小时过期
            )

            # 2. 保存元数据
            metadata = {
                "position": self.position,
                "user_id": self.user_id,
                "llm_provider": self.provider,
                "current_stage": self._get_current_stage(),
                "question_count": len(self.db.query(InterviewQuestion).filter_by(
                    interview_id=self.interview.id).all()),
                "last_updated": datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
            }

            metadata_key = f"{base_key}:metadata"
            self.redis.set(
                metadata_key,
                json.dumps(metadata),
                ex=86400  # 24小时过期
            )

            # 3. 保存会话ID到用户索引，方便按用户查询
            user_sessions_key = f"user:{self.user_id}:interviews"
            self.redis.sadd(user_sessions_key, interview_id)
            self.redis.expire(user_sessions_key, 604800)  # 7天过期

            return True
        except Exception as e:
            print(f"Redis存储失败: {str(e)}")
            return False

    @classmethod
    def load_from_redis(cls, db_session, interview_id, redis_client=None):
        """从Redis加载会话"""
        try:
            if redis_client is None:
                redis_client = current_app.extensions['redis']

            # 获取面试记录
            interview = db_session.query(Interview).get(interview_id)
            if not interview:
                raise ValueError(f"面试记录 {interview_id} 不存在")

            # 获取元数据
            metadata_key = f"interview:{interview_id}:metadata"
            metadata_json = redis_client.get(metadata_key)

            if not metadata_json:
                raise ValueError(f"Redis中没有找到面试会话 {interview_id} 的元数据")

            metadata = json.loads(metadata_json)

            # 创建会话实例，设置first=False避免创建新面试记录
            session = cls(
                db_session=db_session,
                user_id=metadata["user_id"],
                provider=metadata.get("llm_provider", "hunyuan"),
                position=metadata.get("position", "高级开发工程师"),
                first=False
            )

            # 设置已有的面试记录
            session.interview = interview
            session.session_id = f"interview_{interview_id}"

            # 加载历史记录
            history_key = f"interview:{interview_id}:history"
            history_json = redis_client.get(history_key)

            if history_json:
                messages_data = json.loads(history_json)
                # 恢复历史记录
                history = ChatMessageHistory()
                for msg in messages_data:
                    if msg["type"] == "human":
                        history.add_user_message(msg["content"])
                    elif msg["type"] == "ai":
                        history.add_ai_message(msg["content"])

                # 将历史记录加载到会话中
                session._history_store[session.session_id] = history

            return session
        except Exception as e:
            print(f"Redis加载失败: {str(e)}")
            return None


    def _get_llm_by_provider(self, provider: str):
        """根据提供商获取对应的LLM实例"""
        if provider == "openai":
            return ChatOpenAI(temperature=0.7, model_name="gpt-3.5-turbo")
        elif provider == "deepseek":
            # 假设使用HuggingFace加载deepseek模型
            return  ChatOpenAI(api_key=Settings.DEEPSEEK_API_KEY, base_url='https://api.deepseek.com/v1')
        elif provider == "hunyuan":
            # 为Hunyuan模型创建合适的接口 (如果有特定API)
            # 这里使用ChatOpenAI作为占位符，实际应根据hunyuan API调整
            return ChatOpenAI(model_name="hunyuan-lite",api_key=Settings.HUNYUAN_API_KEY, base_url="https://api.hunyuan.cloud.tencent.com/v1")
        else:
            # 默认使用OpenAI
            return ChatOpenAI(temperature=0.7)



    async def generate_question(self, answer: Optional[str] =None) -> Dict:
        history = self._get_session_history(self.session_id).messages
        print("\n" + "=" * 50)
        print("当前对话历史:")
        for msg in history:
            print(f"{msg.type}: {msg.content}")
        print("=" * 50 + "\n")

        input_data = {"input": answer or "请提出第一个问题"}
        print("动态生成的Prompt结构:")
        print(json.dumps({
            "system_prompt": f"你正在面试{self.position}职位的候选人，当前阶段：{self._get_current_stage()}...",
            "history": [{"role": msg.type, "content": msg.content} for msg in history],
            "human_input": input_data["input"]
        }, indent=2, ensure_ascii=False))
        print("\n" + "=" * 50 + "\n")

        """生成问题并记录"""
        llm_response = await self.runnable.ainvoke(
            {"input": answer or "请提出第一个问题"
             },
            config={"configurable": {"session_id": self.session_id}}
        )

        result = self._parse_llm_response(llm_response)
        print("result:", result)
        # 存储问题
        question_record = self._create_question_record(result)
        _,_,question_id =  self._save_question(question_record)
        #存储到历史
        # self._save_answer_to_history(answer or "请提出第一个问题")
        # self._save_question_to_history(result["question"])

        print("生成问题后的对话历史:")
        history = self._get_session_history(self.session_id).messages
        for msg in history:
            print(f"{msg.type}: {msg.content}")
        print("=" * 50 + "\n")
        self.save_to_redis()
        # 存储回答（如果有）
        if answer:
            self._save_answer(question_id, answer, result['evaluation'])

        return question_record

    def _get_current_stage(self) -> str:
        """根据问题历史判断当前阶段"""
        # 实现你的阶段判断逻辑
        return "初步筛选"

    def _parse_llm_response(self, raw_response: str) -> dict:
        """
        解析LLM的原始响应，提取结构化数据
        返回格式：
        {
            "question": str,
            "evaluation": str,
            "need_followup": bool,
            "stage": str,
            "context": dict  # 原始对话上下文
        }
        """
        try:
            # 尝试解析JSON格式响应
            print("raw_response:", raw_response)
            content_str = raw_response.content
            json_match = re.search(r'```json\n(.*?)```', content_str, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1).strip())
            else:
                data = json.loads(content_str)
            return {
                "question": data["next_question"],
                "evaluation": data["evaluation"],
                "need_followup": data.get("need_followup", False),
                "stage": self._determine_stage(data.get("evaluation", "")),
                "context": {
                    "parsed_data": data,
                    "timestamp": datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
                }
            }
        except (json.JSONDecodeError, KeyError) as e:
            # 失败时使用应急处理
            return self._fallback_parse(raw_response)

    def _fallback_parse(self, raw_text: str) -> dict:
        """应急解析方案"""
        return {
            "question": "能否详细说明您在这方面的经验？",
            "evaluation": "正在分析您的回答...",
            "need_followup": True,
            "stage": "general",
            "context": {
                "error": "failed_to_parse",
                "raw_text": raw_text
            }
        }

    def _determine_stage(self, evaluation_text: str) -> str:
        """根据评价内容判断当前阶段"""
        evaluation_text = evaluation_text.lower()
        if any(word in evaluation_text for word in ["基础", "basic", "fundamental"]):
            return "technical_basic"
        elif any(word in evaluation_text for word in ["项目", "project", "experience"]):
            return "project_experience"
        elif any(word in evaluation_text for word in ["设计", "design", "架构"]):
            return "system_design"
        return "general"

    def _create_question_record(self, parsed_data: dict) -> dict:
        """
        创建标准化的问题记录
        返回格式：
        {
            "text": str,
            "category": str,
            "difficulty": str,
            "stage": str,
            "is_followup": bool,
            "evaluation": str,
            "llm_provider": str,
            "order": int,
            "context": dict
        }
        """
        # 自动判断问题类型和难度
        question_text = parsed_data["question"]
        category, difficulty = self._analyze_question(question_text)

        return {
            "text": question_text,
            "category": category,
            "difficulty": difficulty,
            "stage": parsed_data["stage"],
            "is_followup": parsed_data["need_followup"],
            "evaluation": parsed_data["evaluation"],
            "llm_provider": self.llm.__class__.__name__,
            "order": len(self.db.query(InterviewQuestion).filter_by(
                interview_id=self.interview.id).all()) + 1,
            "context": parsed_data["context"]
        }

    def _analyze_question(self, question_text: str) -> tuple[str, str]:
        """分析问题类型和难度"""
        # 实现简单的关键词分析
        text = question_text.lower()

        # 判断类别
        if any(word in text for word in ["怎么实现", "算法", "优化"]):
            category = "technical"
        elif any(word in text for word in ["项目", "经验", "案例"]):
            category = "project"
        elif any(word in text for word in ["设计", "架构", "扩展"]):
            category = "system_design"
        else:
            category = "behavioral"

        # 判断难度（简单实现）
        question_length = len(question_text)
        if question_length > 150:
            difficulty = "hard"
        elif question_length > 80:
            difficulty = "medium"
        else:
            difficulty = "easy"

        return category, difficulty

    def _save_question(self, question_data: dict) -> tuple[Question, InterviewQuestion,int]:
        """
        保存问题到数据库，返回(Question, InterviewQuestion)记录
        """
        # 创建或获取基础问题记录
        text_hash = hashlib.sha256(question_data["text"].encode()).hexdigest()
        question = self.db.query(Question).filter_by(text_hash=text_hash).first()

        if not question:
            question = Question(
                text=question_data["text"],
                text_hash=text_hash,
                meta_info={
                    "category": question_data["category"],
                    "difficulty": question_data["difficulty"],
                    "provider": question_data["llm_provider"]
                }
            )
            self.db.add(question)
            self.db.flush()  # 立即生成ID但不提交

        # 创建面试关联记录
        interview_question = InterviewQuestion(
            interview_id=self.interview.id,
            question_id=question.id,
            stage=question_data["stage"],
            is_followup=question_data["is_followup"],
            evaluation=question_data["evaluation"],
            order=question_data["order"],
            context=question_data["context"]
        )
        self.db.add(interview_question)
        self.db.commit()

        return question, interview_question,interview_question.id

    def _save_answer(self,
                     interview_question_id: int,
                     answer_text: str,
                     evaluation: Optional[str] = None) -> Answer:
        """
        存储用户回答到数据库
        :param interview_question_id: InterviewQuestion关联记录的ID
        :param answer_text: 用户回答内容
        :param evaluation: LLM生成的评价（可选）
        :return: 创建的Answer记录
        """
        try:
            # 验证关联问题是否存在
            iq_record = self.db.query(InterviewQuestion) \
                .filter_by(id=interview_question_id) \
                .first()

            if not iq_record:
                raise ValueError(f"InterviewQuestion记录 {interview_question_id} 不存在")

            # 创建回答记录
            answer = Answer(
                interview_question_id=interview_question_id,
                text=answer_text,
                evaluation=evaluation or iq_record.evaluation
            )

            self.db.add(answer)
            self.db.commit()

            return answer

        except SQLAlchemyError as e:
            self.db.rollback()
            raise RuntimeError(f"回答存储失败: {str(e)}") from e

    async def generate_final_score_and_feedback(self)->tuple[int, str]:
        """
        生成最终评分和反馈
        :return: (final_score, feedback)
        """
        # 根据面试记录生成评分和反馈
        # 根据历史询问GPT生成评分和反馈
        history_str = "\n".join(
            [f"{msg.type}: {msg.content}" for msg in self._get_session_history(self.session_id).messages]
        )
        prompt = f"""
              你已经完成了对于{self.position}职位候选人的面试，以下是你们的对话记录：
                {history_str}
                请根据对话记录生成一个最终的评分（1-100分）和反馈总结（限200字），
                评分和反馈要尽量客观和专业。
                返回JSON格式：
                {{{{"final_score": int,"feedback_summary": "...","need_end": bool}}}}"""
        llm_response = await self.llm.ainvoke(prompt)
        print("llm_response:", llm_response)
        # 解析响应
        try:
            content_str = llm_response.content
            json_match = re.search(r'```json\n(.*?)```', content_str, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1).strip())
            else:
                data = json.loads(content_str)
            final_score = data["final_score"]
            feedback_summary = data["feedback_summary"]
        except (json.JSONDecodeError, KeyError) as e:
            # 失败时使用应急处理
            final_score = 75
            feedback_summary = "面试过程顺利，但有些问题需要进一步深入了解。"
            print(f"解析失败: {str(e)}")
        # 更新面试记录
        self.interview.final_score = final_score
        self.interview.feedback = feedback_summary
        self.interview.ended_at = datetime.now(ZoneInfo('Asia/Shanghai'))
        self.db.commit()
        # 保存到Redis
        self.save_to_redis()
        # 返回评分和反馈
        return final_score, feedback_summary


def test_chain_initialization():
    from app.extensions import db
    from app.main import create_app
    app = create_app()
    with app.app_context():
        session = InterviewSession(
            db_session=db.session,
            user_id=1,
            position="Java工程师",
            provider="hunyuan"
        )

import asyncio
from app.extensions import db
from sqlalchemy.orm import sessionmaker


async def async_test_generate():
    from app.main import create_app
    app = create_app()

    with app.app_context():
        Session = sessionmaker(bind=db.engine)
        session = Session()
        db.create_all()

        # 创建面试会话
        interview_session = InterviewSession(session, user_id=1, provider="hunyuan")
        print("面试会话创建成功")

        # 生成问题
        question_result = await interview_session.generate_question()
        print("生成的问题：", question_result)

        # 包装成同步函数以便普通测试框架可以调用
def test_generate():
    asyncio.run(async_test_generate())
        # # 处理回答
        # answer_result = interview_session.process_answer("我在项目中使用了Spring框架")
        # print("处理后的回答：", answer_result)
