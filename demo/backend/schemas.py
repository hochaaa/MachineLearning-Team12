"""Independent demo request validation, compatible fields plus AND scent rules."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Scent = Literal['woody', 'floral', 'rose']

class Rating(BaseModel):
    model_config = ConfigDict(extra='forbid')
    perfume_id: str = Field(min_length=1, max_length=80)
    rating: float = Field(ge=0, le=10, allow_inf_nan=False)

    @field_validator('rating', mode='before')
    @classmethod
    def numeric(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('Use numeric ratings from 0 to 10')
        return value

class Recommendation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ratings: list[Rating] = Field(min_length=1, max_length=50)
    required_scent: Literal['none', 'woody', 'floral', 'rose'] = 'none'
    required_scents: list[Scent] = Field(default_factory=list, max_length=3)
    top_k: Literal[5] = 5

    @field_validator('top_k', mode='before')
    @classmethod
    def integer_five(cls, value):
        if type(value) is not int or value != 5:
            raise ValueError('top_k must be integer 5')
        return value

    @model_validator(mode='after')
    def unique(self):
        if len({r.perfume_id for r in self.ratings}) != len(self.ratings):
            raise ValueError('Duplicate perfume IDs')
        return self
