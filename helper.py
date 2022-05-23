from models import (
    User, PostLike
)
from peewee import fn

def get_likes_subquery():
    """
        get subquery for all post with author name and like time sorted descending
        so that the last like show first
    """
    UserAlias = User.alias()
    return (
        PostLike.select(
            PostLike.post_id,
            fn.GROUP_CONCAT(
                fn.json_object("name", UserAlias.name, "created", PostLike.created)
            )
            .order_by(PostLike.created.desc())
            .alias("likes"),
        )
        .join(UserAlias, on=UserAlias.id == PostLike.user_id)
        .group_by(PostLike.post_id)
    )