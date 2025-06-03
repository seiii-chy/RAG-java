import asyncio
from http import HTTPStatus

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.Interview_question import InterviewQuestion
from app.models.answer import Answer
from app.models.interview import Interview
from app.models.question import Question
from app.services.interview.interview import InterviewSession

interview_bp = Blueprint('interview', __name__, url_prefix='/interviews')


@interview_bp.route('', methods=['POST'])
def start_interview():
    """
    开始新的面试会话
    POST interviews
    {
        "user_id": 123,
        "position": "高级开发工程师",
        "provider": "hunyuan"
        "interview_name": "我的第一次模拟面试“
    }
    """
    try:
        data = request.get_json()
        # 参数验证
        required_fields = ['user_id', 'position',"interview_name","cv"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), HTTPStatus.BAD_REQUEST

        # 创建面试会话
        session = db.session
        interview_session = InterviewSession(
            db_session=session,
            user_id=data['user_id'],
            position=data['position'],
            provider=data.get('provider', 'hunyuan'),
            interview_name = data["interview_name"],
            cv = data['cv']
        )

        # 生成第一个问题
        initial_question = asyncio.run(interview_session.generate_question())
        # 保存面试会话到redis
        interview_session.save_to_redis()
        return jsonify({
            "interview_id": interview_session.interview.id,
            "first_question": initial_question,
            "start_time": interview_session.interview.started_at.isoformat()
        }), HTTPStatus.CREATED

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@interview_bp.route('/<int:interview_id>/answers', methods=['POST'])
async def submit_answer(interview_id):
    """
    提交回答并获取下一个问题
    POST interviews/123/answers
    {
        "answer": "我的回答内容..."
    }
    """
    try:
        data = request.get_json()
        if 'answer' not in data:
            return jsonify({"error": "Answer is required"}), HTTPStatus.BAD_REQUEST

        # 获取面试记录
        interview = db.session.get(Interview, interview_id)
        if not interview:
            raise NoResultFound("Interview not found")
        if interview.ended_at:
            return jsonify({"error": "Interview already ended"}), HTTPStatus.BAD_REQUEST

        # 尝试从Redis恢复会话
        redis_client = current_app.extensions['redis']
        redis_key = f"interview:{interview_id}"

        # 检查Redis中是否存在此会话
        if redis_client.exists(f"{redis_key}:metadata"):
            # 从Redis恢复会话
            interview_session = InterviewSession.load_from_redis(
                db_session=db.session,
                interview_id=interview_id,
                redis_client=redis_client
            )

            if not interview_session:
                # 恢复失败，创建新会话
                interview_session = InterviewSession(
                    db_session=db.session,
                    user_id=interview.user_id,
                    provider=interview.llm_provider,
                    position=interview.position,
                    first=False
                )
                interview_session.interview = interview
        else:
            # Redis中没有会话记录，创建新的会话实例
            interview_session = InterviewSession(
                db_session=db.session,
                user_id=interview.user_id,
                provider=interview.llm_provider,
                position=interview.position,
                first=False
            )
            interview_session.interview = interview
        # 提交回答
        # 处理回答并生成新问题
        next_question = await interview_session.generate_question(data['answer'])

        # 获取当前阶段和进度
        current_stage = interview_session._get_current_stage()
        question_count = len(db.session.query(InterviewQuestion).filter_by(
            interview_id=interview_id).all())

        return jsonify({
                "next_question": next_question,
                "current_stage": current_stage,
                "progress": f"{question_count}/15"
            }), HTTPStatus.OK
    except NoResultFound:
        return jsonify({"error": "Interview not found"}), HTTPStatus.NOT_FOUND
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@interview_bp.route('/<int:interview_id>', methods=['POST'])
async def end_interview(interview_id):
    """
    结束面试会话
    POST /api/v1/interviews/123
    """
    try:
        interview = db.session.get(Interview, interview_id)
        # 获取面试记录
        if(interview.final_score is not None and interview.feedback is not None):
            return jsonify({"error": "Interview already ended"}), HTTPStatus.BAD_REQUEST
        if not interview:
            return jsonify({"error": "Interview not found"}), HTTPStatus.NOT_FOUND

        if interview.ended_at:
            return jsonify({"error": "Interview already ended"}), HTTPStatus.BAD_REQUEST
        # 结束面试
        interview.ended_at = db.func.now()
        #生成面试的 final_score 和 feedback

        # 尝试从Redis恢复会话
        redis_client = current_app.extensions['redis']
        redis_key = f"interview:{interview_id}"

        # 检查Redis中是否存在此会话
        if redis_client.exists(f"{redis_key}:metadata"):
            # 从Redis恢复会话
            interview_session = InterviewSession.load_from_redis(
                db_session=db.session,
                interview_id=interview_id,
                redis_client=redis_client
            )

            if not interview_session:
                #报错
                raise NoResultFound("Interview session not found in Redis")
        else:
            raise NoResultFound("Interview session not found in Redis")

        # 根据interview_session生成 final_score 和 feedback
        final_score,feedback = await interview_session.generate_final_score_and_feedback()




        db.session.commit()



        return jsonify({"message": "Interview ended successfully",
                        "final_score": final_score,
                        "feed_back": feedback}), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR

