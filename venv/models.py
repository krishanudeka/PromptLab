from sqlalchemy import Column, Integer, String, Text, ForeignKey
from database import Base

class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"))
    version_number = Column(Integer)
    content = Column(Text)


from sqlalchemy import Float

class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer)
    input_text = Column(Text)


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer)
    version_id = Column(Integer)
    output = Column(Text)
    score = Column(Float)