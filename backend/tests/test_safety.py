"""User isolation guard."""
import pytest

from utils.safety import enforce_user_isolation


def test_same_user_is_allowed():
    enforce_user_isolation("user-a", "user-a")
    enforce_user_isolation("user-a", None)


def test_cross_user_access_is_rejected():
    with pytest.raises(ValueError, match="isolation"):
        enforce_user_isolation("user-a", "user-b")
