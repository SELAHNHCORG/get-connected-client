"""Declarative plumbing shared by all resource namespaces."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from ..client import MAX_PER_PAGE
from ..exceptions import NotFoundError
from ..models.base import GalaxyModel

if TYPE_CHECKING:
    from ..client import GalaxyClient

M = TypeVar("M", bound=GalaxyModel)


class Resource(Generic[M]):
    """Base for a resource namespace: one API endpoint and its model.

    Subclasses declare two attributes and inherit whichever CRUD mixins the
    endpoint supports:

    * ``path`` -- the endpoint's path relative to the API root, e.g.
      ``"/users"``. It is the base for every URL the namespace builds.
    * ``model`` -- the :class:`~galaxy_digital_cli.models.base.GalaxyModel`
      subclass rows of this endpoint validate into. It is also the type
      parameter, so the mixins' return types stay precise::

          class Users(ListMixin[User], GetMixin[User], Resource[User]):
              path = "/users"
              model = User

    ``Users(client).get(5)`` then types as ``User``, not ``GalaxyModel``.

    ``model`` is deliberately *not* a :data:`~typing.ClassVar`: a ``ClassVar``
    may not reference a type variable.
    """

    path: ClassVar[str]
    model: type[M]

    def __init__(self, client: GalaxyClient):
        """Bind this namespace to *client*, which performs all I/O."""
        self._client = client

    def _url(self, *parts: Any) -> str:
        """Join ``path`` and *parts* into an endpoint URL.

        ``self._url(5, "hours")`` on a ``path`` of ``"/users"`` yields
        ``"/users/5/hours"``. Each part is stringified, so ids may be passed
        as ``int``.
        """
        return "/".join([self.path, *[str(p) for p in parts]])

    def _parse(self, payload: Any, model: type[GalaxyModel] | None = None) -> Any:
        """Validate *payload* into *model*, defaulting to ``self.model``.

        Non-dict payloads (``None``, a bare message, a scalar) are returned
        untouched -- the API does not always answer with an object.
        """
        model = model or self.model
        if isinstance(payload, dict):
            return model.model_validate(payload)
        return payload

    def _get_one(self, url: str, model: type[GalaxyModel] | None = None) -> Any:
        """GET *url* and validate the unwrapped payload into a single model.

        Pass *model* to parse a sub-resource that is not ``self.model``.
        """
        return self._parse(self._client.get_data(url), model)

    def _get_list(self, url: str, model: type[GalaxyModel] | None = None) -> list[Any]:
        """GET *url* and validate the unwrapped payload into a list of models.

        A lone object is wrapped in a one-element list. A 404 yields ``[]``:
        the API answers 404 rather than an empty list when a sub-resource
        collection has no rows, which is absence, not an error.
        """
        try:
            rows = self._client.get_data(url) or []
        except NotFoundError:
            return []
        if not isinstance(rows, list):
            rows = [rows]
        return [self._parse(r, model) for r in rows]


class ListMixin(Resource[M]):
    """Adds :meth:`list` to a namespace whose endpoint is paginated."""

    def list(
        self,
        *,
        per_page: int = MAX_PER_PAGE,
        since_id: int | None = None,
        since_created: str | None = None,
        since_updated: str | None = None,
        show_inactive: bool | None = None,
        **filters: Any,
    ) -> Iterator[M]:
        """Iterate every row of the endpoint, paging transparently.

        Rows stream as they arrive; the iterator issues one request per page
        and stops when the server runs out of rows.

        :param per_page: rows per request, clamped by the client to the API
            maximum of ``MAX_PER_PAGE``. Tunes request count, not results.
        :param since_id: return only rows with an id greater than this. The
            client also uses it as the paging cursor.
        :param since_created: server-side filter on creation time, formatted
            ``"YYYY-MM-DD HH:MM"``.
        :param since_updated: server-side filter on last-modified time, same
            format as *since_created*.
        :param show_inactive: ``True`` sends ``"Yes"`` and ``False`` sends
            ``"No"``; ``None`` (the default) omits the parameter entirely and
            takes the server default, which excludes inactive records.
        :param filters: any further endpoint-specific query parameters,
            passed through verbatim. ``None`` values are dropped.
        :return: an iterator of ``model`` instances.
        """
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


class GetMixin(Resource[M]):
    """Adds :meth:`get` to a namespace whose endpoint serves single rows."""

    def get(self, id: int) -> M:
        """Fetch the row with this *id*.

        :raises NotFoundError: no such row.
        :return: the parsed ``model`` instance.
        """
        return self._get_one(self._url(id))


class CreateMixin(Resource[M]):
    """Adds :meth:`create` to a namespace whose endpoint accepts POSTs."""

    def create(self, **fields: Any) -> M | dict[str, Any] | None:
        """POST *fields* to the endpoint to create a row.

        :param fields: the new row's attributes, sent as the JSON body.
        :raises ReadOnlyError: the client is in read-only mode.
        :return: the parsed model when the API returns a ``data`` object;
            otherwise the raw response payload, since some endpoints return
            nothing or a bare message.
        """
        payload = self._client.request("POST", self.path, json=fields)
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            return self._parse(data)
        return payload


class UpdateMixin(Resource[M]):
    """Adds :meth:`update` to a namespace whose endpoint accepts PUTs."""

    def update(self, id: int, **fields: Any) -> M | dict[str, Any] | None:
        """PUT *fields* to the row with this *id*.

        Only the supplied fields are sent, so this is a partial update.

        :param id: the row to modify.
        :param fields: the attributes to change, sent as the JSON body.
        :raises ReadOnlyError: the client is in read-only mode.
        :return: the parsed model when the API returns a ``data`` object;
            otherwise the raw response payload, since some endpoints return
            nothing or a bare message.
        """
        payload = self._client.request("PUT", self._url(id), json=fields)
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            return self._parse(data)
        return payload


class DeleteMixin(Resource[M]):
    """Adds :meth:`delete` to a namespace whose endpoint accepts DELETEs."""

    def delete(self, id: int) -> None:
        """Delete the row with this *id*.

        :raises ReadOnlyError: the client is in read-only mode.
        :raises NotFoundError: no such row.
        """
        self._client.request("DELETE", self._url(id))
