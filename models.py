from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

    versions = relationship("PromptVersion", back_populates="prompt")


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"))
    version_number = Column(Integer)
    content = Column(Text)

    prompt = relationship("Prompt", back_populates="versions")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"))
    input_text = Column(Text)

    results = relationship("Result", back_populates="experiment")


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"))
    version_id = Column(Integer, ForeignKey("prompt_versions.id"))
    output = Column(Text)
    score = Column(Float)
    latency = Column(Float)

    experiment = relationship("Experiment", back_populates="results")