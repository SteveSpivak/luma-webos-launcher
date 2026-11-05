#!/usr/bin/env python3
"""Deterministic OFFLINE model of webOS applicationManager launch and Nuvio startup.
Synthetic state only: not a claim of real webOS or Nuvio semantics.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from nuvio_launch_contract import validate_launch

STARTUP = {"setup", "login", "profiles", "pin"}
@dataclass
class MockNuvio:
    installed: bool = True
    route: str = "home"
    current_title: str | None = None
    pending: str | None = None
    selected_profile: str | None = "demo"
    launches: int = 0
    opened: int = 0
    playing: bool = False
    history: list[str] = field(default_factory=list)

    def launch(self, request: object) -> dict:
        req = validate_launch(request)
        if not self.installed:
            return {"returnValue": False, "errorCode": -1, "errorText": "Application not installed"}
        title = req["params"]["contentTarget"]
        self.launches += 1
        if self.route in STARTUP or self.selected_profile is None:
            self.pending = title  # last valid relaunch wins; Nuvio parser behavior hypothesis
            return {"returnValue": True, "deferred": True}
        self._open(title)
        return {"returnValue": True, "deferred": False}

    def ready(self, profile: str, route: str = "home") -> bool:
        if not profile or route in STARTUP:
            raise ValueError("must have a selected profile and non-startup route")
        self.selected_profile = profile
        self.route = route
        if self.pending is None:
            return False
        title, self.pending = self.pending, None
        self._open(title)
        return True

    def _open(self, title: str) -> None:
        if self.current_title == title and self.route == "detail":
            return
        if self.route != "detail":
            self.history.append(self.route)
        self.current_title, self.route = title, "detail"
        self.opened += 1
        # No play call. We model navigation only, not decoder/media state.

    def back(self) -> str:
        self.route = self.history.pop() if self.history else "home"
        return self.route

    def switch_profile(self) -> None:
        # Explicit privacy safeguard proposed for Luma, not established Nuvio behavior.
        self.selected_profile, self.pending, self.current_title = None, None, None
        self.route, self.history = "profiles", []

@dataclass
class MockApplicationManager:
    nuvio: MockNuvio = field(default_factory=MockNuvio)
    calls: list[dict] = field(default_factory=list)

    def call(self, uri: str, payload: object) -> dict:
        if uri != "luna://com.webos.applicationManager/launch":
            raise ValueError("unrecognized service")
        self.calls.append(validate_launch(payload))
        return self.nuvio.launch(payload)
