# Merged Updates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `galaxy <resource> update` (and a new library `patch`) fetch the current record, translate it into a valid PUT body, overlay the supplied fields, and send the whole thing, so the API's full-replacement PUT stops rejecting partial updates with 422.

**Architecture:** `Resource` gains a `request_fields` allowlist and a `to_request(model)` translator; `UpdateMixin` gains `prepare_patch` (fetch + translate + overlay, returns a `PatchPlan` with the changed fields) and `patch` (prepare + PUT). Six resources override `to_request` to flatten nested objects into the ids/names their PUT schema wants. The nine CLI `update` commands route through one `run_update` helper that shows only the changed fields in the confirmation prompt, exits early on no changes, and keeps the old raw PUT behind `--replace`.

**Tech Stack:** Python 3.10+, pydantic v2, httpx, typer, rich; tests with pytest + respx; `just test` runs the suite, `just check` runs lint + types.

**Spec:** `.agents/superpowers/specs/2026-09-20-merged-updates-design.md`

---

## File structure

| File | Responsibility |
|---|---|
| `src/get_connected_client/resources/base.py` | `request_fields`, `to_request`, `Change`, `PatchPlan`, `_same`, `UpdateMixin.prepare_patch` / `patch`; corrected `update` docstring |
| `src/get_connected_client/resources/{users,qualifications,benchmarks,groups}.py` | `request_fields` only (base translation suffices; groups documents the `ug_type` gap) |
| `src/get_connected_client/resources/{needs,events,hours,responses,agencies}.py` | `request_fields` + `to_request` override |
| `src/get_connected_client/__init__.py` | export `Change`, `PatchPlan` |
| `src/get_connected_client/cli/_confirm.py` | `confirm_patch` (changed-fields prompt) |
| `src/get_connected_client/cli/_update.py` (new) | `run_update` + the shared `--replace` option |
| `src/get_connected_client/cli/{users,agencies,needs,events,hours,responses,groups,qualifications,benchmarks}.py` | `update` commands call `run_update` |
| `tests/test_resources_base.py` | base mechanism tests on the `Widgets` fixture |
| `tests/test_request_fields.py` (new) | spec-conformance test for every `request_fields` |
| `tests/test_{needs,events_hours,responses_teams_groups,agencies}.py` | translation tests + updated CLI tests |
| `tests/test_users.py`, `tests/test_quals_benchmarks_misc.py` | updated CLI tests; users gets the full prompt/no-change/replace/decline set |
| `doc/source/cli.rst`, `doc/source/quickstart.rst` | "Updates are merged" section, `patch` example |

Conventions to follow throughout: every resource module already starts with `from __future__ import annotations`; ids in translated bodies are sent as **strings** (`str(obj.x.id)`) to match the spec's `type: string, format: number`; all new public names get docstrings in the existing style (Sphinx `:param:`/`:raises:`/`:return:`); commit after each task with `just test` green.

---

### Task 1: Base mechanism — `request_fields`, `to_request`, `PatchPlan`, `prepare_patch`, `patch`

**Goal:** The generic read-translate-overlay machinery on `Resource` and `UpdateMixin`, exported from the package, with the `update` docstring corrected.

**Files:**
- Modify: `src/get_connected_client/resources/base.py`
- Modify: `src/get_connected_client/__init__.py`
- Test: `tests/test_resources_base.py`

**Acceptance Criteria:**
- [ ] `Resource.request_fields` defaults to an empty frozenset; `to_request` keeps only non-None keys in it
- [ ] `prepare_patch` GETs the row, returns `PatchPlan(current, body, changes)`; a supplied value equal to current (including `42` vs `"42"`) is not a change; a key absent from current is a change with `old=None`
- [ ] `patch` PUTs `plan.body`
- [ ] `update` docstring says PUT is a full replacement and points at `patch`
- [ ] `Change`, `PatchPlan` importable from `get_connected_client`

**Verify:** `just test tests/test_resources_base.py` → all pass

**Steps:**

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_resources_base.py` (the `Widgets` class and imports already exist at the top of the file; add `Change`, `PatchPlan` to the `from get_connected_client.resources.base import (...)` block and add `import json`):

```python
class RequestWidgets(Widgets):
    """Widgets with a request allowlist: `name` is writable, `id` is not."""

    path = "/rwidgets"
    request_fields = frozenset({"name"})


def test_to_request_default_keeps_nothing(client):
    """With no request_fields declared, nothing is writable."""
    assert Widgets(client).to_request(Tag(id=1, name="a")) == {}


def test_to_request_filters_to_request_fields(client):
    assert RequestWidgets(client).to_request(Tag(id=1, name="a")) == {"name": "a"}


def test_to_request_drops_none(client):
    assert RequestWidgets(client).to_request(Tag(id=1, name=None)) == {}


def test_prepare_patch_merges_and_reports_changes(client, api):
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "old"}})
    plan = RequestWidgets(client).prepare_patch(5, name="new", colour="red")
    assert plan.current == {"name": "old"}
    assert plan.body == {"name": "new", "colour": "red"}
    assert plan.changes == [
        Change(field="name", old="old", new="new"),
        Change(field="colour", old=None, new="red"),
    ]


def test_prepare_patch_unchanged_value_is_not_a_change(client, api):
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "same"}})
    plan = RequestWidgets(client).prepare_patch(5, name="same")
    assert plan.changes == []
    assert plan.body == {"name": "same"}


def test_prepare_patch_int_and_numeric_string_are_same(client, api):
    """Ids come back as strings; a caller's int must not read as a change."""
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "42"}})
    plan = RequestWidgets(client).prepare_patch(5, name=42)
    assert plan.changes == []


def test_prepare_patch_makes_no_write(client, api):
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "old"}})
    RequestWidgets(client).prepare_patch(5, name="new")
    assert all(c.request.method == "GET" for c in api.calls)


def test_patch_puts_merged_body(client, api):
    api.get("/rwidgets/5").respond(json={"data": {"id": 5, "name": "old"}})
    route = api.put("/rwidgets/5").respond(json={"data": {"id": 5, "name": "new"}})
    made = RequestWidgets(client).patch(5, name="new")
    assert made.name == "new"
    assert json.loads(route.calls.last.request.content) == {"name": "new"}


def test_patch_plan_exported():
    import get_connected_client

    assert get_connected_client.PatchPlan is PatchPlan
    assert get_connected_client.Change is Change
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `just test tests/test_resources_base.py`
Expected: ImportError on `Change` / `PatchPlan`.

- [ ] **Step 3: Implement in `resources/base.py`**

Add to the imports:

```python
from dataclasses import dataclass
```

Add after `M = TypeVar(...)`:

```python
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
    """

    current: dict[str, Any]
    body: dict[str, Any]
    changes: list[Change]


def _same(a: Any, b: Any) -> bool:
    """True when *a* and *b* mean the same thing on the wire.

    The API sends numeric ids as strings, so a caller's ``42`` must not read
    as a change against a stored ``"42"``. Booleans are excluded from the
    string comparison so ``True`` never equals ``"True"``.
    """
    if a == b:
        return True
    scalar = (str, int, float)
    if (
        isinstance(a, scalar)
        and isinstance(b, scalar)
        and not isinstance(a, bool)
        and not isinstance(b, bool)
    ):
        return str(a) == str(b)
    return False
```

