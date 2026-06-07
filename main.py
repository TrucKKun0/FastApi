from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

posts : list[dict]=[
    {
        "id" : 1,
        "title" : "First Post",
        "content" : "This is the content of the first post.",
        "published" : True
    },
    {
        "id" : 2,
        "title" : "Second Post",    
        "content" : "This is the content of the second post.",
        "published" : False
    },
    {
        "id" : 3,
        "title" : "Third Post",
        "content" : "This is the content of the third post.",
        "published" : True
    }
]

@app.get("/")
@app.get("/posts")
def home(request : Request):
    context = {
        "posts" : posts,
        "title" : "Home"
    }
    return templates.TemplateResponse(request,"home.html",context)
@app.get("/api/posts")
def get_posts():
    return {"data": posts}
