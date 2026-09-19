from fastapi import HTTPException, status


def validate_pagination(offset: int, limit: int) -> None:
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Giá trị phân trang không hợp lệ.",
        )