In `class Resource`, after `model: type[M]`:

```python
    #: Property names of this endpoint's PUT/POST request schema (the
    #: ``*RequestSchema`` in ``doc/api.yml``). :meth:`to_request` keeps only
    #: these keys, so a fetched row can be sent back without the read-only
    #: fields -- ``id``, timestamps, nested objects -- the PUT would reject.
    #: ``tests/test_request_fields.py`` asserts each set matches the spec.
    request_fields: ClassVar[frozenset[str]] = frozenset()
```

In `class Resource`, after `url()`:

```python
    def to_request(self, obj: M) -> dict[str, Any]:
        """Turn a fetched *obj* into a body the endpoint's PUT accepts.

        Keeps every non-``None`` field named in :attr:`request_fields` and
        drops the rest. Resources whose read object nests what the request
        schema wants flat -- an ``agency`` object where the PUT takes
        ``agency_id`` -- override this, call it first, then reshape.

        This is the read half of :meth:`UpdateMixin.prepare_patch`; it never
        touches the network.
        """
        data = obj.model_dump(mode="json", exclude_none=True)
        return {k: v for k, v in data.items() if k in self.request_fields}
```

Replace `UpdateMixin` entirely:

```python
class UpdateMixin(Resource[M]):
    """Adds :meth:`update`, :meth:`prepare_patch` and :meth:`patch` to a
    namespace whose endpoint accepts PUTs."""

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
        payload = self._client.request("PUT", self._url(id), json=fields)
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            return self._parse(data)
        return payload

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
        :raises NotFoundError: no such row.
        :return: the :class:`PatchPlan`.
        """
        current = self.to_request(self._get_one(self._url(id)))
        body = {**current, **fields}
        changes = [
            Change(field=name, old=current.get(name), new=value)
            for name, value in fields.items()
            if name not in current or not _same(current[name], value)
        ]
        return PatchPlan(current=current, body=body, changes=changes)

    def patch(self, id: int, **fields: Any) -> M | dict[str, Any] | None:
        """Change only *fields* on the row with this *id*.

        Two requests: a GET to read the row and a PUT of the merged body
        (see :meth:`prepare_patch`). This is what you want for "set the
        notes on this user"; :meth:`update` is for sending a complete body.

        :param id: the row to modify.
        :param fields: the attributes to change.
        :raises ReadOnlyError: the client is in read-only mode.
        :raises NotFoundError: no such row.
        :return: whatever :meth:`update` returns.
        """
        return self.update(id, **self.prepare_patch(id, **fields).body)
```

In `src/get_connected_client/__init__.py`, add after the exceptions import:

```python
from .resources.base import Change, PatchPlan
```

and add `"Change"` and `"PatchPlan"` to `__all__` (keep the list alphabetical: `"Change"` after `"AuthError"`, `"PatchPlan"` after `"NotFoundError"`).

Note on the circular import: `resources.base` imports `..client` at module level for `MAX_PER_PAGE`, and `client.py` imports the resources lazily inside `__init__`. Importing `resources.base` from the package `__init__` **after** `from .client import GalaxyClient` is therefore safe. If `just test` shows an ImportError cycle, move the new import line to the very end of `__init__.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `just test tests/test_resources_base.py`
Expected: all pass. Then `just check` → clean (mypy may want `obj: M` in `to_request`; it is declared that way).

- [ ] **Step 5: Commit**

```bash
git add src/get_connected_client/resources/base.py src/get_connected_client/__init__.py tests/test_resources_base.py
git commit -m "feat: to_request / prepare_patch / patch on resources; PUT is a full replacement"
```

---

### Task 2: `request_fields` on all nine updatable resources + spec conformance test

**Goal:** Every resource with an `UpdateMixin` declares its PUT schema's property names, and a test proves each set matches `doc/api.yml` so drift fails CI.

**Files:**
- Modify: `src/get_connected_client/resources/users.py`, `needs.py`, `events.py`, `groups.py`, `hours.py`, `responses.py`, `agencies.py`, `qualifications.py`, `benchmarks.py`
- Create: `tests/test_request_fields.py`

**Acceptance Criteria:**
- [ ] Each of the nine classes has a `request_fields` frozenset equal to the property names of its `*RequestSchema`
- [ ] `tests/test_request_fields.py` is parametrized over the nine (class, schema) pairs and passes
- [ ] The test also asserts every `UpdateMixin` subclass in the package is in the pair list (so a tenth updatable resource cannot appear without one)

**Verify:** `just test tests/test_request_fields.py` → 10 passed

**Steps:**

- [ ] **Step 1: Write the failing test**

Create `tests/test_request_fields.py`:

```python
"""Every updatable resource's ``request_fields`` matches its PUT schema.

``doc/api.yml`` is the vendored source of truth. If Galaxy Digital adds a
field to a request schema, this test fails until the allowlist catches up,
which is the point: a stale allowlist would silently drop that field from
every merged update.
"""

import inspect
from pathlib import Path

import pytest
import yaml

from get_connected_client import resources
from get_connected_client.resources import (
    agencies,
    benchmarks,
    events,
    groups,
    hours,
    needs,
    qualifications,
    responses,
    users,
)
from get_connected_client.resources.base import UpdateMixin

SPEC = Path(__file__).resolve().parents[1] / "doc" / "api.yml"

PAIRS = [
    (users.Users, "userRequestSchema"),
    (needs.Needs, "needRequestSchema"),
    (events.Events, "eventRequestSchema"),
    (groups.Groups, "groupRequestSchema"),
    (hours.Hours, "hourRequestSchema"),
    (responses.Responses, "responseRequestSchema"),
    (agencies.Agencies, "agencyRequestSchema"),
    (qualifications.Qualifications, "qualificationRequestSchema"),
    (benchmarks.Benchmarks, "benchmarkRequestSchema"),
]


@pytest.fixture(scope="module")
def schemas():
    with SPEC.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["components"]["schemas"]


@pytest.mark.parametrize(("cls", "schema"), PAIRS, ids=[c.__name__ for c, _ in PAIRS])
def test_request_fields_match_spec(schemas, cls, schema):
    expected = frozenset(schemas[schema]["properties"])
    assert cls.request_fields == expected, (
        f"{cls.__name__}.request_fields drifted from {schema}: "
        f"missing={sorted(expected - cls.request_fields)} "
        f"extra={sorted(cls.request_fields - expected)}"
    )


def test_every_updatable_resource_is_covered():
    """A new UpdateMixin subclass must be added to PAIRS (and get an allowlist)."""
    covered = {cls for cls, _ in PAIRS}
    found = set()
    for module_name in (
        "agencies",
        "benchmarks",
        "events",
        "groups",
        "hours",
        "misc",
        "needs",
        "qualifications",
        "responses",
        "teams",
        "users",
    ):
        module = getattr(
            __import__(f"{resources.__name__}.{module_name}", fromlist=["x"]),
            "__dict__",
        )
        for _, obj in module.items():
            if (
                inspect.isclass(obj)
                and issubclass(obj, UpdateMixin)
                and obj is not UpdateMixin
                and obj.__module__.startswith(resources.__name__)
            ):
                found.add(obj)
    assert found == covered, f"uncovered: {found - covered}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `just test tests/test_request_fields.py`
