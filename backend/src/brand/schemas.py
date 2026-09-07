from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContentStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    traffic: int = Field(ge=0, le=100)
    brand: int = Field(ge=0, le=100)
    product: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def totals_one_hundred(self) -> ContentStrategy:
        if self.traffic + self.brand + self.product != 100:
            raise ValueError("content strategy percentages must total 100")
        return self


class ProductInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    category: str = ""
    audience: str = ""
    scene: str = ""
    selling_point: str = ""
    goal: str = ""
    inventory: str = ""


class BrandProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    positioning: str
    audiences: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    tone: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    content_strategy: ContentStrategy
    products: list[ProductInput] = Field(default_factory=list)
