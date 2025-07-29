from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from database import get_db
from models import User, Product
from schemas import ProductOut, WooCommerceCredentials, CreateCheckoutSessionRequest
from token_module import get_current_user
from services.woocommerce_sync import fetch_and_store_products_from_woocommerce
from services.stripe_service import (
    create_checkout_session,
    cancel_user_subscription,
    create_credits_checkout_session,
)
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/products", response_model=list[ProductOut], tags=["products"])
def get_my_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Product).filter(Product.owner_id == current_user.id).all()

@router.post("/products/sync", tags=["products"])
def sync_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        fetch_and_store_products_from_woocommerce(db, current_user)
        return {"message": "Products synced successfully"}
    except Exception as e:
        print(f"[sync_products error]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/credits", tags=["credits"])
def get_credits(current_user: User = Depends(get_current_user)):
    return {"credits": current_user.credits}

@router.post("/subscribe", tags=["subscription"])
def subscribe(
    req: CreateCheckoutSessionRequest,  # Πρέπει να έχει πεδίο plan_id
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        checkout_url = create_checkout_session(current_user, req.plan_id)
        return {"checkout_url": checkout_url}
    except Exception as e:
        print(f"[subscribe error]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cancel-subscription", tags=["subscription"])
def cancel_subscription(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        success = cancel_user_subscription(current_user)
        if not success:
            raise HTTPException(status_code=404, detail="No active subscription to cancel")
        return {"message": "Subscription cancelled"}
    except Exception as e:
        print(f"[cancel_subscription error]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/buy-credits", tags=["credits"])
async def buy_credits(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        data = await request.json()
        credits = data.get("credits")
        if not credits or not isinstance(credits, int) or credits <= 0:
            raise HTTPException(status_code=400, detail="Invalid number of credits")
        checkout_url = create_credits_checkout_session(current_user, credits)
        return {"checkout_url": checkout_url}
    except Exception as e:
        print(f"[buy_credits error]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/woocommerce-credentials", response_model=WooCommerceCredentials, tags=["woocommerce"])
def get_woocommerce_credentials(current_user: User = Depends(get_current_user)):
    has_credentials = (
        current_user.woocommerce_url is not None and
        current_user.consumer_key is not None and
        current_user.consumer_secret is not None
    )
    return {
        "has_credentials": has_credentials,
        "woocommerce_url": current_user.woocommerce_url,
        "consumer_key": current_user.consumer_key,
        "consumer_secret": current_user.consumer_secret,
    }

@router.put("/woocommerce-credentials", tags=["woocommerce"])
def update_woocommerce_credentials(creds: WooCommerceCredentials, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.woocommerce_url = creds.woocommerce_url
    current_user.consumer_key = creds.consumer_key
    current_user.consumer_secret = creds.consumer_secret
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"message": "WooCommerce credentials updated"}

@router.delete("/woocommerce-credentials", tags=["woocommerce"])
def delete_woocommerce_credentials(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.woocommerce_url = None
    current_user.consumer_key = None
    current_user.consumer_secret = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"message": "WooCommerce credentials deleted"}
