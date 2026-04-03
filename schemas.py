from pydantic import BaseModel


class PromptCreate(BaseModel):
    name: str


class VersionCreate(BaseModel):
    content: str


class ExperimentRun(BaseModel):
    prompt_id: int
    input_text: str