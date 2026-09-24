from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from hone.core.clock import utc_now
from hone.engines.checkins import Checkin, Streak
from hone.engines.overview import Overview
from hone.engines.progress import ModuleLink, ModuleStatus, ModuleView, TrackView
from hone.engines.sessions import SessionView
from hone.voice import MODULE_STATUS_LABELS, streak_message


class ChallengeOut(BaseModel):
    problem: str
    next_step: str


class StreakOut(BaseModel):
    current: int
    longest: int
    checked_in_today: bool
    message: str

    @classmethod
    def from_streak(cls, streak: Streak) -> StreakOut:
        return cls(
            current=streak.current,
            longest=streak.longest,
            checked_in_today=streak.checked_in_today,
            message=streak_message(streak),
        )


class CheckinOut(BaseModel):
    day: date
    intention: str

    @classmethod
    def from_checkin(cls, checkin: Checkin) -> CheckinOut:
        return cls(day=checkin.day, intention=checkin.intention)


class SessionOut(BaseModel):
    module_key: str | None
    module_title: str | None
    started_at: datetime
    minutes: int

    @classmethod
    def from_session(cls, session: SessionView) -> SessionOut:
        return cls(
            module_key=session.module_key,
            module_title=session.module_title,
            started_at=session.started_at,
            minutes=session.elapsed_minutes(utc_now()),
        )


class DayMinutesOut(BaseModel):
    day: date
    minutes: int


class ModuleLinkOut(BaseModel):
    key: str
    title: str

    @classmethod
    def from_link(cls, link: ModuleLink) -> ModuleLinkOut:
        return cls(key=link.key, title=link.title)


class ModuleOut(BaseModel):
    key: str
    track_slug: str
    slug: str
    title: str
    summary: str
    position: int
    status: ModuleStatus
    status_label: str
    prerequisites: list[ModuleLinkOut]
    missing_prerequisites: list[ModuleLinkOut]

    @classmethod
    def from_view(cls, module: ModuleView) -> ModuleOut:
        return cls(
            key=module.key,
            track_slug=module.track_slug,
            slug=module.slug,
            title=module.title,
            summary=module.summary,
            position=module.position,
            status=module.status,
            status_label=MODULE_STATUS_LABELS[module.status],
            prerequisites=[ModuleLinkOut.from_link(link) for link in module.prerequisites],
            missing_prerequisites=[
                ModuleLinkOut.from_link(link) for link in module.missing_prerequisites
            ],
        )


class ModuleDetailOut(ModuleOut):
    track_name: str
    content_html: str


class TrackSummaryOut(BaseModel):
    slug: str
    name: str
    description: str
    completed: int
    total: int

    @classmethod
    def from_view(cls, track: TrackView) -> TrackSummaryOut:
        return cls(
            slug=track.slug,
            name=track.name,
            description=track.description,
            completed=track.completed_count,
            total=track.total_count,
        )


class TrackDetailOut(TrackSummaryOut):
    modules: list[ModuleOut]

    @classmethod
    def from_track(cls, track: TrackView) -> TrackDetailOut:
        summary = TrackSummaryOut.from_view(track)
        return cls(**summary.model_dump(), modules=[ModuleOut.from_view(m) for m in track.modules])


class OverviewOut(BaseModel):
    user_name: str
    today: date
    streak: StreakOut
    todays_checkin: CheckinOut | None
    active_session: SessionOut | None
    study_minutes: list[DayMinutesOut]
    tracks: list[TrackSummaryOut]
    next_modules: list[ModuleOut]

    @classmethod
    def from_overview(cls, user_name: str, overview: Overview) -> OverviewOut:
        return cls(
            user_name=user_name,
            today=overview.today,
            streak=StreakOut.from_streak(overview.streak),
            todays_checkin=CheckinOut.from_checkin(overview.todays_checkin)
            if overview.todays_checkin
            else None,
            active_session=SessionOut.from_session(overview.active_session)
            if overview.active_session
            else None,
            study_minutes=[
                DayMinutesOut(day=day, minutes=minutes) for day, minutes in overview.study_minutes
            ],
            tracks=[TrackSummaryOut.from_view(track) for track in overview.tracks],
            next_modules=[ModuleOut.from_view(module) for module in overview.next_modules],
        )
