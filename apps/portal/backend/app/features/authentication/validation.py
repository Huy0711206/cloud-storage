import re

def _password_error(password: str) -> str | None:
    if len(password) < 10:
        return "Mật khẩu phải có ít nhất 10 ký tự."
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        return "Mật khẩu phải gồm cả chữ và số."
    return None

