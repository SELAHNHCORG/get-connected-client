"""Declarative plumbing shared by all resource namespaces."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar

from ..exceptions import NotFoundError
from ..models.base import GalaxyModel

if TYPE_CHECKING:
    from ..client import GalaxyClient


class Resource:
    path: ClassVar[str]
    model: ClassVar[type[GalaxyModel]]

    def __init__(self, client: GalaxyClient):
        self._client = client

    def _url(self, *parts: Any) -> str:
        return "/".join([self.path, *[str(p) for p in parts]])

    def _parse(self, payload: Any, model: type[GalaxyModel] | None = None) -> Any:
        model = model or self.model
        if isinstance(payload, dict):
            return model.model_validate(payload)
        return payload

    def _get_one(self, url: str, model: type[GalaxyModel] | None = None) -> Any:
        return self._parse(self._client.get_data(url), model)

    def _get_list(self, url: str, model: type[GalaxyModel] | None = None) -> list[Any]:
        model = model or self.model
        try:
            rows = self._client.get_data(url) or []
        except NotFoundError:
            return []
        if not isinstance(rows, list):
            rows = [rows]
        return [model.model_validate(r) if isinstance(r, dict) else r for r in rows]


class ListMixin(Resource):
    def list(
        self,
        *,
        per_page: int = 150,
        since_id: int | None = None,
        since_created: str | None = None,
        since_updated: str | None = None,
        show_inactive: bool | None = None,
        **filters: Any,
    ) -> Iterator[GalaxyModel]:
        params: dict[str, Any] = {
            "since_id": since_id,
            "since_created": since_created,
            "since_updated": since_updated,
            **filters,
        }
        if show_inactive is not None:
            params["show_inactive"] = "Yes" if show_inactive else "No"
        for row in self._client.paginate(self.path, params, per_page=per_page):
            yield self.model.model_validate(row)


class GetMixin(Resource):
    def get(self, id: int) -> GalaxyModel:
        return self._get_one(self._url(id))


class CreateMixin(Resource):
    def create(self, **fields: Any) -> Any:
        payload = self._client.request("POST", self.path, json=fields)
        data = payload.get("data") if isinstance(payload, dict) else None
        return self._parse(data) if isinstance(data, dict) else payload


class UpdateMixin(Resource):
    def update(self, id: int, **fields: Any) -> Any:
        payload = self._client.request("PUT", self._url(id), json=fields)
        data = payload.get("data") if isinstance(payload, dict) else None
        return self._parse(data) if isinstance(data, dict) else payload


class DeleteMixin(Resource):
    def delete(self, id: int) -> None:
        self._client.request("DELETE", self._url(id))
