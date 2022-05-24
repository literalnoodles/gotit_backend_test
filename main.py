from cmath import inf
import json
from fastapi import Depends, HTTPException, Request, Response
from fastapi import FastAPI
from fastapi.responses import (RedirectResponse, HTMLResponse)
from auth import AuthHandler
from playhouse.shortcuts import model_to_dict
from peewee import JOIN
from exception import RequiresExtraInfoException
from schemas import (
    Credentials,
    AdditionalInfo,
    PostCreate
)
from models import (
    User,
    Post,
    PostLike
)
from helper import get_likes_subquery
from google.oauth2 import id_token
from google.auth.transport import requests
import requests as rq
from dotenv import load_dotenv
import os
load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
app = FastAPI()
auth_handler = AuthHandler()


@app.get('/login', response_class=HTMLResponse, include_in_schema=False)
def login():
    return """
        <html>
            <head>
                <title>Login</title>
            </head>
            <body>
                <script src="https://accounts.google.com/gsi/client" async defer></script>
                <div id="g_id_onload"
                    data-client_id="759432235722-upj1ssj87tght2ciova3kskgd44q9k3n.apps.googleusercontent.com"
                    data-callback="handleCredentialResponse">
                </div>
                <div class="g_id_signin"
                    data-type="standard"
                    data-size="large"
                    data-theme="outline"
                    data-text="sign_in_with"
                    data-shape="rectangular"
                    data-logo_alignment="left">
                </div>
                <fb:login-button
                    scope="public_profile,email"
                    onlogin="checkLoginState();">
                </fb:login-button>
                <script>
                    function handleCredentialResponse(response) {
                        console.log({google_access_token: response.credential})
                    }
                </script>
                <script>
                    window.fbAsyncInit = function() {
                        FB.init({
                            appId      : '473728743238650',
                            cookie     : true,
                            xfbml      : true,
                            version    : 'v13.0'
                        });

                        FB.AppEvents.logPageView();
                    };

                    function checkLoginState() {
                        FB.getLoginStatus(function(response) {
                            statusChangeCallback(response);
                        });
                    }

                    function statusChangeCallback(response) {
                        console.log({facebook_access_token: response.authResponse.accessToken})
                    }

                    (function(d, s, id){
                        var js, fjs = d.getElementsByTagName(s)[0];
                        if (d.getElementById(id)) {return;}
                        js = d.createElement(s); js.id = id;
                        js.src = "https://connect.facebook.net/en_US/sdk.js";
                        fjs.parentNode.insertBefore(js, fjs);
                    }(document, 'script', 'facebook-jssdk'));
                </script>
            </body>
        </html>
    """

# ------------------------ Handle Accounts ------------------------ #


@app.post('/api/login/google')
def login_google(credentials: Credentials):
    access_token = credentials.access_token
    # verify google token
    try:
        idinfo = id_token.verify_oauth2_token(
            access_token, requests.Request(), GOOGLE_CLIENT_ID)
        # check if email is already exists in database
        exists_user = (User.select()
                       .where(User.email == idinfo["email"])
                       .first())
        if exists_user and exists_user.platform == "facebook":
            raise HTTPException(
                status_code=400,
                detail="This email is already exists")
        if not exists_user:
            # register new user to database
            db_user = User(
                email=idinfo["email"],
                platform="google"
            )
            db_user.save()
        # return access_token for user
        token = auth_handler.encode_token(idinfo["email"])
        return {"access_token": token}
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post('/api/login/facebook')
def login_facebook(credentials: Credentials):
    access_token = credentials.access_token
    try:
        res = rq.get(
            "https://graph.facebook.com/me?access_token=&fields=email",
            params={
                "access_token": access_token,
                "fields": "email"})

        res.raise_for_status()
        info = res.json()
        # check if email is already exists in database
        exists_user = (User.select()
                       .where(User.email == info["email"])
                       .first())
        if exists_user and exists_user.platform == "google":
            raise HTTPException(
                status_code=400,
                detail="This email is already exists")
        if not exists_user:
            # register new user to database
            db_user = User(
                email=info["email"],
                platform="facebook"
            )
            db_user.save()
        # return access_token for user
        token = auth_handler.encode_token(info["email"])
        return {"access_token": token}
    except rq.exceptions.HTTPError as e:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.patch('/api/users/self', status_code=204)
def add_information(
    details: AdditionalInfo,  # payload
    user_info=Depends(auth_handler.auth_wrapper)  # authentication
):
    # validate user id
    user = (User.select()
                .where(User.id == user_info['id'])
                .first())
    if not details.name:
        raise HTTPException(status_code=400, detail="You need to provide name")
    if user.platform == "facebook" and not details.phone_number:
        raise HTTPException(status_code=400,
                            detail="You need to provide phone number")
    if user.platform == "google" and not details.occupation:
        raise HTTPException(
            status_code=400,
            detail="You need to provide occupation information")
    user.name = details.name
    if details.phone_number:
        user.phone_number = details.phone_number
    if details.occupation:
        user.occupation = details.occupation
    user.save()
    return Response(status_code=204)

# ------------------------ Handle Posts ------------------------ #


@app.post('/api/posts',
          dependencies=[Depends(auth_handler.verify_information)])
def create_post(
    post_data: PostCreate,
    user_info=Depends(auth_handler.auth_wrapper)  # authentication
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


@app.post('/api/posts/{post_id}/likes',
          dependencies=[Depends(auth_handler.verify_information)])
def like_post(
    post_id,
    user_info=Depends(auth_handler.auth_wrapper)  # authentication
):
    """
        Like post
    """
    # check if post exists
    post = Post.select().where(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=401,
            detail="This post does not exists")
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
        ) .join(
            User,
            on=Post.author == User.id) .join(
                likes_subquery,
                JOIN.LEFT_OUTER,
                on=likes_subquery.c.post_id == Post.id) .order_by(
                    Post.created) .group_by(
                        Post.id) .paginate(
                            page,
            items_per_page) .dicts())

    # add short description and likes for each post
    for post in posts:
        post["likes"] = json.loads(
            '[' + post["likes"] + ']') if post["likes"] else []
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
            likes_subquery.c.likes) .join(
            User,
            on=Post.author == User.id) .join(
                likes_subquery,
                JOIN.LEFT_OUTER,
                on=likes_subquery.c.post_id == Post.id) .where(
                    Post.author == user_id) .order_by(
                        Post.created) .dicts())
    # adding short description for each posts
    for post in posts:
        post["likes"] = json.loads(
            '[' + post["likes"] + ']') if post["likes"] else []
        post["short_description"] = post["body"][:100]
    return [post for post in posts]


@app.get("/api/posts/{post_id}", dependencies=[
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
            likes_subquery.c.likes) .join(
            User,
            on=Post.author == User.id) .join(
                likes_subquery,
                JOIN.LEFT_OUTER,
                on=likes_subquery.c.post_id == Post.id) .where(
                    Post.id == post_id) .dicts())

    posts = [post for post in posts]
    if not posts:
        return None
    post = posts[0]

    # adding short description for post
    post["likes"] = json.loads(
        '[' + post["likes"] + ']') if post["likes"] else []
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


@app.get('/user/extra_information',
         response_class=HTMLResponse,
         include_in_schema=False)
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
