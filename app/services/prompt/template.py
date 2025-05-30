class PromptTemplate:
    def __init__(self, template: str):
        self.template = template

    def format(self, **kwargs) -> str:
        return self.template.format(**kwargs)

    def generate(self, query: str, context: str = None, **kwargs) -> str:
        return query