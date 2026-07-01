from app.core.exceptions import BadRequestError


def test_bad_request_error_has_http_metadata() -> None:
    error = BadRequestError("invalid input")

    assert error.status_code == 400
    assert error.error_code == "bad_request"
