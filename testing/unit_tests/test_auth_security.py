import pytest
import bcrypt
from fastapi import HTTPException
from API.auth.security import (
    User,
    verify_password,
    create_access_token,
    get_current_admin,
    SECRET_KEY,
    ALGORITHM,
)
from jose import jwt


def test_verify_password():
    raw_pwd = "my_secret_password"
    hashed = bcrypt.hashpw(raw_pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_create_and_decode_access_token():
    token = create_access_token(username="admin", role="admin")
    assert isinstance(token, str)

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_get_current_admin():
    admin_user = User(username="admin", role="admin")
    result = await get_current_admin(current_user=admin_user)
    assert result.username == "admin"

    regular_user = User(username="user1", role="viewer")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(current_user=regular_user)
    assert exc_info.value.status_code == 403
