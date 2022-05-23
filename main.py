import json
from fastapi import Depends, HTTPException, Request, Response
from fastapi import FastAPI
from fastapi.responses import (RedirectResponse, HTMLResponse)
from auth import AuthHandler
from playhouse.shortcuts import model_to_dict
from peewee import JOIN
from exception import RequiresExtraInfoException
from schemas import (
    RegisterInfo,
    LoginInfo,
    AdditionalInfo,
    PostCreate
)
from models import (
    User,
    Post,
    PostLike
)
from helper import get_likes_subquery

app = FastAPI()
auth_handler = AuthHandler()

# ------------------------ Handle Accounts ------------------------ #
@app.post('/api/users', status_code=201)
def register(details: RegisterInfo):
    """
        Register new user
    """
    if not details.password or not details.email:
        raise HTTPException(status_code=400, detail="You need to provide email and/or password")
    if details.platform not in ['facebook', 'google']:
        raise HTTPException(status_code=400, detail="Platform should be facebook or google")
    # check if email is already exists in database
    count_exists_user = (User.select()
                             .where(User.email == details.email)
                             .count())
    if count_exists_user:
        raise HTTPException(status_code=400, detail="This email is already exists")
    # else register new user to database
    db_user = User(
        email=details.email,
        password=auth_handler.get_password_hash(details.password),
        platform=details.platform
    )
    db_user.save()
    return model_to_dict(db_user)

@app.patch('/api/users/self', status_code=204)
def add_information(
    details: AdditionalInfo, # payload
    user_info=Depends(auth_handler.auth_wrapper) # authentication
):
    # validate user id
    user = (User.select()
                .where(User.id == user_info['id'])
                .first())
    if not details.name:
        raise HTTPException(status_code=400, detail="You need to provide name")
    if user.platform == "facebook" and not details.phone_number:
        raise HTTPException(status_code=400, detail="You need to provide phone number")
    if user.platform == "google" and not details.occupation:
        raise HTTPException(status_code=400, detail="You need to provide occupation information")
    user.name = details.name
    if details.phone_number:
        user.phone_number = details.phone_number
    if details.occupation:
        user.occupation = details.occupation
    user.save()
    return Response(status_code=204)

