
from schema import PostCreate,PostResponse,UserCreate,UserResponse,PostUpdated,UserUpdate
from typing import Annotated
from fastapi import FastAPI, Request , HTTPException,status,Depends,APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import models
from database import get_db

router = APIRouter()

@router.delete("/{post_id}/", status_code = status.HTTP_204_NO_CONTENT)
async def delete_one_post(post_id : int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "Post not found")
    await db.delete(post)
    await db.commit()

@router.put("/{post_id}/", response_model=PostUpdated)
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

@router.patch("/{post_id}/", response_model=PostUpdated)
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

@router.post(
        "",
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

@router.get("/{post_id}/", response_model=PostResponse)
async def get_one_post(post_id : int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "Post not found")

@router.get("", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()
    return posts
