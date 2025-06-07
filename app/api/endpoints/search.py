from flask import Blueprint, request, jsonify, Response, current_app

from app.services.rag import RAGService

bp = Blueprint('search', __name__)

@bp.route('/search', methods=['POST'])
async def search():
    try:
        # 1. 解析请求数据
        data = request.get_json()
        query = data.get("query")
        top_k = data.get("top_k", 5)
        model = data.get("model", "hunyuan")# 默认检索前 5 条结果

        if not query:
            return jsonify({"error": "Missing 'query' in request body"}), 400
        if model not in ["hunyuan", "deepseek"]:
            model = "hunyuan"
        # 2. 初始化 RAG 服务
        rag_service = RAGService(LLMrequire=model)

        # 3. 执行 RAG 查询
        result = await rag_service.query(query, top_k=top_k)

        # 4. 构造响应
        return jsonify({
            "answer": result["answer"],
            "retrieved_docs": result["retrieved_docs"]
        })

    except Exception as e:
        # 捕获异常并返回错误信息
        return jsonify({"error": str(e)}), 500

@bp.route('/hybrid_search', methods=['POST'])
async def hybrid_search():
    try:
        # 1. 解析请求数据
        data = request.get_json()
        query = data.get("query")
        top_k = data.get("top_k", 5)  # 默认检索前 5 条结果
        model = data.get("model", "hunyuan")

        if not query:
            return jsonify({"error": "Missing 'query' in request body"}), 400

        if model not in ["hunyuan", "deepseek"]:
            model = "hunyuan"

        # 2. 初始化 RAG 服务
        rag_service = RAGService(LLMrequire=model)

        # 3. 执行 RAG 查询
        result = await rag_service.hybrid_search(query, top_k=top_k)

        # 4. 构造响应
        return jsonify({
            "answer": result["answer"],
            "retrieved_docs": result["retrieved_docs"]
        })

    except Exception as e:
        # 捕获异常并返回错误信息
        return jsonify({"error": str(e)}), 500

@bp.route('/stream_output',methods=['POST'])
def stream_output():
    #build a server sent event
    data = request.get_json()
    query = data.get("query")
    top_k = data.get("top_k", 5)# 默认检索前 5 条结果
    model = data.get("model","hunyuan")
    collection_name = data.get("collection_name", "java_doc_plus")
    milvus_client = current_app.extensions['milvus']
    if milvus_client.collection_name != collection_name:
        milvus_client.change_collection(collection_name)
    print("query:",query)
    if not query:
        return jsonify({"error": "Missing 'query' in request body"}), 400
    if model not in ["hunyuan", "deepseek"]:
        model = "hunyuan"
        # 2. 初始化 RAG 服务
    rag_service = RAGService(LLMrequire=model)
    print("service:",rag_service)

    # def generate():
    #     try:
    #         # 流式输出文档和生成内容
    #         import asyncio
    #         async def _collect_async_results():
    #             results = []
    #             async for packet in rag_service.stream_output(query, top_k=top_k):
    #                 results.append(packet)
    #             return results
    #
    #         for packet in asyncio.run(_collect_async_results()):
    #             yield f"data: {packet}\n\n"
    #         yield "data: [END]\n\n"
    #     except Exception as e:
    #         print(f"Error during streaming: {e}")
    #         yield "data: [ERROR]\n\n"
    # 创建线程安全的队列
    import asyncio, threading
    data_queue = asyncio.Queue()
    loop = asyncio.new_event_loop()

    async def async_generator():
        """真正的异步生成器协程"""
        try:
            async for packet in rag_service.stream_output(query, top_k=top_k):
                # 将数据放入队列
                await data_queue.put(packet)
            await data_queue.put("[END]")
        except Exception as e:
            print(f"Error during async streaming: {e}")
            await data_queue.put("[ERROR]")

    def run_async_task():
        """在单独线程中运行异步任务"""
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_generator())

    # 启动异步任务线程
    threading.Thread(target=run_async_task, daemon=True).start()

    def generate():
        """同步生成器，从队列获取数据"""
        try:
            while True:
                # 同步等待队列数据
                packet = asyncio.run_coroutine_threadsafe(data_queue.get(), loop).result()

                if packet == "[END]":
                    yield "data: [END]\n\n"
                    break
                elif packet == "[ERROR]":
                    yield "data: [ERROR]\n\n"
                    break
                else:
                    yield f"data: {packet}\n\n"
        except Exception as e:
            print(f"Error in synchronous generator: {e}")
            yield "data: [ERROR]\n\n"
        finally:
            # 清理事件循环
            loop.call_soon_threadsafe(loop.stop)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )