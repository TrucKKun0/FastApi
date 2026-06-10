from typing import Annotated
from fastapi import FastAPI, Request , HTTPException,status,Depends
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as starletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import models
from schema import PostCreate,PostResponse,UserCreate,UserResponse,PostUpdated,UserUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from database import Base,engine,get_db
from contextlib import asynccontextmanager
from fastapi.exception_handlers import(
    http_exception_handler,
    request_validation_exception_handler
)





@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

    await engine.dispose()
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media",StaticFiles(directory="media"),name='media')
templates = Jinja2Templates(directory="templates")


@app.get("/", include_in_schema=False)
@app.get("/posts", include_in_schema=False)
async def home(request : Request, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})

@app.post(
        "/api/users",
        response_model=UserResponse,
        status_code= status.HTTP_201_CREATED
)
async def create_user(user : UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.username == user.username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Username already exits")
     
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="email already exits")
    new_user = models.User(
        username = user.username,
        email = user.email
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@app.get("/api/user/{user_id}", response_model=UserResponse)
async def get_user(user_id : int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found with that user id. Please try again")


@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found the user id")
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts



@app.get("/post/{post_id}", include_in_schema=False)
async def post_page(request: Request, post_id : int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(request, "post.html", {"post": post, "title": title})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/api/posts", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()
    return posts


@app.get("/user/{user_id}/posts")
async def get_user_all_posts(request: Request, db: Annotated[AsyncSession, Depends(get_db)], user_id : int):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    result = await db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": f"{user.username}'s Posts"})



@app.get("/api/post/{post_id}/", response_model=PostResponse)
async def get_one_post(post_id : int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "Post not found")


@app.delete("/api/post/{post_id}/", status_code = status.HTTP_204_NO_CONTENT)
async def delete_one_post(post_id : int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "Post not found")
    await db.delete(post)
    await db.commit()

@app.put("/api/post/{post_id}/", response_model=PostUpdated)
async def update_post_full(post_id : int, db: Annotated[AsyncSession, Depends(get_db)],post_data : PostCreate):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "Post not found")
    if post.user_id != post_data.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This user is not authorized to make an edit to this post")
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id
    await db.commit()
    await db.refresh(post)
    return post


@app.patch("/api/user/{user_id}", response_model=UserResponse)
async def update_user(user_id : int, db : Annotated[(AsyncSession,Depends(get_db))],user_update : UserUpdate):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    
    if user_update.username is not None and user_update.username != user.username:
        result = await db.execute(select(models.User).where(models.User.username == user_update.username))
        exisiting_user = result.scalars().first()
        if exisiting_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Same username as previous")
        
    
    if user_update.email is not None and user_update.email != user.email:
        result = await db.execute(select(models.User).where(models.User.email == user_update.email))
        exisiting_user = result.scalars().first()
        if exisiting_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Same email as previous")
    
    if user_update.username is not None :
        user.username = user_update.username
    if user_update.email is not None :
        user.email = user_update.email
    
    if user_update.image_file is not None :
        user.image_file = user_update.image_file
    await db.commit()
    await db.refresh(user)
    return user

@app.delete("/api/user/{user_id}",status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id : int,db : Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found with userid")
    await db.delete(user)
    await db.commit()



@app.patch("/api/post/{post_id}/", response_model=PostUpdated)
async def update_post_partial(post_id : int, db: Annotated[AsyncSession, Depends(get_db)],post_data : PostUpdated):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "Post not found")
    update_data = post_data.model_dump(exclude=True)
    for field , value in update_data.items():
        setattr(post,field,value)
    await db.commit()
    await db.refresh(post)
    return post



@app.exception_handler(starletteHTTPException)
async def general_http_exception_handler(request : Request, exception : starletteHTTPException):
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request,exception)
    message = (
        exception.detail
        if exception.detail
        else "An error occured. Please check your request and try again"
    )
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
async def create_post(post : PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,detail="User not found with the user id")
    new_post = models.Post(
        title = post.title,
        content = post.content,
        published = post.published,
        user_id = post.user_id
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)
    return new_post

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request : Request,exception : RequestValidationError):
    if request.url.path.startswith("/api"):
         return await http_exception_handler(request,exception)
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