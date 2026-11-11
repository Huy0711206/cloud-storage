"""Session-bound protection for browser clients whose Origin is opaque (null)."""
import hmac
import secrets
from urllib.parse import urlsplit
from fastapi import Request

def ensure_token(request: Request) -> str:
    token=request.session.get('_csrf')
    if not isinstance(token,str) or len(token)<32:
        token=secrets.token_urlsafe(32)
        request.session['_csrf']=token
    return token

def token_matches(request: Request, supplied: str) -> bool:
    expected=request.session.get('_csrf')
    return isinstance(expected,str) and isinstance(supplied,str) and len(supplied)<=128 and hmac.compare_digest(expected,supplied)

def origin_allowed(request: Request, base_url: str) -> bool:
    origin=request.headers.get('origin')
    site=request.headers.get('sec-fetch-site')
    if origin=='null':
        return site=='same-origin' and bool(getattr(request.state,'csrf_validated',False))
    if origin:
        actual,expected=urlsplit(origin),urlsplit(base_url)
        return (actual.scheme,actual.netloc)==(expected.scheme,expected.netloc)
    return site!='cross-site'