@app.post('/api/users/login')
def login(details: LoginInfo):
    """
        Login user and get access token
    """
    # check password
    user = (User.select()
                .where(User.email == details.email)
                .first())
    if not user or not auth_handler.verify_password(details.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = auth_handler.encode_token(user.id)
    return {"access_token": token}

# ------------------------ Handle Posts ------------------------ #

@app.post('/api/posts', dependencies=[Depends(auth_handler.verify_information)])
def create_post(
    post_data: PostCreate,
    user_info=Depends(auth_handler.auth_wrapper) # authentication
):
    """
        Create a new post
    """
    new_post = Post(
        title=post_data.title,
        body=post_data.body,
        author=user_info['id']
    )
    new_post.save()
    return model_to_dict(new_post)

@app.post('/api/posts/{post_id}/likes', dependencies=[Depends(auth_handler.verify_information)])
def like_post(
    post_id,
    user_info=Depends(auth_handler.auth_wrapper) # authentication
):
    """
        Like post
    """
    # check if post exists
    post = Post.select().where(Post.id==post_id).first()
    if not post:
        raise HTTPException(status_code=401, detail="This post does not exists")
    # check if user already like the post
    post_like = (PostLike.select()
                         .where(PostLike.post_id == post_id)
                         .where(PostLike.user_id == user_info['id'])
                         .first())
    if post_like:
        return Response(status_code=204)
    new_like = PostLike(
        post_id=int(post_id),
        user_id=user_info['id']
    )
    new_like.save()
    return model_to_dict(new_like)

@app.get('/api/posts', dependencies=[
    Depends(auth_handler.auth_wrapper),
    Depends(auth_handler.verify_information)
])
def list_posts(
    page: int = 1
):
    """
        List all posts in the home page and likes for each post
        The likes for each post will be sorted by time
    """
    items_per_page = 3
    likes_subquery = get_likes_subquery()
    posts = (
        Post.select(
            User.name.alias("author_name"),
            Post.title,
            Post.body,
            Post.created,
            likes_subquery.c.likes,
        )
        .join(User, on=Post.author == User.id)
        .join(likes_subquery, JOIN.LEFT_OUTER, on=likes_subquery.c.post_id == Post.id)
        .order_by(Post.created)
        .group_by(Post.id)
        .paginate(page, items_per_page)
        .dicts()
    )

    # add short description and likes for each post
    for post in posts:
        post["likes"] = json.loads('[' + post["likes"] + ']') if post["likes"] else []
        post["short_description"] = post["body"][:100]
    return [post for post in posts]

@app.get("/api/users/{user_id}/posts", dependencies=[
    Depends(auth_handler.auth_wrapper),
    Depends(auth_handler.verify_information)
])
def list_posts_for_user(
    user_id: int
):
    """
        List all posts in the home page by an user
        The likes for each post will be sorted by time
    """
    likes_subquery = get_likes_subquery()
    posts = (
        Post.select(
            User.name.alias("author_name"),
            Post.title,
            Post.body,
            Post.created,
            likes_subquery.c.likes
        )
        .join(User, on=Post.author == User.id)
        .join(likes_subquery, JOIN.LEFT_OUTER, on=likes_subquery.c.post_id == Post.id)
        .where(Post.author == user_id)
        .order_by(Post.created)
        .dicts()
    )
    # adding short description for each posts
    for post in posts:
        post["likes"] = json.loads('[' + post["likes"] + ']') if post["likes"] else []
        post["short_description"] = post["body"][:100]
    return [post for post in posts]

@app.get("/api/posts/{post_id}",dependencies=[
    Depends(auth_handler.auth_wrapper),
    Depends(auth_handler.verify_information)
])
def get_post(
    post_id: int
):
    """
        get full content of a post
    """
    likes_subquery = get_likes_subquery()
    posts = (
        Post.select(
            User.name.alias("author_name"),
            Post.title,
            Post.body,
            Post.created,
            likes_subquery.c.likes
        )
        .join(User, on=Post.author == User.id)
        .join(likes_subquery, JOIN.LEFT_OUTER, on=likes_subquery.c.post_id == Post.id)
        .where(Post.id == post_id)
        .dicts()
    )

    posts = [post for post in posts]
    if not posts:
        return None
    post = posts[0]

    # adding short description for post
    post["likes"] = json.loads('[' + post["likes"] + ']') if post["likes"] else []
    post["short_description"] = post["body"][:100]
    return post


# ------------------------ Handle extra information ------------------------ #
@app.exception_handler(RequiresExtraInfoException)
async def exception_handler(request: Request, exc: RequiresExtraInfoException) -> Response:
    # if user has missing information -> after login they will be
    # redirected to a form to provide additional information
    return RedirectResponse(url='/user/extra_information')

# handle extra information form
# this should be a frontend page so I only implemented as a placeholder
@app.get('/user/extra_information', response_class=HTMLResponse, include_in_schema=False)
def extra_information():
    """
        frontend form url
    """
    return """
        <html>
            <head>
                <title>Extra information</title>
            </head>
            <body>
                <h1>Please provide some extra information</h1>
                <form>
                    <label for="name">Name:</label><br>
                    <input type="text" id="name" name="name" required><br>
                    <label for="phone_number">Phone number:</label><br>
                    <input type="tel" id="phone_number" name="phone_number" placeholder="123-45-678"><br>
                    <label for="occupation">Occupation:</label><br>
                    <input type="text" id="occupation" name="occupation"><br>
                    <br>
                    <input type="submit" value="Submit">
                </form> 
            </body>
        </html>
    """