Expected: 9 failures ("drifted ... missing=[...]"), the coverage test passes.

- [ ] **Step 3: Add `request_fields` to each resource**

Each goes directly under `model = ...` in the class body. The literal sets below were generated from `doc/api.yml`; the test in Step 1 is the check.

`users.py` (class `Users`):

```python
request_fields = frozenset(
    {
        "user_address",
        "user_address2",
        "user_age_range",
        "user_birthday",
        "user_city",
        "user_comments",
        "user_company",
        "user_company_title",
        "user_country",
        "user_county",
        "user_department",
        "user_disaster",
        "user_email",
        "user_ethnicity",
        "user_fname",
        "user_gender",
        "user_grad_semester",
        "user_grad_year",
        "user_lname",
        "user_mname",
        "user_notes",
        "user_phone",
        "user_phone_cell",
        "user_postal",
        "user_reference_id",
        "user_state",
        "user_status",
        "user_username",
    }
)
```

`needs.py` (class `Needs`):

```python
request_fields = frozenset(
    {
        "accessible",
        "agency_id",
        "attributes",
        "event_id",
        "family_friendly",
        "groups",
        "initiative_id",
        "interests",
        "need_address",
        "need_address2",
        "need_allow_groups",
        "need_body",
        "need_city",
        "need_comments",
        "need_contact",
        "need_date",
        "need_date_close",
        "need_date_type",
        "need_hours",
        "need_hours_description",
        "need_impact_area",
        "need_latitude",
        "need_longitude",
        "need_postal",
        "need_public",
        "need_response_notify",
        "need_state",
        "need_status",
        "need_title",
        "need_type",
        "need_volunteers_needed",
        "outdoors",
        "shifts",
        "tags",
        "virtual_need",
    }
)
```

`events.py` (class `Events`):

```python
request_fields = frozenset(
    {
        "event_address",
        "event_address2",
        "event_all_day",
        "event_area",
        "event_area_id",
        "event_capacity",
        "event_city",
        "event_comments",
        "event_contact",
        "event_country",
        "event_date_end",
        "event_date_start",
        "event_description",
        "event_email",
        "event_location",
        "event_phone",
        "event_postal",
        "event_rsvp",
        "event_state",
        "event_tags",
        "event_title",
    }
)
```

`groups.py` (class `Groups`):

```python
request_fields = frozenset(
    {
        "ug_allow_member_remove",
        "ug_approval",
        "ug_block_id",
        "ug_color",
        "ug_description",
        "ug_description_private",
        "ug_domains",
        "ug_goal",
        "ug_icon",
        "ug_limit",
        "ug_status",
        "ug_submitted_hours",
        "ug_suppress_resume",
        "ug_text_color",
        "ug_title",
        "ug_type",
    }
)
```

`hours.py` (class `Hours`):

```python
request_fields = frozenset(
    {
        "group_ids",
        "hour_contact_details",
        "hour_contact_name",
        "hour_hours",
        "hour_location",
        "hour_miles",
        "hour_relationship",
        "hour_start",
        "hour_status",
        "response_id",
        "user_id",
    }
)
```

`responses.py` (class `Responses`):

```python
request_fields = frozenset(
    {
        "need_id",
        "questions",
        "response_date_added",
        "response_note",
        "schedule_ids",
        "team_id",
        "user_id",
    }
)
```

`agencies.py` (class `Agencies`):

```python
request_fields = frozenset(
    {
        "agency_address",
        "agency_address2",
        "agency_city",
        "agency_comments",
        "agency_contact",
        "agency_contact_title",
        "agency_contacts",
        "agency_ein",
        "agency_email",
        "agency_facebook_link",
        "agency_fax",
        "agency_instagram_link",
        "agency_link",
        "agency_linkedin_link",
        "agency_mission",
        "agency_name",
        "agency_news",
        "agency_partner",
        "agency_phone",
        "agency_phone_extension",
        "agency_postal",
        "agency_state",
        "agency_status",
        "agency_twitter_link",
        "agency_url",
        "agency_video",
        "agency_youtube_link",
    }
)
```

`qualifications.py` (class `Qualifications`):

```python
request_fields = frozenset(
    {
        "qualification_approval",
        "qualification_correct_answer",
        "qualification_duration",
        "qualification_hide_from_registration",
        "qualification_level",
        "qualification_link_show",
        "qualification_link_text",
        "qualification_link_url",
        "qualification_options",
        "qualification_question",
        "qualification_required",
        "qualification_status",
        "qualification_title",
        "qualification_type",
    }
)
```

`benchmarks.py` (class `Benchmarks`):

```python
request_fields = frozenset(
    {
        "benchmark_allow_indv_hours",
        "benchmark_approval_required",
        "benchmark_date_end",
        "benchmark_date_start",
        "benchmark_group_id",
        "benchmark_hours",
        "benchmark_icon",
        "benchmark_status",
        "benchmark_title",
    }
)
```

`ruff format` will reflow these; let it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `just test tests/test_request_fields.py` → 10 passed. Run `just fix` then `just test` → full suite green.

- [ ] **Step 5: Commit**

```bash
git add src/get_connected_client/resources/ tests/test_request_fields.py
git commit -m "feat: declare request_fields on every updatable resource, checked against the spec"
```

---

### Task 3: Needs translation

**Goal:** `Needs.to_request` flattens `agency`, `initiative`, `tags`, `groups` into the ids/names the PUT wants and leaves `shifts` out of the merge base.

**Files:**
- Modify: `src/get_connected_client/resources/needs.py`
- Test: `tests/test_needs.py`

**Acceptance Criteria:**
- [ ] `agency.id` → `agency_id` (string); `initiative.id` → `initiative_id` (string)
- [ ] `tags` → list of tag names; `groups` → list of group id strings
- [ ] `shifts` absent from the result even when the row has them
- [ ] Read-only keys (`id`, `domain_id`, `created_at`, `updated_at`, `background_check_required`, `outdoors_plan`) absent

**Verify:** `just test tests/test_needs.py -k to_request` → pass

**Steps:**

- [ ] **Step 1: Write the failing test**

Add to `tests/test_needs.py` (after the model tests; `Need` and `Needs` are already imported there, `client` fixture from conftest):

