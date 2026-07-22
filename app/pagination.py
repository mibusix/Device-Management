from typing import Any, TypeVar

T = TypeVar("T")


def paginate(items: list[T], page: int, page_size: int) -> dict[str, Any]:
    """对内存列表做分页，返回与前端分页组件兼容的结构。"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    total = len(items)
    pages = (total + page_size - 1) // page_size if total else 1
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "items": items[start:end],
    }
