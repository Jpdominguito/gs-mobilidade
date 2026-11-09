"""Adaptador de repositório lendo um arquivo JSON (dados sintéticos do piloto)."""
import json
from pathlib import Path
from typing import Optional

from src.domain.models import Page, Point, PointStatus


class JsonPointRepository:
    def __init__(self, path):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        points = [
            Point(
                id=item["id"],
                name=item["name"],
                line=item["line"],
                neighborhood=item["neighborhood"],
                status=PointStatus(item["status"]),
                status_updated_at=item["status_updated_at"],
                alternative_point_id=item.get("alternative_point_id"),
                note=item.get("note"),
            )
            for item in raw
        ]
        self._points = sorted(points, key=lambda p: p.id)
        self._by_id = {p.id: p for p in self._points}

    def get(self, point_id: str) -> Optional[Point]:
        return self._by_id.get(point_id)

    def all_points(self) -> "list[Point]":
        return list(self._points)

    def list_points(self, status: Optional[PointStatus], limit: int, offset: int) -> Page:
        filtered = [p for p in self._points if status is None or p.status == status]
        return Page(
            items=filtered[offset:offset + limit],
            total=len(filtered),
            limit=limit,
            offset=offset,
        )