```python
def test_to_request_flattens_nested_objects(client):
    need = Need.model_validate(
        {
            "id": "42",
            "domain_id": "1",
            "need_title": "Park Cleanup",
            "need_status": "active",
            "agency": {"id": "3", "agency_name": "Helping Hands"},
            "initiative": {"id": "8", "init_title": "Spring"},
            "tags": [{"id": "1", "name": "Outdoors"}, {"id": "2", "name": None}],
            "groups": [{"id": "7", "group_title": "Rotary"}],
            "shifts": [{"id": "99", "start": "2024-03-01 08:00:00", "slots": 5}],
            "background_check_required": "No",
            "created_at": "2024-01-01 00:00:00",
        }
    )
    body = Needs(client).to_request(need)
    assert body == {
        "need_title": "Park Cleanup",
        "need_status": "active",
        "agency_id": "3",
        "initiative_id": "8",
        "tags": ["Outdoors"],
        "groups": ["7"],
    }


def test_to_request_without_nested_objects(client):
    body = Needs(client).to_request(Need.model_validate(NEED_ROW))
    assert body == {
        "need_title": "Park Cleanup",
        "need_status": "active",
        "need_date": "2024-03-01",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `just test tests/test_needs.py -k to_request`
Expected: FAIL — body contains `agency` dict / `shifts` list, lacks `agency_id`.

- [ ] **Step 3: Implement the override in `needs.py`**

Add to the class body of `Needs`, after `request_fields`:

```python
    def to_request(self, obj: Need) -> dict[str, Any]:
        """Flatten a fetched need into the shape ``PUT /needs/{id}`` wants.

        The read object nests what the request schema takes flat:
        ``agency``/``initiative`` objects become ``agency_id``/
        ``initiative_id``, ``tags`` objects become their names, ``groups``
        objects become their ids. All ids are sent as strings.

        ``shifts`` is deliberately **left out**: the read shape
        (``shiftObject``) does not match ``shiftRequestSchema``, and
        resending shifts on every update risks duplicating rows that
        :meth:`add_shift`/:meth:`remove_shift` already manage. Pass
        ``shifts=[...]`` explicitly to :meth:`patch` if you mean to.
        """
        body = super().to_request(obj)
        body.pop("shifts", None)
        if obj.agency is not None and obj.agency.id is not None:
            body["agency_id"] = str(obj.agency.id)
        if obj.initiative is not None and obj.initiative.id is not None:
            body["initiative_id"] = str(obj.initiative.id)
        if obj.tags is not None:
            body["tags"] = [t.name for t in obj.tags if t.name]
        if obj.groups is not None:
            body["groups"] = [str(g.id) for g in obj.groups if g.id is not None]
        return body
```

Also add a line to the `.. note::` block in the class docstring (the one about shifts): "For the same reason :meth:`to_request` never carries shifts into a merged update."

- [ ] **Step 4: Run tests to verify they pass**

Run: `just test tests/test_needs.py` → pass; `just check-types` → clean (mypy accepts `obj: Need` because `Needs` is `Resource[Need]`).

- [ ] **Step 5: Commit**

```bash
git add src/get_connected_client/resources/needs.py tests/test_needs.py
git commit -m "feat: Needs.to_request flattens agency/initiative/tags/groups, skips shifts"
```

---

### Task 4: Events and Groups translation

**Goal:** `Events.to_request` renames `tags` to `event_tags` names; `Groups` documents that `ug_type` cannot be derived.

**Files:**
- Modify: `src/get_connected_client/resources/events.py`, `src/get_connected_client/resources/groups.py`
- Test: `tests/test_events_hours.py`, `tests/test_responses_teams_groups.py`

**Acceptance Criteria:**
- [ ] Event `tags` objects → `event_tags` list of names; `tags` key absent
- [ ] Group `to_request` drops `users`, `needs`, `agencies`, `questions_*`, ids, timestamps and does **not** invent `ug_type`
- [ ] `Groups` docstring states the `ug_type` requirement

**Verify:** `just test tests/test_events_hours.py tests/test_responses_teams_groups.py -k to_request` → pass

**Steps:**

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_events_hours.py` (imports `Event`, `Events` already present):

```python
def test_event_to_request_renames_tags(client):
    event = Event.model_validate(
        {
            **EVENT_ROW,
            "tags": [{"id": "1", "name": "Fair"}, {"id": "2", "name": "Family"}],
            "update_at": "2024-01-01 00:00:00",
        }
    )
    assert Events(client).to_request(event) == {
        "event_title": "Volunteer Fair",
        "event_date_start": "2024-03-01 08:00:00",
        "event_location": "Community Center",
        "event_tags": ["Fair", "Family"],
    }
```

Add to `tests/test_responses_teams_groups.py` (imports `Group`, `Groups` already present):

```python
def test_group_to_request_drops_membership_and_keeps_ug_type_absent(client):
    group = Group.model_validate(
        {
            **GROUP_ROW,
            "users": [{"id": "1", "user_fname": "A"}],
            "needs": [{"id": "2", "need_title": "N"}],
            "agencies": [{"id": "3", "agency_name": "G"}],
            "questions_join": [],
            "created_at": "2024-01-01 00:00:00",
        }
    )
    body = Groups(client).to_request(group)
    assert body == {"ug_title": "Rotary Club", "ug_status": "active"}
    assert "ug_type" not in body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `just test tests/test_events_hours.py tests/test_responses_teams_groups.py -k to_request`
Expected: the events test fails (no `event_tags`); the groups test already passes (base behaviour) — that is fine, it pins the contract.

- [ ] **Step 3: Implement**

`events.py`, in `Events` after `request_fields`:

```python
    def to_request(self, obj: Event) -> dict[str, Any]:
        """Flatten a fetched event into the shape ``PUT /events/{id}`` wants.

        The read object's ``tags`` (objects) become the request schema's
        ``event_tags`` (names). Note the spec's warning on that field:
        submitted tags replace the event's existing tags, which is exactly
        why they must be carried over here.
        """
        body = super().to_request(obj)
        if obj.tags is not None:
            body["event_tags"] = [t.name for t in obj.tags if t.name]
        return body
```

Add `from typing import Any` to the imports of `events.py`.

`groups.py`: no override. Add this paragraph to the end of the `Groups` class docstring:

```
    .. note::
       ``ug_type`` (``gc`` or ``slm``) is required by every ``PUT /groups/{id}``
       but never returned by ``GET``, so :meth:`patch` cannot carry it over.
       A merged update must supply it explicitly -- ``patch(9, ug_type="gc",
       ...)`` -- or the API answers 422.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `just test tests/test_events_hours.py tests/test_responses_teams_groups.py` → pass.

- [ ] **Step 5: Commit**

```bash
git add src/get_connected_client/resources/events.py src/get_connected_client/resources/groups.py tests/test_events_hours.py tests/test_responses_teams_groups.py
git commit -m "feat: Events.to_request carries tags as event_tags; document the group ug_type gap"
```

---

### Task 5: Hours and Responses translation

**Goal:** `Hours.to_request` and `Responses.to_request` derive the id fields their PUT schemas require from nested objects.

**Files:**
- Modify: `src/get_connected_client/resources/hours.py`, `src/get_connected_client/resources/responses.py`
- Test: `tests/test_events_hours.py`, `tests/test_responses_teams_groups.py`

**Acceptance Criteria:**
- [ ] Hour: `user.id` → `user_id`; `groups[].id` → `group_ids`; `hour_date_start` → `hour_start`; `need`, `hour_date_end`, `hour_description`, `hour_parent`, `hour_source`, `hour_type` dropped
- [ ] Response: `need.id` → `need_id`; `user.id` → `user_id`; `shift.id` → `schedule_ids=[...]`; `team.id` → `team_id`; `response_status`, `answers`, `agency`, `initiative` dropped

**Verify:** `just test tests/test_events_hours.py tests/test_responses_teams_groups.py -k to_request` → pass

