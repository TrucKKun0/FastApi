from typing import Annotated
from fastapi import FastAPI, Request , HTTPException,status,Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as starletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import models
from schema import PostCreate,PostResponse,UserCreate,UserResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import Base,engine,get_db




Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media",StaticFiles(directory="media"),name='media')
templates = Jinja2Templates(directory="templates")

# posts : list[dict]=[
#     {
#         "id" : 1,
#         "title" : "First Post",
#         "content" : "This is the content of the first post.",
#         "published" : True,
#         "author" : "John Doe",
#         "date_posted" : "2026/08/02"
#     },
#     {
#         "id" : 2,
#         "title" : "Second Post",    
#         "content" : "This is the content of the second post.",
#         "published" : False,
#         "author" : "Jane Doe",
#         "date_posted" : "2079/20/01"
#     },
#     {
#         "id" : 3,
#         "title" : "Third Post",
#         "content" : "This is the content of the third post.",
#         "published" : True,
#         "author" : "John Doe",
#         "date_posted" : "2082/24/01"
#     }
# ]

@app.get("/", include_in_schema=False)
@app.get("/posts", include_in_schema=False)
def home(request : Request, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})

@app.post(
        "/api/users",
        response_model=UserResponse,
        status_code= status.HTTP_201_CREATED
)
def create_user(user : UserCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.username == user.username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Username already exits")
     
    result = db.execute(select(models.User).where(models.User.email == user.email))
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="email already exits")
    new_user = models.User(
        username = user.username,
        email = user.email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/api/user/{user_id}", response_model=UserResponse)
def get_user(user_id : int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found with that user id. Please try again")


@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
def get_user_posts(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found the user id")
    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts



@app.get("/post/{post_id}", include_in_schema=False)
def post_page(request: Request, post_id : int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(request, "post.html", {"post": post, "title": title})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/api/posts", response_model=list[PostResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return posts


@app.get("/user/{user_id}/posts")
def get_user_all_posts(request: Request, db: Annotated[Session, Depends(get_db)], user_id : int):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": f"{user.username}'s Posts"})



@app.get("/api/post/{post_id}/", response_model=PostResponse)
def get_one_post(post_id : int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "Post not found")

@app.exception_handler(starletteHTTPException)
def general_http_exception_handler(request : Request, exception : starletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occured. Please check your request and try again"
    )
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=exception.status_code,content={"details" : message})
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code" : exception.status_code,
            "title" : exception.status_code,
            "message" : message
        },
        status_code=exception.status_code
    )

@app.post(
        "/api/posts",
        response_model=PostResponse,
        status_code= status.HTTP_201_CREATED
)
def create_post(post : PostCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,detail="User not found with the user id")
    new_post = models.Post(
        title = post.title,
        content = post.content,
        user_id = post.user_id
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request : Request,exception : RequestValidationError):
    if request.url.path.startswith("/api"):
         return JSONResponse(
             status_code= status.HTTP_422_UNPROCESSABLE_CONTENT,
             content = {"detail" : exception.errors()}
         )
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            'status_code' : status.HTTP_422_UNPROCESSABLE_CONTENT,
            'title' : status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message" : "Invalid request with invalid datatype"
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
    )