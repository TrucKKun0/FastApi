from pydantic import BaseModel,ConfigDict,Field,EmailStr

from datetime import datetime

class UserBase(BaseModel):
    username : str = Field(min_length=1, max_length=100)
    email : EmailStr = Field(max_length=120) 
class UserCreate(UserBase):
    pass
class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes= True)
    id : int
    image_file : str | None
    image_path  : str
 
class UserUpdate(UserBase):
    username : str | None = Field(default=None,min_length=5 , max_length=100)
    email : EmailStr | None = Field(default=None,max_length=120)
    image_file : str | None = Field(default = None,min_length=1,max_length=250)


class PostBase(BaseModel):
    title : str = Field(min_length = 1 , max_length = 100)
    content : str = Field(min_length = 5)
    author : str = Field(min_length = 1, max_length = 50)

class PostCreate(PostBase):
    published: bool = False
    user_id: int

class PostUpdated(PostBase):
    content : str = Field(min_length=10,default=None)
    title : str = Field(min_length=1,max_length=50,default= None)

class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes = True)
    id : int
    date_posted : str 
    published : bool
    user_id: int
    author: UserResponse