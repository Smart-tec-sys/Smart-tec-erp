"""Real signed JWT validation with a fixed clock; no network or database."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from app.auth.supabase_jwt import verify_supabase_access_token, SupabaseTokenError

NOW = 1791339504
ISSUER = "https://auth.test.invalid/auth/v1"
class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.fromtimestamp(NOW, tz=timezone.utc).astimezone(tz)

class SupabaseJwtClockSkewTest(unittest.TestCase):
    def setUp(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.patches = [
            patch("app.auth.supabase_jwt.get_supabase_auth_config", return_value=(ISSUER,"https://auth.test.invalid/jwks")),
            patch("app.auth.supabase_jwt.PyJWKClient"),
            patch("jwt.api_jwt.datetime", FixedDatetime),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        from app.auth.supabase_jwt import PyJWKClient
        PyJWKClient.return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.key.public_key())

    def token(self, **changes):
        claims = dict(iss=ISSUER, aud="authenticated", sub="test-subject", iat=NOW, nbf=NOW, exp=NOW+3600, aal="aal2", amr=[{"method":"totp","timestamp":NOW}])
        claims.update(changes)
        return jwt.encode(claims,self.key,algorithm="ES256",headers={"kid":"test-key"})

    def reject(self, token, cause):
        with self.assertRaises(SupabaseTokenError) as caught:
            verify_supabase_access_token(token)
        self.assertIsInstance(caught.exception.__cause__,cause)

    def test_iat_and_nbf_one_second_future_accepted(self):
        self.assertEqual(verify_supabase_access_token(self.token(iat=NOW+1,nbf=NOW+1)).identity.subject,"test-subject")

    def test_iat_ten_seconds_future_rejected(self):
        self.reject(self.token(iat=NOW+10),jwt.ImmatureSignatureError)

    def test_nbf_ten_seconds_future_rejected(self):
        self.reject(self.token(nbf=NOW+10),jwt.ImmatureSignatureError)

    def test_expired_beyond_leeway_rejected(self):
        self.reject(self.token(iat=NOW-60,nbf=NOW-60,exp=NOW-10),jwt.ExpiredSignatureError)

    def test_normal_token_accepted(self):
        self.assertEqual(verify_supabase_access_token(self.token()).claims["aal"],"aal2")

    def test_wrong_issuer_rejected(self):
        self.reject(self.token(iss="https://wrong.test.invalid"),jwt.InvalidIssuerError)

    def test_wrong_audience_rejected(self):
        self.reject(self.token(aud="wrong"),jwt.InvalidAudienceError)

    def test_invalid_signature_rejected(self):
        other=ec.generate_private_key(ec.SECP256R1())
        token=jwt.encode(dict(iss=ISSUER,aud="authenticated",sub="test",iat=NOW,exp=NOW+60),other,algorithm="ES256")
        self.reject(token,jwt.InvalidSignatureError)

if __name__ == "__main__":
    unittest.main()
