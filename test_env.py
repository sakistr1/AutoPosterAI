import stripe

def main():
    # Σκληροκωδικοποιημένο το secret key από το dashboard σου (sandbox)
    stripe.api_key = "sk_test_51RnHTuBBE8GGmWkWghyuOEWsVRDU88ejivLLimygROfe8tPA6NPb8ZStMep5CTwZttTAqmdQ7mKa8FyI3ad47bgD00i1r2qqkJ"

    print("[TEST] Using hardcoded Stripe Secret Key")

    try:
        balance = stripe.Balance.retrieve()
        print("[TEST] Stripe balance retrieved successfully!")
        print(balance)
    except Exception as e:
        print(f"[TEST ERROR] Stripe API call failed: {e}")

if __name__ == "__main__":
    main()
