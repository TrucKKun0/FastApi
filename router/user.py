from schema import (PostCreate,
                    PostResponse,
                    UserCreate,
                    UserPrivate,
                    UserPublic,
                    Token,
                    PostUpdated,
                    UserUpdate,
                    PaginatedPostResponse,
                    ChangePasswordRequest,
                    ForgetPasswordRequest,
                    ResetPasswordRequest)
from typing import Annotated
from fastapi import FastAPI, Request , HTTPException,status,Depends,APIRouter,UploadFile,Query,BackgroundTasks
from sqlalchemy import select,func
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import UnidentifiedImageError
from starlette.concurrency import run_in_threadpool
from image_utils import delete_profile_image,process_profile_image,upload_profile_image
from sqlalchemy.orm import selectinload
import models
from database import get_db
from datetime import timedelta,UTC,datetime
from fastapi.security import OAuth2PasswordRequestForm
from auth import create_access_token,CurrentUser,hash_password,vefiry_accesstoken,verify_password,generate_token,hash_reset_token
from email_utlis import send_password_reset_email
from config import settings
from sqlalchemy import Delete as sql_delete
from botocore.exceptions import ClientError




router = APIRouter()


@router.post(
        "",
        response_model=UserPublic,
        status_code= status.HTTP_201_CREATED
)
async def create_user(user : UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    print(user)
    result = await db.execute(select(models.User).where(func.lower(models.User.username) == user.username.lower()))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Username already exits")
     
    result = await db.execute(select(models.User).where(func.lower(models.User.email) == user.email.lower()))
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="email already exits")
    new_user = models.User(
        username = user.username,
        email = user.email.lower(),
        password_hash = hash_password(user.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/token",response_model=Token)
async def login_for_access_token(
    form_data : Annotated[OAuth2PasswordRequestForm,Depends()],
    db : Annotated[AsyncSession,Depends(get_db)]
):
    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == form_data.username.lower())
    )
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password,user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail = "Incorrect email or password",
            header  =  {"WWW-Authenticate"  : "Bearer"}
        )
    access_token_expires = timedelta(minutes=settings.access_token_expires_minutes)
    access_token = create_access_token(
        data = {"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    return Token(access_token = access_token,token_type="bearer")

@router.get("/me",response_model=UserPrivate)
async def get_current_user(current_user : CurrentUser):
  return current_user
@router.get("{user_id}", response_model=UserPublic)
async def get_user(user_id : int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found with that user id. Please try again")


@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(
    user_id: int, 
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int,Query(ge=0)] = 0,
    limit : Annotated[int,Query(ge=0,le=100)] = 10
    ):
    
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found the user id")
    count_result = await db.execute(select(func.count()).select_from(models.Post).where(models.Post.user_id == user_id))
    total = count_result.scalars() or 0
    result = await db.execute(select(models.Post)
                              .options(selectinload(models.Post.author))
                              .where(models.Post.user_id == user_id)
                              .order_by(models.Post.date_posted.desc())
                              .offset(skip)
                              .limit(limit),)
    posts = result.scalars().all()
    return posts

@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(user_id : int, current_user : CurrentUser, db : Annotated[AsyncSession, Depends(get_db)], user_update : UserUpdate):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_NOT_FOUND, detail = "Not authorized to update")
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    
    if user_update.username is not None and user_update.username != user.username:
        result = await db.execute(select(models.User).where(func.lower(models.User.username) == user_update.username.lower()))
        exisiting_user = result.scalars().first()
        if exisiting_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Same username as previous")
        
    
    if user_update.email is not None and user_update.email != user.email:
        result = await db.execute(select(models.User).where(func.lower(models.User.email) == user_update.email.lower()))
        exisiting_user = result.scalars().first()
        if exisiting_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Same email as previous")
    
    if user_update.username is not None :
        user.username = user_update.username
    if user_update.email is not None :
        user.email = user_update.email
    
  
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}",status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id : int,db : Annotated[AsyncSession,Depends(get_db)],current_user : CurrentUser):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_NOT_FOUND, detail = "Not authorized to delete")
        
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found with userid")
    old_filename = user.image_file
    await db.delete(user)
    await db.commit()
    if old_filename:
        await delete_profile_image(old_filename)