**Steps:**

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_events_hours.py` (`Hour`, `Hours` already imported):

```python
def test_hour_to_request_derives_ids_and_start(client):
    hour = Hour.model_validate(
        {
            **HOUR_ROW,
            "user": {"id": "5", "user_fname": "Ada"},
            "need": {"id": "42", "need_title": "Park Cleanup"},
            "groups": [{"id": "9", "group_title": "Rotary"}],
            "hour_date_end": "2024-03-01 11:00:00",
            "hour_description": "Raking",
            "hour_type": "need",
        }
    )
    assert Hours(client).to_request(hour) == {
        "hour_hours": "3",
        "hour_status": "approved",
        "hour_start": "2024-03-01 08:00:00",
        "user_id": "5",
        "group_ids": ["9"],
    }
```

Add to `tests/test_responses_teams_groups.py` (`Response`, `Responses` already imported):

```python
def test_response_to_request_derives_ids(client):
    response = Response.model_validate(
        {
            **RESPONSE_ROW,
            "need": {"id": "42", "need_title": "Park Cleanup"},
            "user": {"id": "5", "user_fname": "Ada"},
            "shift": {"id": "77", "start": "2024-03-01 08:00:00"},
            "team": {"id": "3", "team_name": "Crew"},
            "agency": {"id": "9", "agency_name": "HH"},
            "response_note": "Bring gloves",
            "answers": [{"key": "q1", "answer": "yes"}],
        }
    )
    assert Responses(client).to_request(response) == {
        "response_date_added": "2024-03-01 12:00:00",
        "response_note": "Bring gloves",
        "need_id": "42",
        "user_id": "5",
        "schedule_ids": ["77"],
        "team_id": "3",
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `just test tests/test_events_hours.py tests/test_responses_teams_groups.py -k to_request`
Expected: both new tests fail (missing `user_id` etc.).

- [ ] **Step 3: Implement**

`hours.py`, add `from typing import Any` to imports; in `Hours` after `request_fields`:

```python
    def to_request(self, obj: Hour) -> dict[str, Any]:
        """Flatten a fetched hour record into the shape ``PUT /hours/{id}`` wants.

        The request schema names the volunteer as ``user_id``, the groups as
        ``group_ids`` and the start as ``hour_start``; the read object nests
        the first two and calls the third ``hour_date_start``. ``need`` has
        no counterpart on the write side (the record is tied to its need
        through ``response_id``, which the read object does not return) and
        is dropped.
        """
        body = super().to_request(obj)
        if obj.hour_date_start is not None:
            body["hour_start"] = obj.hour_date_start
        if obj.user is not None and obj.user.id is not None:
            body["user_id"] = str(obj.user.id)
        if obj.groups is not None:
            body["group_ids"] = [str(g.id) for g in obj.groups if g.id is not None]
        return body
```

`responses.py`, add `from typing import Any` to imports; in `Responses` after `request_fields`:

```python
    def to_request(self, obj: Response) -> dict[str, Any]:
        """Flatten a fetched response into the shape ``PUT /responses/{id}`` wants.

        The three required write fields all live inside nested read objects:
        ``need.id`` → ``need_id``, ``user.id`` → ``user_id`` and
        ``shift.id`` → ``schedule_ids`` (a one-element list; a response is
        tied to one shift). ``team.id`` → ``team_id`` when present. The
        read-only ``response_status``, ``answers``, ``agency`` and
        ``initiative`` are dropped.
        """
        body = super().to_request(obj)
        if obj.need is not None and obj.need.id is not None:
            body["need_id"] = str(obj.need.id)
        if obj.user is not None and obj.user.id is not None:
            body["user_id"] = str(obj.user.id)
        if obj.shift is not None and obj.shift.id is not None:
            body["schedule_ids"] = [str(obj.shift.id)]
        if obj.team is not None and obj.team.id is not None:
            body["team_id"] = str(obj.team.id)
        return body
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `just test tests/test_events_hours.py tests/test_responses_teams_groups.py` → pass.

- [ ] **Step 5: Commit**

```bash
git add src/get_connected_client/resources/hours.py src/get_connected_client/resources/responses.py tests/test_events_hours.py tests/test_responses_teams_groups.py
git commit -m "feat: Hours/Responses.to_request derive user, need, shift, team and group ids"
```

---

### Task 6: Agencies translation

**Goal:** `Agencies.to_request` leaves `agency_contacts` out of the merge base (list on read, string on write, format undocumented).

**Files:**
- Modify: `src/get_connected_client/resources/agencies.py`
- Test: `tests/test_agencies.py`

**Acceptance Criteria:**
- [ ] `agency_contacts` absent from the result; `logo`, `agency_hours`, `agency_extra_location`, lat/long, ids, timestamps absent
- [ ] All plain `agency_*` fields carried over

**Verify:** `just test tests/test_agencies.py -k to_request` → pass

**Steps:**

- [ ] **Step 1: Write the failing test**

Add to `tests/test_agencies.py` (`Agency`, `Agencies` already imported):

```python
def test_to_request_drops_contacts_and_read_only(client):
    agency = Agency.model_validate(
        {
            **AGENCY_ROW,
            "agency_contacts": ["a@x.org", "b@x.org"],
            "logo": "https://img/x.png",
            "agency_hours": "9-5",
            "agency_latitude": "1.0",
            "updated_at": "2024-01-01 00:00:00",
        }
    )
    assert Agencies(client).to_request(agency) == {
        "agency_name": "Helping Hands",
        "agency_city": "Springfield",
        "agency_state": "IL",
        "agency_status": "active",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `just test tests/test_agencies.py -k to_request`
Expected: FAIL — `agency_contacts` present as a list.

- [ ] **Step 3: Implement**

In `Agencies` (which already imports `Any`), after `request_fields`:

```python
    def to_request(self, obj: Agency) -> dict[str, Any]:
        """Filter a fetched agency to the shape ``PUT /agencies/{id}`` wants.

        ``agency_contacts`` is **left out**: the read object returns a list
        of strings, the request schema takes a single string, and the spec
        does not say how the two relate. Sending the list back would either
        be rejected or mangle the field, so a merged update never carries it.
        Pass ``agency_contacts="..."`` explicitly to :meth:`patch` to set it.
        """
        body = super().to_request(obj)
        body.pop("agency_contacts", None)
        return body
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `just test tests/test_agencies.py` → pass.

- [ ] **Step 5: Commit**

```bash
git add src/get_connected_client/resources/agencies.py tests/test_agencies.py
git commit -m "feat: Agencies.to_request leaves agency_contacts out of merged updates"
```

---

### Task 7: CLI helper (`run_update`, `confirm_patch`) and the `users update` command

**Goal:** The shared merged-update flow for the CLI, wired into `galaxy users update` with the full test set (prompt, no-change, `--replace`, decline).

**Files:**
- Create: `src/get_connected_client/cli/_update.py`
- Modify: `src/get_connected_client/cli/_confirm.py`
- Modify: `src/get_connected_client/cli/users.py` (the `update_user` command)
- Test: `tests/test_users.py`

**Acceptance Criteria:**
- [ ] `--yes users update 5 --data '{"user_city":"X"}'` GETs `/users/5`, then PUTs the translated row with `user_city` overlaid
- [ ] Prompt shows `PUT /users/5 (merged over the current record)` and a table with only the changed fields; unchanged values do not appear
- [ ] No changes → exit 0, "No changes" on stderr, no PUT; under `--format json` stdout is `{"changes": []}`
- [ ] `--replace` sends the given fields verbatim with no GET
- [ ] Declining at the prompt makes no PUT

**Verify:** `just test tests/test_users.py -k cli_update` → pass

**Steps:**

- [ ] **Step 1: Write the failing tests**

In `tests/test_users.py`, **replace** `test_cli_update_merges_data` with:

```python
def test_cli_update_merges_over_current_record(api, cli_env):
    api.get("/users/5").respond(json={"data": USER_ROW})
    route = api.put("/users/5").respond(json={"data": USER_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "users",
            "update",
            "5",
            "--fname",
            "Ada",
            "--data",
            '{"user_city":"X"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "user_fname": "Ada",
        "user_lname": "Lovelace",
        "user_email": "ada@example.com",
        "user_status": "active",
        "user_city": "X",
    }


def test_cli_update_prompt_shows_only_changes(api, cli_env):
    api.get("/users/5").respond(json={"data": USER_ROW})
    route = api.put("/users/5").respond(json={})
    result = runner.invoke(
        app, ["users", "update", "5", "--data", '{"user_city":"X"}'], input="y\n"
    )
    assert result.exit_code == 0, result.output
    assert "PUT /users/5" in result.output
    assert "merged over the current record" in result.output
    assert "user_city" in result.output
    assert "(none)" in result.output
    # Unchanged fields are carried over silently, not listed.
    assert "Lovelace" not in result.output
    assert route.called


def test_cli_update_declined_makes_no_put(api, cli_env):
    api.get("/users/5").respond(json={"data": USER_ROW})
    result = runner.invoke(
        app, ["users", "update", "5", "--data", '{"user_city":"X"}'], input="n\n"
    )
    assert result.exit_code != 0
    assert [c.request.method for c in api.calls] == ["GET"]


def test_cli_update_no_changes_makes_no_put(api, cli_env):
    api.get("/users/5").respond(json={"data": USER_ROW})
    result = runner.invoke(app, ["--yes", "users", "update", "5", "--fname", "Ada"])
    assert result.exit_code == 0, result.output
    assert "No changes" in result.stderr
    assert [c.request.method for c in api.calls] == ["GET"]


def test_cli_update_no_changes_json(api, cli_env):
    api.get("/users/5").respond(json={"data": USER_ROW})
    result = runner.invoke(
        app, ["--yes", "--format", "json", "users", "update", "5", "--fname", "Ada"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"changes": []}


def test_cli_update_replace_sends_raw_body(api, cli_env):
    route = api.put("/users/5").respond(json={"data": USER_ROW})
    result = runner.invoke(
        app,
        [
            "--yes",
            "users",
            "update",
            "5",
            "--replace",
            "--fname",
            "Ada",
            "--data",
            '{"user_city":"X"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert [c.request.method for c in api.calls] == ["PUT"]
    assert json.loads(route.calls.last.request.content) == {
        "user_fname": "Ada",
        "user_city": "X",
    }
```

Check the existing `--format` global option spelling in `tests/test_cli_root.py` / `cli/__init__.py` before relying on `["--format", "json"]`; if it is `--json` or positional, use that form.

- [ ] **Step 2: Run tests to verify they fail**

Run: `just test tests/test_users.py -k cli_update`
Expected: failures — no GET made, `--replace` unknown option.

- [ ] **Step 3: Implement `confirm_patch` in `cli/_confirm.py`**

Replace the module with:

```python
"""Interactive gate in front of every CLI write against production."""

from __future__ import annotations

import json
from typing import Any

import typer
from rich.table import Table
from rich.text import Text

from ..resources.base import PatchPlan
from ._output import console


def confirm_write(state: Any, description: str, payload: Any = None) -> None:
    """Show what is about to be written and require consent (unless ``--yes``).

    :raises typer.Abort: the operator declined.
    """
    if state.assume_yes:
        return
    console.print(f"[bold red]About to write to the API:[/] {description}")
    if payload is not None:
        console.print_json(json.dumps(payload, default=str))
    if not typer.confirm("Proceed?"):
        raise typer.Abort()


def _cell(value: Any) -> Text:
    """Render one table cell; user data goes through ``Text`` so ``[`` in a
    value can never be read as rich markup."""
    if value is None:
        return Text("(none)", style="dim")
    if isinstance(value, str):
        return Text(value)
    return Text(json.dumps(value, default=str))


def confirm_patch(state: Any, description: str, plan: PatchPlan) -> None:
    """Show only what a merged update changes and require consent.

    The payload on the wire is the whole record (see
    :meth:`~get_connected_client.resources.base.UpdateMixin.prepare_patch`);
    printing it would bury the two fields the operator typed under thirty
    they did not. So this lists the changed fields alone, current value
    beside new, and says the rest is carried over.

    :raises typer.Abort: the operator declined.
    """
    if state.assume_yes:
        return
    console.print(
        f"[bold red]About to write to the API:[/] {description} "
        "(merged over the current record)"
    )
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("field")
    table.add_column("current")
    table.add_column("new")
    for change in plan.changes:
        table.add_row(change.field, _cell(change.old), _cell(change.new))
    console.print(table)
    if not typer.confirm("Proceed?"):
        raise typer.Abort()
```

- [ ] **Step 4: Create `cli/_update.py`**

```python
"""The merged-update flow every ``update`` command shares.

The API's PUT is a full replacement, so a bare ``--data '{"x": 1}'`` is
rejected with 422 for every required field it lacks. Each ``update`` command
therefore hands its fields to :func:`run_update`, which fetches the record,
merges, shows the diff and sends the whole body -- unless ``--replace`` asks
for the raw PUT.
"""

from __future__ import annotations

import json
from typing import Any

import typer

from ._confirm import confirm_patch, confirm_write
from ._output import OutputFormat, console, err_console, output_result

#: The ``--replace`` option, shared by every ``update`` command.
REPLACE = typer.Option(
    False,
    "--replace",
    help=(
        "Send only the given fields as the whole PUT body: no fetch, no "
        "merge. The API rejects a body missing any required field."
    ),
)


def run_update(
    state: Any, resource: Any, id: int, fields: dict[str, Any], *, replace: bool
) -> None:
    """Confirm and send an update of *id* on *resource*.

    With *replace* false (the default) the record is fetched, *fields* are
    merged over it and only the changed fields are shown for confirmation;
    when nothing would change, nothing is written. With *replace* true,
    *fields* are shown and sent verbatim, exactly as before this flow
    existed.

    :param resource: a namespace with ``url``, ``prepare_patch`` and
        ``update`` (any :class:`~get_connected_client.resources.base.UpdateMixin`).
    """
    target = f"PUT {resource.url(id)}"
    if replace:
        confirm_write(state, target, fields)
        output_result(state, resource.update(id, **fields))
        return
    plan = resource.prepare_patch(id, **fields)
    if not plan.changes:
        if state.format is OutputFormat.JSON:
            console.print_json(json.dumps({"changes": []}))
        else:
            err_console.print(
                "[yellow]No changes:[/] every supplied field already has that value."
            )
        return
    confirm_patch(state, target, plan)
    output_result(state, resource.update(id, **plan.body))
```

- [ ] **Step 5: Wire `users update`**

In `cli/users.py` add `from ._update import REPLACE, run_update` to the imports, then replace `update_user`:

```python
@users_app.command("update")
@handle_errors
def update_user(
    ctx: typer.Context,
    id: int = _ID,
    fname: str | None = typer.Option(None, "--fname", help="First name."),
    lname: str | None = typer.Option(None, "--lname", help="Last name."),
    email: str | None = typer.Option(None, "--email", help="Email address."),
    data: str | None = typer.Option(
        None, "--data", help="JSON object of any further user_* fields."
    ),
    replace: bool = REPLACE,
) -> None:
    """Update a user, merging the fields you name over the current record."""
    state = get_state(ctx)
    run_update(
        state,
        state.client.users,
        id,
        _user_fields(data, fname, lname, email),
        replace=replace,
    )
```

`confirm_write` stays imported in `users.py` because `create` and the sub-resource commands still use it.

- [ ] **Step 6: Run tests to verify they pass**

Run: `just test tests/test_users.py` → pass. `just check` → clean.

- [ ] **Step 7: Commit**

```bash
git add src/get_connected_client/cli/_confirm.py src/get_connected_client/cli/_update.py src/get_connected_client/cli/users.py tests/test_users.py
git commit -m "feat(cli): users update merges over the current record; --replace keeps the raw PUT"
```

---

### Task 8: Wire the other eight `update` commands

**Goal:** agencies, needs, events, hours, responses, groups, qualifications and benchmarks all use `run_update`; their existing CLI tests are updated to the merged body; needs gets a CLI test proving translation end to end.

**Files:**
- Modify: `src/get_connected_client/cli/{agencies,needs,events,hours,responses,groups,qualifications,benchmarks}.py`
- Test: `tests/test_agencies.py`, `tests/test_needs.py`, `tests/test_events_hours.py`, `tests/test_responses_teams_groups.py`, `tests/test_quals_benchmarks_misc.py`

**Acceptance Criteria:**
- [ ] Every `update` command accepts `--replace` and calls `run_update`
- [ ] Every `*_update_merges_data` test registers the GET and asserts the merged body
- [ ] `test_cli_update_translates_nested_need` passes (agency_id/tags/groups flattened, no shifts)
- [ ] Full suite green

**Verify:** `just test` → all pass

**Steps:**

- [ ] **Step 1: Update the existing tests (they will fail until Step 3)**

Each existing `..._update_merges_data` test gains a GET route on the line before its PUT route and a new expected body. Apply exactly:

`tests/test_agencies.py::test_cli_update_merges_data` — add `api.get("/agencies/9").respond(json={"data": AGENCY_ROW})`; expected body:
```python
    {
        "agency_name": "Helping Hands",
        "agency_city": "X",
        "agency_state": "IL",
        "agency_status": "active",
    }
```

`tests/test_needs.py::test_cli_update_merges_data` — add `api.get("/needs/42").respond(json={"data": NEED_ROW})`; expected body:
```python
    {"need_title": "Park Cleanup", "need_status": "inactive", "need_date": "2024-03-01"}
```

`tests/test_events_hours.py::test_cli_events_update_merges_data` — add `api.get("/events/42").respond(json={"data": EVENT_ROW})`; expected body:
```python
    {
        "event_title": "Volunteer Fair",
        "event_date_start": "2024-03-01 08:00:00",
        "event_location": "Town Hall",
    }
```

`tests/test_events_hours.py::test_cli_hours_update_merges_data` — add `api.get("/hours/7").respond(json={"data": HOUR_ROW})`; expected body:
```python
    {
        "hour_hours": "3",
        "hour_start": "2024-03-01 08:00:00",
        "hour_status": "denied",
        "hour_location": "Park",
    }
```

`tests/test_responses_teams_groups.py::test_cli_responses_update_merges_data` — add `api.get("/responses/7").respond(json={"data": RESPONSE_ROW})`; expected body:
```python
    {"response_date_added": "2024-03-01 12:00:00", "response_note": "Bring gloves and hat"}
```

`tests/test_responses_teams_groups.py::test_cli_groups_update_merges_data` — add `api.get("/groups/9").respond(json={"data": GROUP_ROW})`; expected body:
```python
{
    "ug_title": "Rotary Club",
    "ug_status": "inactive",
    "ug_description": "Local service club",
}
```

`tests/test_quals_benchmarks_misc.py::test_cli_qualifications_update_merges_data` — add `api.get("/qualifications/11").respond(json={"data": QUALIFICATION_ROW})`; expected body:
```python
    {
        "qualification_title": "Background Check",
        "qualification_status": "inactive",
        "qualification_type": "select",
    }
```

`tests/test_quals_benchmarks_misc.py::test_cli_benchmarks_update_merges_data` — add `api.get("/benchmarks/5").respond(json={"data": BENCHMARK_ROW})`; expected body:
```python
    {"benchmark_status": "inactive", "benchmark_title": "10 Hours", "benchmark_hours": "10"}
```

Add to `tests/test_needs.py`:

```python
def test_cli_update_translates_nested_need(api, cli_env):
    api.get("/needs/42").respond(
        json={
            "data": {
                **NEED_ROW,
                "agency": {"id": "3", "agency_name": "Helping Hands"},
                "tags": [{"id": "1", "name": "Outdoors"}],
                "groups": [{"id": "7", "group_title": "Rotary"}],
                "shifts": [{"id": "99", "start": "2024-03-01 08:00:00", "slots": 5}],
            }
        }
    )
    route = api.put("/needs/42").respond(json={"data": NEED_ROW})
    result = runner.invoke(
        app,
        ["--yes", "needs", "update", "42", "--data", '{"need_body":"Bring gloves"}'],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {
        "need_title": "Park Cleanup",
        "need_status": "active",
        "need_date": "2024-03-01",
        "need_body": "Bring gloves",
        "agency_id": "3",
        "tags": ["Outdoors"],
        "groups": ["7"],
    }
```

Also add one `--replace` test for a translated resource so the escape hatch is covered outside users, in `tests/test_needs.py`:

```python
def test_cli_update_replace_skips_fetch(api, cli_env):
    route = api.put("/needs/42").respond(json={"data": NEED_ROW})
    result = runner.invoke(
        app, ["--yes", "needs", "update", "42", "--replace", "--title", "T"]
    )
    assert result.exit_code == 0, result.output
    assert [c.request.method for c in api.calls] == ["PUT"]
    assert json.loads(route.calls.last.request.content) == {"need_title": "T"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `just test tests/test_agencies.py tests/test_needs.py tests/test_events_hours.py tests/test_responses_teams_groups.py tests/test_quals_benchmarks_misc.py -k update`
Expected: the eight rewritten tests fail on body mismatch; the two new needs tests fail (`--replace` unknown / body mismatch).

- [ ] **Step 3: Wire each command**

In each of the eight CLI modules: add `from ._update import REPLACE, run_update` to the imports; add `replace: bool = REPLACE,` as the last parameter of the `update` command; change its docstring from "sending only the fields you name" to "merging the fields you name over the current record"; replace the body's last two lines. The resulting bodies:

`agencies.py`:
```python
state = get_state(ctx)
run_update(
    state, state.client.agencies, id, _agency_fields(data, name), replace=replace
)
```

`needs.py`:
```python
state = get_state(ctx)
run_update(
    state,
    state.client.needs,
    id,
    _need_fields(data, title, body, agency_id),
    replace=replace,
)
```

`events.py`:
```python
state = get_state(ctx)
run_update(
    state,
    state.client.events,
    id,
    _event_fields(data, title, description),
    replace=replace,
)
```

`hours.py`:
```python
    state = get_state(ctx)
    run_update(
        state,
        state.client.hours,
        id,
        _hour_fields(data, user_id, response_id, hours, miles, start, status),
        replace=replace,
    )
```

`responses.py`:
```python
    state = get_state(ctx)
    run_update(
        state,
        state.client.responses,
        id,
        _response_fields(data, need_id, user_id, team_id, note),
        replace=replace,
    )
```

`groups.py` (also extend the `--data` help to `"JSON object of any further ug_* fields. ug_type is required by the API and never returned, so a merged update must include it."`):
```python
state = get_state(ctx)
run_update(
    state, state.client.groups, id, _group_fields(data, title, status), replace=replace
)
```

`qualifications.py`:
```python
state = get_state(ctx)
run_update(
    state,
    state.client.qualifications,
    id,
    _qualification_fields(data, title),
    replace=replace,
)
```

`benchmarks.py`:
```python
state = get_state(ctx)
run_update(
    state,
    state.client.benchmarks,
    id,
    _benchmark_fields(data, title, hours),
    replace=replace,
)
```

If `confirm_write` is no longer referenced in a module after this (check with `grep -n confirm_write`), remove it from that module's imports; ruff will flag it otherwise.

- [ ] **Step 4: Run the full suite and static checks**

Run: `just fix && just test && just check`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add src/get_connected_client/cli/ tests/
git commit -m "feat(cli): every update command merges over the current record"
```

---

### Task 9: Documentation

**Goal:** The CLI reference and quickstart explain merged updates, `--replace`, the no-change exit and the three caveats; the library docs pick up `patch`.

**Files:**
- Modify: `doc/source/cli.rst` (new section after "Free-form fields with ``--data``")
- Modify: `doc/source/quickstart.rst` (a `patch` example near the library usage; the "Write safety" section)

**Acceptance Criteria:**
- [ ] `just check-docs` passes (doc8)
- [ ] `just docs` builds without warnings from the new text
- [ ] `PatchPlan`/`Change`/`patch`/`prepare_patch`/`to_request` render on the API page (they are in `resources.base`, already automodule'd)

**Verify:** `just check-docs` → clean; `uv run --no-sync sphinx-build -W -b html doc/source /tmp/docs-out` → exit 0 (or `just docs`)

**Steps:**

- [ ] **Step 1: Add the CLI section**

Append to `doc/source/cli.rst` after the "Free-form fields with ``--data``" section:

```rst
Updates are merged
------------------

The API's ``PUT`` replaces the whole record: every field its request schema
marks required must be present, whatever the record already holds. Sending
only ``--data '{"user_notes": "..."}'`` would be answered with a 422 listing
the first name, last name, email and status as missing.

So every ``update`` command first fetches the record, converts it into a
valid request body, lays the fields you named over it, and sends the
result. The confirmation prompt shows only what changes:

.. code-block:: text

   $ galaxy users update 10253823 --data '{"user_notes": "Prefers mornings."}'
   About to write to the API: PUT /users/10253823 (merged over the current record)
   field        current   new
   user_notes   (none)    Prefers mornings.
   Proceed? [y/N]:

If nothing you named differs from the record, nothing is written: the
command says so on stderr and exits 0 (under ``--format json`` it prints
``{"changes": []}``).

``--replace`` skips the fetch and merge and sends exactly the fields you
gave, as the whole body -- the behaviour before this flow existed. Use it
when you already have a complete body, or when the merge gets in your way.

Three things the merge cannot do, because the API's read and write shapes
disagree:

* ``groups update`` still needs ``ug_type`` (``gc`` or ``slm``) in
  ``--data``. The API requires it on every write and never returns it.
* ``needs update`` never carries the record's shifts into the body; the
  read shape does not match the write shape, and resending could duplicate
  shifts that ``needs add-shift`` / ``needs remove-shift`` manage. Pass
  ``shifts`` in ``--data`` if you mean to set them.
* ``agencies update`` never carries ``agency_contacts``; it is a list on
  read and a string on write with no documented relationship. Set it
  explicitly in ``--data``.
```

- [ ] **Step 2: Add the library example to the quickstart**

In `doc/source/quickstart.rst`, in the library-usage part (near the existing `client.agencies.get(1)` example around line 135), add:

```rst
To change a few fields on a record, use ``patch``: it fetches the row,
merges your fields over it and sends the whole body, which is what the
API's full-replacement ``PUT`` demands. ``update`` sends exactly what you
give it and is for when you already hold a complete body.

.. code-block:: python

   client.users.patch(10253823, user_notes="Prefers mornings.")

   # Or look before you leap:
   plan = client.users.prepare_patch(10253823, user_notes="Prefers mornings.")
   for change in plan.changes:
       print(change.field, change.old, "->", change.new)
   client.users.update(10253823, **plan.body)
```

In the "Write safety, in brief" section, after the delete example, add one sentence: "``update`` commands go further and show only the fields that will change, since the body they send is the whole record merged with your input -- see :ref:`the CLI reference <cli:Updates are merged>`." (If the `:ref:` target does not resolve, use ``:doc:`cli``` instead.)

- [ ] **Step 3: Build and lint the docs**

Run: `just check-docs` → clean. Run: `just docs` (or the sphinx-build line in **Verify**) → no new warnings.

- [ ] **Step 4: Commit**

```bash
git add doc/source/cli.rst doc/source/quickstart.rst
git commit -m "docs: merged updates, --replace, and the three read/write gaps"
```

---

## Self-review

**Spec coverage.** `request_fields` + `to_request` (Task 1, 2); six overrides with the shifts/contacts exclusions and the `ug_type` note (Tasks 3–6); `prepare_patch`/`patch`/`PatchPlan`/`Change` + corrected `update` docstring + exports (Task 1); spec-conformance test (Task 2); `confirm_patch`, `run_update`, `--replace`, no-change exit with JSON form (Task 7, 8); docs (Task 9). No live test added, as the spec says.

**Type consistency.** `Change(field, old, new)` and `PatchPlan(current, body, changes)` are used with those names in Tasks 1, 7. `REPLACE`/`run_update` names match between Task 7's `_update.py` and Task 8's call sites. `to_request(self, obj: <Model>)` overrides call `super().to_request(obj)` in every task.

**Placeholders.** None; every step carries its code. The one conditional instruction (the `--format json` spelling in Task 7 and the `:ref:` target in Task 9) tells the implementer exactly how to resolve it.
