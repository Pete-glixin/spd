"""
Glixin Stripe Telemetry Module (src/stripe_telemetry.py)
-------------------------------------------------------
Non-blocking async telemetry reporter for Glixin Governance Tokens (GGT).
Posts usage events directly to Stripe Billing Meters.
"""

import threading
import requests
import time
from typing import Optional


class StripeTelemetryClient:
    def __init__(self, stripe_restricted_key: str):
        self.api_url = "https://api.stripe.com/v1/billing/meter_events"
        self.stripe_restricted_key = stripe_restricted_key

    def send_ggt_usage_async(
        self, 
        stripe_customer_id: str, 
        license_key: str, 
        ggt_count: int,
        device_label: Optional[str] = "local-sdk-node"
    ) -> None:
        """
        Fires an asynchronous telemetry ping to Stripe.
        Runs in a daemon thread so it won't block the prompt pipeline or program exit.
        """
        if ggt_count <= 0:
            return

        def _ping():
            headers = {
                "Authorization": f"Bearer {self.stripe_restricted_key}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            payload = {
                "event_name": "ggt_usage",
                "payload[value]": str(ggt_count),
                "payload[stripe_customer_id]": stripe_customer_id,
                "payload[license_key]": license_key,
                "payload[device_label]": device_label,
                "timestamp": int(time.time())
            }
            try:
                # 2-second timeout guarantees we abandon stalled requests gracefully
                requests.post(self.api_url, headers=headers, data=payload, timeout=2.0)
            except Exception:
                # Fail silently to prioritize application stability and pipeline execution
                pass

        threading.Thread(target=_ping, daemon=True).start()