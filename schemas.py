from pydantic import BaseModel, HttpUrl, EmailStr
from typing import List, Optional
from datetime import datetime


class WooCommerceCredentials(BaseModel):
    woocommerce_url: str
    consumer_key: str
    consumer_secret: str


class CreateCheckoutSessionRequest(BaseModel):
    plan_id: str


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(UserBase):
    id: int
    is_active: bool
    credits: int
    woocommerce_url: Optional[str]
    consumer_key: Optional[str]
    consumer_secret: Optional[str]

    class Config:
        orm_mode = True


class UserUpdateWoocommerce(BaseModel):
    woocommerce_url: str
    consumer_key: str
    consumer_secret: str


class Token(BaseModel):
    access_token: str
    token_type: str


class ProductBase(BaseModel):
    name: str
    description: Optional[str]
    price: Optional[str]
    image_url: Optional[HttpUrl]
    permalink: Optional[HttpUrl]
    categories: Optional[str]


class ProductCreate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True


class PostBase(BaseModel):
    product_id: int
    type: str
    media_urls: List[str]
    caption: Optional[str]
    mode: Optional[str]


class PostCreate(PostBase):
    pass


class PostOut(PostBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class CreditResponse(BaseModel):
    message: str
    remaining_credits: int


# ----------- ΝΕΑ SCHEMAS ΓΙΑ TEMPLATES -----------

class TemplateBase(BaseModel):
    name: str
    type: str  # image, carousel, video
    file_path: str


class TemplateCreate(TemplateBase):
    owner_id: Optional[int]


class TemplateOut(TemplateBase):
    id: int
    owner_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