@router.patch("/{user_id}/pricture",response_model=UserPrivate)
async def upload_profile_picture(
    user_id : int,
    file : UploadFile,
    current_user : CurrentUser,
    db : Annotated[AsyncSession, Depends(get_db)]
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not authorized to update this profile")
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large to upload. Please try again"
        )
    try :
        process_bytes,new_filename = await run_in_threadpool(process_profile_image, content)
    except UnidentifiedImageError as err:
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file. Please upload a valid image (JPEG,PNG,GIF,WebP)"
        )from err
    try:
        await upload_profile_image(process_bytes,new_filename)
    except ClientError as err:
        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image. Please Try again"
        )from err
    old_filename = current_user.image_file
    current_user.image_file = new_filename
    await db.commit()
    await db.refresh(current_user)
    if old_filename:
        delete_profile_image(old_filename)
    return current_user

@router.post("/forget-password",status_code=status.HTTP_202_ACCEPTED)
async def forget_password(
    request_data:ForgetPasswordRequest,
    background_task : BackgroundTasks,
    db : Annotated[AsyncSession,Depends(get_db)]
):
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == request_data.email.lower(),
        )
    )
    user = result.scalars().first()
    if user :
        await db.execute(
            sql_delete(models.PasswordResetToken).where(
                models.PasswordResetToken.user_id == user.id,
            )
        )
        token = generate_token()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.reset_token_expire_minute
        )
        reset_token = models.PasswordResetToken(
            user_id = user.id,
            token_hash = token_hash,
            expires_at = expires_at
        )
        db.add(reset_token)
        await db.commit()
        background_task.add_task(
            send_password_reset_email,
            to_email = user.email,
            username = user.username,
            token = token
        )
        return {
            "message" : "If  an account exits with this email, you will recieve a password reset instruction"
        }

@router.post("/reset-password",status_code=status.HTTP_200_OK)
async def reset_password(
    request_data : ResetPasswordRequest,
    db : Annotated[AsyncSession,Depends(get_db)]
):
    token_hash = hash_reset_token(request_data.token)
    result = await db.execute(
        select(models.PasswordResetToken).where(
            models.PasswordResetToken.token_hash == token_hash
        )
    )
    reset_token = result.scalars().first()
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ivalid or expired token"
        )
    if reset_token.expires_at < datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    result = await db.execute(
        select(models.User).where(models.User.id == reset_token.user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expire token"
        )
    user.password_hash =hash_password(request_data.new_password)
    await db.execute(
        sql_delete(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == user.id
        )
    )
    await db.commit()
    return {
        "message" : "Password reset successfully. You can now log in with your new password."
    }

@router.patch("/me/password",status_code=status.HTTP_200_OK)
async def change_password(
    password_data : ChangePasswordRequest,
    current_user : CurrentUser,
    db : Annotated[AsyncSession,Depends(get_db)]
):
    if not verify_password(password_data.current_password,current_user.password_hash):
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    current_user.password_hash= hash_password(password_data.new_password)
    await db.execute(
        sql_delete(models.PasswordResetToken.user_id).where(
            models.PasswordResetToken.user_id == current_user.id
        )
    )
    await db.commit()
    return {
        "message" : "Password changed successfully"
    }

@router.delete("{user_id}/delete_profile_picture/")
async def delete_user_profile_picture(
    user_id : int,
    current_user : CurrentUser,
    db : Annotated[AsyncSession, Depends(get_db)]
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code= status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access to delete profile picture"
        )
    old_filename = current_user.image_file
    if old_filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete"
        )
    current_user.image_file = None
    await db.commit()
    await db.refresh(current_user)
    await delete_profile_image(old_filename)
    return current_user

