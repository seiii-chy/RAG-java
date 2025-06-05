from pymilvus import (
    FieldSchema,
    DataType,
    CollectionSchema,
    Collection,
    MilvusException
)


class DocumentModel:
    """Milvus 数据库模型定义"""

    # 字段配置
    FIELDS = [
        {
            "name": "id",
            "dtype": DataType.INT64,
            "is_primary": True,
            "auto_id": True
        },
        {
            "name": "chunk_embedding",
            "dtype": DataType.FLOAT_VECTOR,
            "dim": 512  # 根据实际模型维度调整
        },
        {
            "name": "content",
            "dtype": DataType.VARCHAR,
            "max_length": 30000
        },
        {
            "name": "file_name",
            "dtype": DataType.VARCHAR,
            "max_length": 255
        },
        {
            "name": "chunk_index",
            "dtype": DataType.INT32
        },
        {
            "name": "keywords",
            "dtype": DataType.VARCHAR,
            "max_length": 10000  # 逗号分隔的关键词
        },
        {
            "name": "belong_to",
            "dtype": DataType.INT32 #
        }
    ]

    @classmethod
    def create_schema(cls):
        """生成 Milvus 集合 Schema"""
        fields = [FieldSchema(**field) for field in cls.FIELDS]
        return CollectionSchema(
            fields=fields,
            description="Java技术文档向量存储",
            enable_dynamic_field=False
        )