# Merged Updates (read-merge-write) — Design

**Date:** 2026-09-20
**Status:** Approved

## Problem

Galaxy Digital's `PUT /{resource}/{id}` endpoints treat the body as a full
replacement, not a patch. The spec's request schemas mark several fields
required on every PUT, so sending only the fields you want to change is
rejected:

```
$ galaxy users update 10253823 --data '{"user_notes": "This is a note."}'
error: HTTP 422: {"message":"The given data was invalid.","errors":{
  "user_fname":["The user fname field is required."], ...}}
```

`UpdateMixin.update`'s docstring currently claims "only the supplied fields
are sent, so this is a partial update". The first half is true, the second is
false. The CLI's nine `update` commands inherit the same misbehaviour.

## Goal

A CLI operator (or Python caller) supplies only the fields they want to
change. The client fetches the current record, turns it into a valid request
body, overlays the supplied fields, and PUTs the result. The confirmation
prompt shows only what changed.

## Non-goals

- Changing `create`.
- Client-side validation of required fields. The API is the authority; its
  422 is surfaced unchanged.
- Making the raw PUT go away. `update` stays as the escape hatch.

## API facts driving the design

Comparing each resource's read object against its PUT request schema in
`doc/api.yml`:

| resource      | read → write differences                                                                                       |
|---------------|----------------------------------------------------------------------------------------------------------------|
| user          | drop `id`, `domain_id`, `domain_sitename`, `created_at`, `updated_at`                                          |
| qualification | drop `id`, `domain_id`, `qualification_cat_id`, timestamps                                                     |
| benchmark     | drop `id`, `created_at`, `update_at`                                                                           |
| need          | `agency` → `agency_id`; `initiative` → `initiative_id`; `tags` objects → names; `groups` objects → ids; `shifts` objects ≠ `shiftRequestSchema`; drop the rest |
| event         | `tags` objects → `event_tags` names; drop `id`, `domain_id`, timestamps                                         |
| group         | drop `agencies`, `needs`, `users`, `questions_*`, ids, timestamps. **`ug_type` is required on write and absent on read.** |
| hour          | `user` → `user_id`; `groups` → `group_ids`; `hour_date_start` → `hour_start`; drop `need`, `hour_date_end`, `hour_description`, `hour_parent`, `hour_source`, `hour_type`, ids, timestamps |
| response      | `need` → `need_id`; `user` → `user_id`; `shift` → `schedule_ids`; `team` → `team_id`; drop `agency`, `initiative`, `answers`, `response_*` read-only fields |
| agency        | `agency_contacts` is `array<string>` on read, `string` on write (format undocumented); drop `logo`, `agency_hours`, `agency_extra_location`, lat/long, ids, timestamps |

Three resources need only a key filter; six need a translation step.

## Design

### Library

**`Resource` gains two hooks.**

```python
class Resource(Generic[M]):
    path: str
    model: type[M]
    #: Property names of this resource's PUT/POST request schema in doc/api.yml.
    request_fields: frozenset[str] = frozenset()

    def to_request(self, obj: M) -> dict[str, Any]:
        """Turn a fetched model into a request body the PUT endpoint accepts."""
```

The base `to_request` dumps the model by alias, drops `None` values, and keeps
only keys in `request_fields`. That is the whole story for users,
qualifications and benchmarks.

Six subclasses override `to_request` (calling the base first, then patching
the result):

- **Needs**: `agency_id = agency.id`; `initiative_id = initiative.id`;
  `tags = [t.name]`; `groups = [str(g.id)]`. `shifts` is **removed** from the
  merge base: the read shape does not match `shiftRequestSchema`, and
  resending shifts risks duplicating rows that `add_shift`/`remove_shift`
  already manage. Shifts are only sent when the caller supplies them.
- **Events**: `event_tags = [t.name for t in tags]`.
- **Groups**: base filter only. `ug_type` cannot be derived; the caller must
  supply it or the API answers 422. Documented on the method and in the CLI
  reference.
- **Hours**: `user_id = user.id`; `group_ids = [str(g.id) ...]` (the read
  side's `groups` is a single `groupMiniObject` ref in the spec; handle both a
  single object and a list); `hour_start = hour_date_start`.
- **Responses**: `need_id = need.id`; `user_id = user.id`;
  `schedule_ids = [str(shift.id)]` when a shift is present; `team_id = team.id`
  when present.
- **Agencies**: `agency_contacts` is **removed** from the merge base (list on
  read, string on write, no documented join format). Sent only if supplied.

All ids in translated bodies are sent as strings, matching the spec's
`type: string, format: number`.

**`UpdateMixin` gains `prepare_patch` and `patch`.**

