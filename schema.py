from pydantic import BaseModel,ConfigDict,Field,EmailStr

from datetime import datetime

class UserBase(BaseModel):
    username : str = Field(min_length=1, max_length=100)
    email : EmailStr = Field(max_length=120) 
class UserCreate(UserBase):
    password  : str = Field(min_length=8)
class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes= True)
    id : int
    image_file : str | None
    image_path  : str
    username : str
class UserPrivate(UserPublic):
    email : EmailStr
 
class Token(BaseModel):
    access_token : str
    token_type : str

class UserUpdate(BaseModel):
    username : str | None = Field(default=None)
    email : EmailStr | None = Field(default=None)
    image_file : str | None = Field(default=None)


class PostBase(BaseModel):
    title : str = Field(min_length = 1 , max_length = 100)
    content : str = Field(min_length = 5)
    author : str | None = Field(default=None)

class PostCreate(PostBase):
    pass
class PostUpdated(BaseModel):
    title : str | None = Field(default=None)
    content : str | None = Field(default=None)
    author : str | None = Field(default=None)

class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes = True)
    id : int
    date_posted : datetime
    user_id: int
    author: UserPublic