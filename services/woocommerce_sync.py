import requests
from sqlalchemy.orm import Session
from models import Product, User

def clean_consumer_secret(secret: str) -> str:
    # Αφαιρεί τη λέξη 'secret' και κενά από το consumer_secret
    return secret.replace('secret', '').strip()

def fetch_and_store_products_from_woocommerce(db: Session, user: User):
    base_url = user.woocommerce_url
    consumer_key = user.consumer_key.strip()
    consumer_secret = user.consumer_secret.strip()

    # Καθαρίζουμε το consumer_secret
    consumer_secret = clean_consumer_secret(consumer_secret)

    api_url = f"{base_url}/wp-json/wc/v3/products"
    params = {
        "per_page": 100,
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
    except requests.HTTPError as e:
        # Αν θες, μπορείς να κάνεις πιο λεπτομερή logging ή raise για να το δεις από έξω
        print(f"Error fetching products from WooCommerce: {e}")
        raise

    products_data = response.json()

    # Διαγραφή προηγούμενων προϊόντων του χρήστη
    db.query(Product).filter(Product.owner_id == user.id).delete()
    db.commit()

    # Αποθήκευση νέων προϊόντων
    for p in products_data:
        # Πάρε βασικά πεδία, προσαρμόζεις ανάλογα με API response
        product = Product(
            id=p.get('id'),
            name=p.get('name'),
            description=p.get('description'),
            image_url=(p.get('images')[0]['src'] if p.get('images') else ''),
            available=p.get('status') == 'publish',
            categories=', '.join([cat['name'] for cat in p.get('categories', [])]),
            owner_id=user.id,
            price=p.get('price', '0')
        )
        db.merge(product)  # merge για update ή insert
    db.commit()