```python
@dataclass
class PatchPlan:
    current: dict[str, Any]   # to_request(fetched row)
    body: dict[str, Any]      # current | supplied fields
    changes: list[Change]     # keys whose value differs, with old and new

@dataclass
class Change:
    field: str
    old: Any   # None when the field was absent
    new: Any

class UpdateMixin(Resource[M]):
    def update(self, id, **fields): ...           # unchanged raw PUT
    def prepare_patch(self, id, **fields) -> PatchPlan: ...
    def patch(self, id, **fields): ...            # prepare_patch + update(**plan.body)
```

`prepare_patch` requires the resource to also be a `GetMixin`; every resource
with an `UpdateMixin` already is. A supplied field whose value equals the
current value is not a change. A supplied field absent from `current` is a
change with `old=None`. The supplied fields always win, including fields
outside `request_fields` (the caller may know something the spec does not).

`update`'s docstring is corrected: the API treats PUT as a full replacement;
use `patch` to change a subset.

**Exports.** `PatchPlan` and `Change` are exported from
`get_connected_client.resources.base` and re-exported from the package root
alongside the existing public names.

### CLI

Every `update` command (agencies, benchmarks, events, groups, hours, needs,
qualifications, responses, users) changes from

```python
fields = _x_fields(...)
confirm_write(state, f"PUT {url}", fields)
output_result(state, state.client.x.update(id, **fields))
```

to

```python
fields = _x_fields(...)
if replace:
    confirm_write(state, f"PUT {url}", fields)
    output_result(state, state.client.x.update(id, **fields))
    return
plan = state.client.x.prepare_patch(id, **fields)
if not plan.changes:
    err_console.print("No changes: every supplied field already has that value.")
    return
confirm_patch(state, f"PUT {url}", plan)
output_result(state, state.client.x.update(id, **plan.body))
```

The repeated shape lives in one helper in `cli/_confirm.py` (or a sibling
module) so the nine commands stay one-liners:

```python
def run_update(state, resource, id, fields, *, replace) -> None
```

**`confirm_patch`** (new, next to `confirm_write`) prints:

```
About to write to the API: PUT /users/10253823 (merged over the current record)
  field          current            new
  user_notes     (none)             This is a note.
  user_comments  (none)             This is a comment.
Proceed? [y/N]:
```

Long values are truncated in the table (rich handles wrapping). `--yes`
skips the prompt exactly as `confirm_write` does. `--read-only` is enforced
by the client, unchanged.

**`--replace`** is a new flag on all nine update commands: "send only the
given fields as the whole PUT body (no fetch, no merge)". Help text for
`update` changes from "sending only the fields you name" to "merging the
fields you name over the current record".

**No-change exit.** When `plan.changes` is empty the command prints a note to
stderr and exits 0 without writing. In JSON mode it prints `{"changes": []}`
to stdout so scripts can detect it.

### Documentation

- `doc/source/cli.rst`: a short "Updates are merged" section covering the
  fetch-merge-PUT behaviour, `--replace`, the no-change exit, and the three
  caveats (group `ug_type`, need `shifts`, agency `agency_contacts`).
- `doc/source/quickstart.rst`: one example using `patch`.
- Docstrings on `patch`, `prepare_patch`, `to_request` and each override.

### Testing

- **Spec conformance** (`tests/test_resources_base.py` or a new
  `tests/test_request_fields.py`): for every resource class with
  `request_fields`, assert it equals the property names of the matching
  `*RequestSchema` in `doc/api.yml`. Mirrors the existing path-coverage
  assertion so upstream schema drift fails CI.
- **Translation** (one test per overriding resource, in the resource's
  existing test module): build a model from a representative read payload,
  call `to_request`, assert the flattened ids/names and the dropped keys.
- **`prepare_patch` / `patch`** (`tests/test_resources_base.py`, on the
  `Widgets` fixture resource): GET is mocked with respx, the resulting PUT
  body is asserted, `changes` is asserted for changed / unchanged / new
  fields, and a supplied field equal to current yields no change.
- **CLI** (`tests/test_users.py` plus one representative of the translated
  resources, e.g. `tests/test_needs.py`): the prompt shows only changed
  fields; `--yes` writes without prompting; `--replace` sends the raw body;
  no changes exits 0 with the stderr note and no PUT.
- **Live** (`tests/live/test_live_write.py`): no new live test. The
  user-in-the-loop write test remains cluster-only.

### Out of scope, noted for later

- `needRequestSchema` carries an `event_id` the read object never returns,
  so a need can be linked to an event on write only. Nothing to do here, but
  it corrects the earlier finding that needs and events are unrelated.
- A per-key `set_extras` / typed patch for sub-resources.
