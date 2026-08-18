"""Models for the ``/agencies`` endpoints.

Field names are copied verbatim from ``doc/api.yml``; the API sends numeric
ids as strings and pydantic coerces them.
"""

from __future__ import annotations

from .base import GalaxyModel


class Agency(GalaxyModel):
    """agencyObject -- an organization on the site."""

    id: int | None = None
    domain_id: int | None = None
    agency_name: str | None = None
    agency_link: str | None = None
    agency_address: str | None = None
    agency_address2: str | None = None
    agency_city: str | None = None
    agency_state: str | None = None
    agency_postal: str | None = None
    agency_extra_location: str | None = None
    agency_phone: str | None = None
    agency_phone_extension: str | None = None
    agency_fax: str | None = None
    agency_twitter_link: str | None = None
    agency_facebook_link: str | None = None
    agency_instagram_link: str | None = None
    agency_youtube_link: str | None = None
    agency_linkedin_link: str | None = None
    agency_email: str | None = None
    agency_video: str | None = None
    agency_url: str | None = None
    agency_ein: str | None = None
    agency_comments: str | None = None
    agency_status: str | None = None
    agency_latitude: str | None = None
    agency_longitude: str | None = None
    agency_contact: str | None = None
    agency_contact_title: str | None = None
    agency_news: str | None = None
    agency_mission: str | None = None
    agency_contacts: list[str] | None = None
    agency_hours: str | None = None
    agency_partner: str | None = None
    logo: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
