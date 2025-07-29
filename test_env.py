import os
import stripe

def main():
    # Παίρνει το secret key από το περιβάλλον (environment variable)
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    if not stripe.api_key:
        print("[ERROR] STRIPE_SECRET_KEY environment variable is not set.")
        return

    print("[TEST] Using Stripe Secret Key from environment variable.")

    try:
        balance = stripe.Balance.retrieve()
        print("[TEST] Stripe balance retrieved successfully!")
        print(balance)
    except Exception as e:
        print(f"[TEST ERROR] Stripe API call failed: {e}")

if __name__ == "__main__":
    main()
