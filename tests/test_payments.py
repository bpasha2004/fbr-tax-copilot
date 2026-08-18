import pytest
from src.shared.payments import PaymentRouter


def test_individual_payment_methods_are_wallets():
    router = PaymentRouter()
    router_config = __import__("src.shared.payments", fromlist=["PAYMENT_CONFIG"]).PAYMENT_CONFIG
    old_j = router_config["jazzcash"]["msisdn"]
    old_e = router_config["easypaisa"]["msisdn"]
    try:
        router_config["jazzcash"]["msisdn"] = "03001234567"
        router_config["easypaisa"]["msisdn"] = "03007654321"
        methods = [r.method for r in router.route(1000, "individual", "REF-1")]
        assert methods == ["jazzcash", "easypaisa"]
    finally:
        router_config["jazzcash"]["msisdn"] = old_j
        router_config["easypaisa"]["msisdn"] = old_e


def test_preferred_method_must_match_client_type():
    router = PaymentRouter()
    with pytest.raises(ValueError, match="not valid for client_type"):
        router.route(1000, "individual", "REF-1", preferred_method="bank")


def test_invalid_amount_and_reference_are_rejected():
    router = PaymentRouter()
    with pytest.raises(ValueError, match="greater than zero"):
        router.route(0, "individual", "REF-1")
    with pytest.raises(ValueError, match="must not be empty"):
        router.route(1000, "individual", "   ")
