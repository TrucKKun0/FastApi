from pydantic import BaseModel,ConfigDict,Field


class PostBase(BaseModel):
    title : str = Field(min_length = 1 , max_length = 100)
    content : str = Field(min_length = 5)
    author : str = Field(min_length = 1, max_length = 50)

class PostCreate(PostBase):
    published: bool = False

class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes = True)
    id : int
    date_posted : str 
    published : bool