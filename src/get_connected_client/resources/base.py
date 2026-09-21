"""Declarative plumbing shared by all resource namespaces."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Protocol, TypeVar

from ..client import MAX_PER_PAGE
from ..exceptions import NotFoundError
from ..models.base import GalaxyModel

if TYPE_CHECKING:
    from ..client import GalaxyClient

M = TypeVar("M", bound=GalaxyModel)


@dataclass(frozen=True)
class Change:
    """One field a merged update will alter.

    ``old`` is the value the API holds now, or ``None`` when the field is
    absent from the current record; ``new`` is what is about to be sent.
    """

    field: str
    old: Any
    new: Any


@dataclass
class PatchPlan:
    """What :meth:`UpdateMixin.prepare_patch` worked out, before any write.

    ``current`` is the fetched row translated by
    :meth:`Resource.to_request`; ``body`` is ``current`` with the supplied
    fields laid over it -- the exact JSON a following PUT sends; ``changes``
    lists the supplied fields whose value differs from ``current``, in the
    order they were supplied.

    ``missing_required`` names the fields this endpoint's request schema
    marks required that ``body`` does not carry. It is advisory only:
    :meth:`UpdateMixin.patch` still sends the body and lets the API answer.

    The plan is deliberately mutable: a caller may adjust ``body`` before
    handing it to :meth:`UpdateMixin.update`.
    """

    current: dict[str, Any]
    body: dict[str, Any]
    changes: list[Change]
    #: Fields in :attr:`Resource.required_fields` that ``body`` lacks. A
    #: non-empty list means the API will almost certainly answer 422.
    missing_required: list[str] = field(default_factory=list)


def _same(a: Any, b: Any) -> bool:
    """True when *a* and *b* mean the same thing on the wire.

    The API sends numeric ids as strings, so a caller's ``42`` must not read
    as a change against a stored ``"42"``, nor ``[1, 2]`` against
    ``["1", "2"]``. Numerics compare numerically (``1.0`` equals ``"1"``);
    booleans are excluded so ``True`` never equals ``"True"``.
    """
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if a == b:
        return True
    scalar = (str, int, float)
    if (
        isinstance(a, scalar)
        and isinstance(b, scalar)
        and not isinstance(a, bool)
        and not isinstance(b, bool)
    ):
        try:
            return float(a) == float(b)
        except (TypeError, ValueError):
            return str(a) == str(b)
    return False


class _HasId(Protocol):
    """Structural type for a nested read object carrying an id.

    Every ``*MiniObject`` model satisfies it -- ``agencyMiniObject``,
    ``groupMiniObject``, ``shiftObject`` and the rest all declare
    ``id: int | None``.
    """

    id: int | None


class _HasName(Protocol):
    """Structural type for a nested read object carrying a name.

    Satisfied by :class:`~get_connected_client.models.common.Tag`, the only
    read shape a request schema wants as bare names.
    """

    name: str | None


def _id_str(obj: _HasId | None) -> str | None:
    """The id of a nested read object, as the wire wants it.

    The API's request schemas type every id as ``type: string,
    format: number``, so a translated body sends ``"42"``, never ``42``.

    :param obj: a nested read object, or ``None`` when ``GET`` omitted it.
    :return: the id as a string, or ``None`` when there is no object or the
        object carries no id -- in both cases the caller leaves the derived
        key out of the body entirely.
    """
    if obj is None or obj.id is None:
        return None
    return str(obj.id)


def _id_strs(items: Iterable[_HasId] | None) -> list[str]:
    """The ids of a nested read list, as the wire wants them.

    Items with no id are skipped; ``0`` is a valid id and is kept, so the
    filter is ``is not None``, not truthiness.

    :param items: the nested read list, or ``None``.
    :return: the ids as strings. An empty list in, or ``None`` in, both give
        an empty list out -- callers that must distinguish "no groups" from
        "key absent" guard on the attribute themselves.
    """
    if items is None:
        return []
    return [str(item.id) for item in items if item.id is not None]


def _names(items: Iterable[_HasName] | None) -> list[str]:
    """The non-empty names of a nested read list.

    Filtered by truthiness: an empty or missing name is not a tag.

    :param items: the nested read list, or ``None``.
    :return: the names.
    """
    if items is None:
        return []
    return [item.name for item in items if item.name]


def _wire(value: Any) -> Any:
    """Coerce one translated value to the type the request schemas use.

    Every scalar property of every ``*RequestSchema`` in ``doc/api.yml`` is
    ``type: string`` -- there is no integer-typed request property in the
    spec -- but a handful of read fields are typed ``int`` on the model
    (``Event.event_area_id``, ``Benchmark.benchmark_group_id``), so
    ``model_dump(mode="json")`` hands back a JSON int where the PUT wants a
    string. Booleans are excluded so ``True`` never becomes ``"True"``.

    :param value: one value from the filtered dump.
    :return: *value*, stringified if it is an int.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return value


