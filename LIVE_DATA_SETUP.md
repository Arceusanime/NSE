# Angel One live data setup

1. Create a SmartAPI app in the Angel One developer portal and obtain the API key.
2. Enable the API account and note the client code, trading password/MPIN, and TOTP secret.
3. Copy `.env.example` to `.env` and fill the `NSE_ANGEL_*` values. Keep `.env` private.
4. Leave `NSE_ANGEL_MAC_ADDRESS`, `NSE_ANGEL_LOCAL_IP`, and `NSE_ANGEL_PUBLIC_IP` as `auto` initially. The app detects them at login. If Angel One has whitelisted a static public IP for your API key, replace only `NSE_ANGEL_PUBLIC_IP` with that registered value.
5. Start the API:

   ```bash
   uvicorn app.main:app --app-dir backend --reload
   ```

6. Trigger a bounded live scan:

   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/scans \
     -H "Content-Type: application/json" \
     -d "{\"levels\":3}"
   ```

The provider downloads Angel One's daily instrument master, resolves the nearest
future expiry, reads the previous NSE cash-session 09:15 candle, selects matching
CE/PE contracts, and requests FULL market quotes in batches of at most 50 tokens.

The first live rollout is intentionally bounded by `NSE_FNO_SYMBOLS`. Expand that
list after validating rate limits and account permissions. OI change is left at
zero when using the live quote endpoint because FULL quotes provide current OI;
historical OI delta needs a separate timestamped `getOIData` policy.
