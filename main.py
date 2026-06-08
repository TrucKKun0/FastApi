from fastapi import FastAPI, Request , HTTPException,status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as starletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from schema import PostCreate,PostResponse


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

posts : list[dict]=[
    {
        "id" : 1,
        "title" : "First Post",
        "content" : "This is the content of the first post.",
        "published" : True,
        "author" : "John Doe",
        "date_posted" : "2026/08/02"
    },
    {
        "id" : 2,
        "title" : "Second Post",    
        "content" : "This is the content of the second post.",
        "published" : False,
        "author" : "Jane Doe",
        "date_posted" : "2079/20/01"
    },
    {
        "id" : 3,
        "title" : "Third Post",
        "content" : "This is the content of the third post.",
        "published" : True,
        "author" : "John Doe",
        "date_posted" : "2082/24/01"
    }
]

@app.get("/",include_in_schema=False)
@app.get("/posts",include_in_schema=False)
def home(request : Request):
    context = {
        "posts" : posts,
        "title" : "Home"
    }
    return templates.TemplateResponse(request,"home.html", context)


@app.get("/post/{post_id}",include_in_schema=False)
def post_page(request: Request, post_id : int):
    for post in posts : 
        if post['id'] == post_id:
            title = post['title'][:50]
            return templates.TemplateResponse(request,"post.html",{"post" : post ,"title" : title})
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found in dictneory")


@app.get("/api/posts",response_model=list[PostResponse])
def get_posts():
    return posts


@app.get("/api/post/{post_id}/",response_model=PostResponse)
def get_one_post(post_id : int):
    for post in posts:
        if post["id"] == post_id:
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
def create_post(post : PostCreate):
    new_id = max(p["id"] for p in posts) + 1 if posts else 1
    new_post = {
        "id" : new_id,
        "author" : post.author,
        "title" : post.title,
        "content" : post.content,
        "published" : post.published,
        "date_posted" : "08/06/2026"
    }
    posts.append(new_post)
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