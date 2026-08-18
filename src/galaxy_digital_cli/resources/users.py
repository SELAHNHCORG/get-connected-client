"""The ``/users`` namespace: CRUD plus every user sub-resource."""

from __future__ import annotations

from typing import Any

from ..exceptions import NotFoundError
from ..models.common import (
    AgencyMini,
    BenchmarkMini,
    Cause,
    Extra,
    Interest,
    Tag,
    TrackMini,
)
from ..models.hours import Hour
from ..models.users import (
    RegistrationAnswer,
    User,
    UserOneclick,
    UserOptouts,
    UserQualification,
    UserResponse,
)
from .base import (
    CreateMixin,
    DeleteMixin,
    GetMixin,
    ListMixin,
    Resource,
    UpdateMixin,
)


class Users(
    ListMixin[User],
    GetMixin[User],
    CreateMixin[User],
    UpdateMixin[User],
    DeleteMixin[User],
    Resource[User],
):
    """Users and everything hanging off them.

    Beyond the inherited CRUD, ``/users`` exposes twenty sub-resources --
    fanned agencies, benchmarks, causes, extras, hours, interests, optouts,
    qualifications, registration answers, responses, tracks and tags.

    :meth:`list` accepts the endpoint's own filters on top of the standard
    paging ones::

        client.users.list(user_status="active", user_email_like="@example.com")

    Supported filters: ``user_status``, ``user_fname``, ``user_lname``,
    ``user_email``, ``user_fname_like``, ``user_lname_like`` and
    ``user_email_like``.
    """

    path = "/users"
    model = User

    # -- agencies ---------------------------------------------------------

    def agencies(self, id: int) -> list[AgencyMini]:
        """The agencies this user has fanned."""
        return self._get_list(self._url(id, "agencies"), AgencyMini)

    def add_agency(self, id: int, agency_id: int) -> Any:
        """Fan *agency_id* on behalf of this user."""
        return self._client.request("POST", self._url(id, "agencies", agency_id))

    def remove_agency(self, id: int, agency_id: int) -> Any:
        """Drop this user's fan relationship with *agency_id*."""
        return self._client.request("DELETE", self._url(id, "agencies", agency_id))

    # -- benchmarks -------------------------------------------------------

    def benchmarks(self, id: int) -> list[BenchmarkMini]:
        """The benchmarks (service milestones) this user has earned."""
        return self._get_list(self._url(id, "benchmarks"), BenchmarkMini)

    def remove_benchmark(self, id: int, benchmark_id: int) -> Any:
        """Take *benchmark_id* away from this user."""
        return self._client.request("DELETE", self._url(id, "benchmarks", benchmark_id))

    # -- causes -----------------------------------------------------------

    def causes(self, id: int) -> list[Cause]:
        """The causes this user cares about."""
        return self._get_list(self._url(id, "causes"), Cause)

    def add_cause(self, id: int, cause_id: int) -> Any:
        """Assign *cause_id* to this user."""
        return self._client.request("POST", self._url(id, "causes", cause_id))

    def remove_cause(self, id: int, cause_id: int) -> Any:
        """Unassign *cause_id* from this user."""
        return self._client.request("DELETE", self._url(id, "causes", cause_id))

    # -- extras -----------------------------------------------------------

    def extras(self, id: int, subset: str | None = None) -> list[Extra]:
        """This user's custom key/value data.

        :param subset: ``"regExtra"`` (the server default) or ``"profile"``.
        :return: the stored pairs, or ``[]`` when the user has none -- the
            API answers 404 rather than an empty list.
        """
        url = self._url(id, "extras")
        params = {"subset": subset} if subset is not None else None
        try:
            rows = self._client.get_data(url, params) or []
        except NotFoundError:
            return []
        if not isinstance(rows, list):
            rows = [rows]
        return [self._parse(row, Extra) for row in rows]

    def set_extras(
        self,
        id: int,
        extras: list[dict[str, Any]] | dict[str, Any],
        subset: str | None = None,
    ) -> Any:
        """Replace this user's extras with *extras*.

        The spec's shape is ``{"extras": [{"key": ..., "value": ...}, ...]}``.
        The payload is the *entirety* of the user's extras for the subset, so
        an update must resend the pairs it wants to keep.

        :param extras: either the bare ``[{"key": ..., "value": ...}, ...]``
            list -- wrapped in the ``{"extras": ...}`` envelope for you -- or
            a dict that already contains that envelope, sent verbatim.
        :param subset: ``"regExtra"`` (the server default) or ``"profile"``.
        """
        body = {"extras": extras} if isinstance(extras, list) else extras
        params = {"subset": subset} if subset is not None else None
        return self._client.request(
            "POST", self._url(id, "extras"), params=params, json=body
        )

    # -- hours ------------------------------------------------------------

    def hours(self, id: int) -> list[Hour]:
        """The volunteer hours this user has submitted."""
        return self._get_list(self._url(id, "hours"), Hour)

    # -- interests --------------------------------------------------------

    def interests(self, id: int) -> list[Interest]:
        """The interests assigned to this user."""
        return self._get_list(self._url(id, "interests"), Interest)

    def add_interest(self, id: int, interest_id: int) -> Any:
        """Assign *interest_id* to this user."""
        return self._client.request("POST", self._url(id, "interests", interest_id))

    def remove_interest(self, id: int, interest_id: int) -> Any:
        """Unassign *interest_id* from this user."""
        return self._client.request("DELETE", self._url(id, "interests", interest_id))

    # -- messaging --------------------------------------------------------

    def send_welcome_email(self, id: int) -> Any:
        """Send this user the site's welcome email.

        A GET with a side effect: the spec models it as a read, but it puts
        mail in someone's inbox. Treat it as a write.
        """
        return self._client.request(
            "GET", self._url(id, "welcomeEmail"), treat_as_write=True
        )

    def oneclick(self, id: int) -> UserOneclick:
        """Mint a one-click (passwordless) login link for this user."""
        return self._get_one(self._url(id, "oneclick"), UserOneclick)

    def optouts(self, id: int) -> UserOptouts:
        """The message areas this user has opted out of.

        :raises NotFoundError: the user has not opted out of anything.
        """
        return self._get_one(self._url(id, "optouts"), UserOptouts)

    def add_optout(self, id: int, **body: Any) -> Any:
        """Opt this user out of messaging.

        The spec's body is ``optout_areas``, a list of area names (or
        ``["all"]``). It *supersedes* whatever was stored before::

            client.users.add_optout(5, optout_areas=["blast"])
        """
        return self._client.request("POST", self._url(id, "optouts"), json=body)

    def remove_optout(self, id: int, **body: Any) -> Any:
        """Remove areas from this user's opt-out list.

        Unlike :meth:`add_optout`, ``optout_areas`` here names only the areas
        to lift.
        """
        return self._client.request("DELETE", self._url(id, "optouts"), json=body)

    # -- qualifications ---------------------------------------------------

    def qualifications(self, id: int) -> list[UserQualification]:
        """The qualifications this user holds."""
        return self._get_list(self._url(id, "qualifications"), UserQualification)

    # -- registration questions -------------------------------------------

    def registration_answers(self, id: int) -> list[RegistrationAnswer]:
        """This user's answers to the site's custom registration questions."""
        return self._get_list(
            self._url(id, "registrationQuestions"), RegistrationAnswer
        )

    def set_registration_answers(self, id: int, answers: list[dict[str, Any]]) -> Any:
        """Store this user's answers to the custom registration questions.

        :param answers: the spec's ``answers`` array -- objects of
            ``{"question_id": ..., "answer": [...]}``. It is wrapped in the
            required ``{"answers": ...}`` envelope for you.
        """
        return self._client.request(
            "POST", self._url(id, "registrationQuestions"), json={"answers": answers}
        )

    # -- responses / tracks -----------------------------------------------

    def responses(self, id: int) -> list[UserResponse]:
        """The needs this user has signed up for."""
        return self._get_list(self._url(id, "responses"), UserResponse)

    def tracks(self, id: int) -> list[TrackMini]:
        """The tracks this user belongs to."""
        return self._get_list(self._url(id, "tracks"), TrackMini)

    # -- tags -------------------------------------------------------------

    def tags(self, id: int) -> list[Tag]:
        """The tags on this user."""
        return self._get_list(self._url(id, "tags"), Tag)

    def add_tags(self, id: int, tags: list[str]) -> Any:
        """Add *tags* -- names, not ids -- to this user."""
        return self._client.request("POST", self._url(id, "tags"), json={"tags": tags})

    def remove_tag(self, id: int, tag_id: int) -> Any:
        """Remove the tag with this id from the user."""
        return self._client.request("DELETE", self._url(id, "tags", tag_id))
