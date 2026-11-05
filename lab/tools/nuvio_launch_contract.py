#!/usr/bin/env python3
"""Offline, restrictive *outbound* Nuvio launch-contract model.
NOT a replacement for Nuvio's permissive inbound parser.
Use for unit fixtures and implementation planning. No app launch performed.
"""
from __future__ import annotations
import json
import re
from urllib.parse import quote
APP="space.nuvio.webos"
KINDS={"movie","series"}
PROVIDERS={"tmdb","imdb"}
SOURCE_ID=re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
TMDB_ID=re.compile(r"^[0-9]{1,12}$")
IMDB_ID=re.compile(r"^tt[0-9]{5,12}$")
def build_launch(media_type: str, provider: str, source_id: str) -> dict:
    if media_type not in KINDS or provider not in PROVIDERS or not isinstance(source_id,str):
        raise ValueError("invalid media type/provider/id")
    if not SOURCE_ID.fullmatch(source_id) or (provider=="tmdb" and not TMDB_ID.fullmatch(source_id)) or (provider=="imdb" and not IMDB_ID.fullmatch(source_id)):
        raise ValueError("invalid source ID")
    link=f"nuvio://{provider}/{media_type}/{quote(source_id,safe='')}"
    return {"id":APP,"params":{"contentTarget":link}}
def validate_launch(value: object) -> dict:
    if not isinstance(value,dict) or set(value)!={"id","params"} or value.get("id")!=APP:
        raise ValueError("unexpected app launch shape")
    params=value["params"]
    if not isinstance(params,dict) or set(params)!={"contentTarget"}:
        raise ValueError("unexpected launch parameters")
    link=params["contentTarget"]
    if not isinstance(link,str) or len(link)>160:
        raise ValueError("invalid length")
    match=re.fullmatch(r"nuvio://(tmdb|imdb)/(movie|series)/([A-Za-z0-9._:-]{1,64})",link)
    if not match:
        raise ValueError("invalid title URI")
    expected=build_launch(match.group(2),match.group(1),match.group(3))
    if expected!=value:
        raise ValueError("non-canonical launch")
    return value
def parse_untrusted_json(raw: str) -> dict:
    if not isinstance(raw,str) or len(raw)>512:
        raise ValueError("request too large")
    return validate_launch(json.loads(raw))
