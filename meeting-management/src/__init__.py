# -*- coding: utf-8 -*-
"""
Meeting Management Skill

AI callable interface for meeting transcription and minutes generation.
"""

from .meeting_skill import transcribe, generate_minutes, save_meeting, update_meeting, query_meetings

__all__ = ["transcribe", "generate_minutes", "save_meeting", "update_meeting", "query_meetings"]
