from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

# --- project imports (άφησέ τα όπως είναι στο project σου) ---
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

router = APIRouter()  # prefix μπαίνει στο main.py: app.include_router(router, prefix="/me")


# ========== PRODUCTS ==========
@router.get("/products", response_model=list[ProductOut], tags=["products"])
def get_my_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Product).filter(Product.owner_id == current_user.id).all()


@router.post("/products/sync", tags=["products"])
def sync_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ΜΗΝ ξεκινάς sync αν λείπουν creds — καθαρό 400, όχι 500.
    if not (current_user.woocommerce_url and current_user.consumer_key and current_user.consumer_secret):
        raise HTTPException(status_code=400, detail="Missing WooCommerce credentials")
    try:
        fetch_and_store_products_from_woocommerce(db, current_user)
        return {"message": "Products synced successfully"}
    except Exception as e:
        # Μην ωραιοποιείς: πέτα καθαρό 500 με το μήνυμα
        raise HTTPException(status_code=500, detail=str(e))


# ========== CREDITS ==========
@router.get("/credits", tags=["credits"])
def get_credits(current_user: User = Depends(get_current_user)):
    return {"credits": current_user.credits}


@router.post("/use-credit", tags=["credits"])
def use_credit(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Κόψε αν δεν υπάρχουν credits
    if current_user.credits is None or current_user.credits < 1:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Not enough credits",
        )
    # Debit 1
    current_user.credits -= 1
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {
        "message": "Credit used",
        "remaining_credits": current_user.credits,
    }


# ========== SUBSCRIPTION / STRIPE ==========
@router.post("/subscribe", tags=["subscription"])
def subscribe(
    req: CreateCheckoutSessionRequest,  # πρέπει να έχει plan_id
    current_user: User = Depends(get_current_user),
):
    try:
        checkout_url = create_checkout_session(current_user, req.plan_id)
        return {"checkout_url": checkout_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cancel-subscription", tags=["subscription"])
def cancel_subscription(current_user: User = Depends(get_current_user)):
    try:
        success = cancel_user_subscription(current_user)
        if not success:
            raise HTTPException(
                status_code=404, detail="No active subscription to cancel"
            )
        return {"message": "Subscription cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/buy-credits", tags=["credits"])
async def buy_credits(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    try:
        data = await request.json()
        credits = data.get("credits")
        if not credits or not isinstance(credits, int) or credits <= 0:
            raise HTTPException(status_code=400, detail="Invalid number of credits")
        checkout_url = create_credits_checkout_session(current_user, credits)
        return {"checkout_url": checkout_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== WOOCOMMERCE CREDENTIALS ==========
# ΣΗΜΑΝΤΙΚΟ: Δεν βάζουμε response_model εδώ, για να μην ρίχνει 500 όταν τα πεδία είναι None.
@router.get("/woocommerce-credentials", tags=["woocommerce"])
def get_woocommerce_credentials(
    current_user: User = Depends(get_current_user),
):
    url = (current_user.woocommerce_url or None)
    ck = (current_user.consumer_key or None)
    cs = (current_user.consumer_secret or None)
    has_credentials = bool(url and ck and cs)
    # Για λόγους ασφάλειας δεν επιστρέφουμε τα κλειδιά. Το UI χρειάζεται μόνο το status.
    return {
        "has_credentials": has_credentials,
        "woocommerce_url": url if has_credentials else None,
    }


@router.put("/woocommerce-credentials", tags=["woocommerce"])
def update_woocommerce_credentials(
    creds: WooCommerceCredentials,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.woocommerce_url = creds.woocommerce_url
    current_user.consumer_key = creds.consumer_key
    current_user.consumer_secret = creds.consumer_secret
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"message": "WooCommerce credentials updated"}


@router.delete("/woocommerce-credentials", tags=["woocommerce"])
def delete_woocommerce_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.woocommerce_url = None
    current_user.consumer_key = None
    current_user.consumer_secret = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"message": "WooCommerce credentials deleted"}
