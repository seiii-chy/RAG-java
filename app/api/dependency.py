from app.services.llm.factory import get_llm_service

def get_llm_service_dependency(provider: str):
    service = get_llm_service(provider)
    return service