@interview_bp.route('/<int:user_id>', methods=['GET'])
def get_user_old_interviews(user_id):
    """
    获取用户的旧面试记录
    GET /api/v1/interviews/123
    """
    try:
        interview = db.session.query(Interview).filter_by(user_id=user_id).all()
        if not interview:
            return jsonify({"error": "Interview not found"}), HTTPStatus.NOT_FOUND

        # 获取面试信息
        interview_list = []
        for interview in interview:
            interview_list.append({
                "interview_id": interview.id,
                "user_id": interview.user_id,
                "position": interview.position,
                "started_at": interview.started_at.isoformat(),
                "ended_at": interview.ended_at.isoformat() if interview.ended_at else None
            })
        return jsonify(interview_list), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR

@interview_bp.route('/single/<int:interview_id>', methods=['GET'])
def get_interview(interview_id):
    """
    获取面试记录
    GET /api/v1/interviews/123
    """
    try:
        interview = db.session.get(Interview, interview_id)
        if not interview:
            return jsonify({"error": "Interview not found"}), HTTPStatus.NOT_FOUND


        return jsonify({
            "interview_id": interview.id,
            "user_id": interview.user_id,
            "position": interview.position,
            "interview_name": interview.interview_name,
            "started_at": interview.started_at.isoformat(),
            "ended_at": interview.ended_at.isoformat() if interview.ended_at else None,
        }), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@interview_bp.route('/<int:interview_id>/questions', methods=['GET'])
def get_interview_questions(interview_id):
    """
    获取面试问题列表
    GET /api/v1/interviews/123/questions
    """
    try:
        #在全连接的interview_question和question表中查询
        questions = (
            db.session.query(InterviewQuestion,Question, Answer)
            .join(Question, InterviewQuestion.question_id == Question.id)
            .join(Answer, InterviewQuestion.id == Answer.interview_question_id) # 自动基于 InterviewQuestion.id == Answer.interview_question_id 连接
            .all()
        )
        print(questions)
        question_list = []
        for interview_q, question, answer in questions:
            if interview_q.interview_id == interview_id:
                question_list.append({
                    "interview_question_id": interview_q.id,
                    "question_id": question.id,
                    "question_text": question.text,
                    "answer_text": answer.text if answer else None,
                    "evaluation": interview_q.evaluation,
                    "stage": interview_q.stage,
                })
        #加上本次面试评价
        interview = db.session.get(Interview, interview_id)
        question_list.append({
            "interview_id": interview.id,
            "final_score": interview.final_score,
            "feedback": interview.feedback
        })
        return jsonify(question_list), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR