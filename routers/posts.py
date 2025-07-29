from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

import models
import schemas
import database
from services import post_generator
from token_module import get_current_user

router = APIRouter()


@router.post("/me/posts/image", response_model=schemas.PostOut)
def create_image_post(
    post_data: schemas.PostCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    product = db.query(models.Product).filter_by(id=post_data.product_id, user_id=current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    post = post_generator.generate_image_post(product, post_data.mode)

    new_post = models.Post(
        product_id=product.id,
        type="image",
        caption=post["caption"],
        media_urls=json.dumps(post["media_urls"]),
        mode=post_data.mode
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post