class Resource(Generic[M]):
    """Base for a resource namespace: one API endpoint and its model.

    Subclasses declare two attributes and inherit whichever CRUD mixins the
    endpoint supports:

    * ``path`` -- the endpoint's path relative to the API root, e.g.
      ``"/users"``. It is the base for every URL the namespace builds.
    * ``model`` -- the :class:`~get_connected_client.models.base.GalaxyModel`
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

    #: Property names of this endpoint's PUT request schema (the
    #: ``*RequestSchema`` in ``doc/api.yml``). :meth:`to_request` keeps only
    #: these keys, so a fetched row can be sent back without the read-only
    #: fields -- ``id``, timestamps, nested objects -- the PUT would reject.
    #: ``tests/test_request_fields.py`` asserts each set matches the spec.
    request_fields: ClassVar[frozenset[str]] = frozenset()

    #: Property names this endpoint's PUT request schema marks ``required``.
    #: Informational only: ``prepare_patch`` reports which are missing from
    #: the body it built, but never refuses to send it -- the API is the
    #: authority, and ``doc/api.yml`` is known to be imperfect.
    #: ``tests/test_request_fields.py`` asserts each set matches the spec.
    required_fields: ClassVar[frozenset[str]] = frozenset()

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

    def url(self, *parts: Any) -> str:
        """Public path builder -- use for confirm prompts so they can't drift
        from the wire.

        With no *parts* this is the collection itself, ``self.path``.
        """
        return self._url(*parts)

    def to_request(self, obj: M) -> dict[str, Any]:
        """Turn a fetched *obj* into a body the endpoint's PUT accepts.

        Keeps every non-``None`` field named in :attr:`request_fields` and
        drops the rest; ints become strings, since every scalar property of
        every request schema is ``type: string``. Resources whose read
        object nests what the request schema wants flat -- an ``agency``
        object where the PUT takes ``agency_id`` -- override this, call it
        first, then reshape.

        This is the read half of :meth:`UpdateMixin.prepare_patch`; it never
        touches the network.

        :param obj: a parsed row, as returned by :meth:`GetMixin.get`.
        :return: the subset of *obj* the PUT request schema accepts.
        """
        data = obj.model_dump(mode="json", exclude_none=True, by_alias=True)
        return {k: _wire(v) for k, v in data.items() if k in self.request_fields}

    def _parse(self, payload: Any, model: type[GalaxyModel] | None = None) -> Any:
        """Validate *payload* into *model*, defaulting to ``self.model``.

        Non-dict payloads (``None``, a bare message, a scalar) are returned
        untouched -- the API does not always answer with an object.
        """
        model = model or self.model
        if isinstance(payload, dict):
            return model.model_validate(payload)
        return payload

    def _get_one(
        self,
        url: str,
        model: type[GalaxyModel] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """GET *url* and validate the unwrapped payload into a single model.

        Pass *model* to parse a sub-resource that is not ``self.model``, and
        *params* for any query string the endpoint takes.
        """
        return self._parse(self._client.get_data(url, params), model)

    def _get_list(
        self,
        url: str,
        model: type[GalaxyModel] | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[Any]:
        """GET *url* and validate the unwrapped payload into a list of models.

        A lone object is wrapped in a one-element list. A 404 yields ``[]``:
        the API answers 404 rather than an empty list when a sub-resource
        collection has no rows, which is absence, not an error.

        Pass *params* for any query string the endpoint takes.
        """
        try:
            rows = self._client.get_data(url, params) or []
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
    """Adds :meth:`update`, :meth:`prepare_patch` and :meth:`patch` (PUT
    operations) to a namespace whose endpoint accepts PUTs.

    ``update`` sends a caller-supplied body verbatim; ``prepare_patch`` and
    ``patch`` fetch the row first and merge, since the API's PUT is a full
    replacement.
    """

    def _put(self, id: int, body: dict[str, Any]) -> M | dict[str, Any] | None:
        """PUT *body* to the row with this *id* and parse the reply."""
        payload = self._client.request("PUT", self._url(id), json=body)
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            return self._parse(data)
        return payload

    def update(self, id: int, **fields: Any) -> M | dict[str, Any] | None:
        """PUT *fields* to the row with this *id*, verbatim.

        The API treats PUT as a **full replacement**: every field the request
        schema marks required must be present or the server answers 422,
        whatever the row already holds. To change a subset of fields use
        :meth:`patch`, which fetches the row and merges for you. Use this
        method when you already have a complete, valid body.

        :param id: the row to modify.
        :param fields: the request body, sent as-is.
        :raises ReadOnlyError: the client is in read-only mode.
        :return: the parsed model when the API returns a ``data`` object;
            otherwise the raw response payload, since some endpoints return
            nothing or a bare message.
        """
        return self._put(id, fields)

    def prepare_patch(self, id: int, **fields: Any) -> PatchPlan:
        """Fetch the row, translate it and lay *fields* over it -- no write.

        The current record is fetched, passed through
        :meth:`Resource.to_request`, and *fields* are merged on top; the
        supplied fields always win, including keys outside
        :attr:`Resource.request_fields` (the caller may know something the
        spec does not). The returned plan carries the body a PUT would send
        and the list of fields that actually differ, so a caller can show
        or log the diff before committing to :meth:`update`.

        :param id: the row to modify.
        :param fields: the attributes to change.
        :raises NotImplementedError: this resource declares no
            :attr:`Resource.request_fields` and does not override
            :meth:`Resource.to_request`, so there is no base to merge over.
        :raises NotFoundError: no such row.
        :return: the :class:`PatchPlan`.
        """
        if not self.request_fields and type(self).to_request is Resource.to_request:
            raise NotImplementedError(
                f"{type(self).__name__} declares no request_fields, so a merged "
                "update has no base to merge over; use update() with a full body"
            )
        current = self.to_request(self._get_one(self._url(id)))
        body = {**current, **fields}
        changes = [
            Change(field=name, old=current.get(name), new=value)
            for name, value in fields.items()
            if name not in current or not _same(current[name], value)
        ]
        return PatchPlan(
            current=current,
            body=body,
            changes=changes,
            missing_required=sorted(self.required_fields - body.keys()),
        )

    def patch(self, id: int, **fields: Any) -> M | dict[str, Any] | None:
        """Change only *fields* on the row with this *id*.

        Two requests: a GET to read the row and a PUT of the merged body
        (see :meth:`prepare_patch`). This is what you want for "set the
        notes on this user"; :meth:`update` is for sending a complete body.

        :param id: the row to modify.
        :param fields: the attributes to change.
        :raises ReadOnlyError: the client is in read-only mode.
        :raises NotFoundError: no such row.
        :raises NotImplementedError: the resource declares no
            request_fields (see :meth:`prepare_patch`).
        :return: the parsed model when the API returns a ``data`` object;
            otherwise the raw response payload.
        """
        return self._put(id, self.prepare_patch(id, **fields).body)


class DeleteMixin(Resource[M]):
    """Adds :meth:`delete` to a namespace whose endpoint accepts DELETEs."""

    def delete(self, id: int) -> None:
        """Delete the row with this *id*.

        :raises ReadOnlyError: the client is in read-only mode.
        :raises NotFoundError: no such row.
        """
        self._client.request("DELETE", self._url(id))
