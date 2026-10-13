"""Topic rotation and Asia/Kolkata calendar scheduling engine."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pytz
import yaml

from app.config import CONFIG_DIR, get_settings
from app.models import CalendarEntry, ContentPillar


class TopicRotationManager:
    """Manages the 30-day rotating schedule and loads editorial configurations."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or CONFIG_DIR
        self._load_configurations()

    def _load_configurations(self) -> None:
        """Load YAML and Markdown configuration files."""
        pillars_file = self.config_dir / "content_pillars.yaml"
        facts_file = self.config_dir / "company_facts.yaml"
        brand_file = self.config_dir / "brand_profile.md"

        if not pillars_file.exists():
            raise FileNotFoundError(f"Missing content pillars configuration: {pillars_file}")
        if not facts_file.exists():
            raise FileNotFoundError(f"Missing company facts configuration: {facts_file}")
        if not brand_file.exists():
            raise FileNotFoundError(f"Missing brand profile configuration: {brand_file}")

        with open(pillars_file, "r", encoding="utf-8") as f:
            pillars_data = yaml.safe_load(f)

        with open(facts_file, "r", encoding="utf-8") as f:
            self.company_facts = yaml.safe_load(f)

        with open(brand_file, "r", encoding="utf-8") as f:
            self.brand_profile_md = f.read()

        # Parse pillars
        self.pillars_by_id: Dict[str, ContentPillar] = {}
        for p in pillars_data.get("pillars", []):
            pillar = ContentPillar(**p)
            self.pillars_by_id[pillar.id] = pillar

        # Parse 30-day schedule
        self.schedule_by_day: Dict[int, CalendarEntry] = {}
        for s in pillars_data.get("schedule_30_days", []):
            entry = CalendarEntry(**s)
            self.schedule_by_day[entry.day] = entry

        if not self.schedule_by_day:
            raise ValueError("No schedule entries found in content_pillars.yaml")

    def get_current_kolkata_date(self) -> datetime:
        """Calculate the current datetime in the configured timezone (default: Asia/Kolkata)."""
        settings = get_settings()
        tz = pytz.timezone(settings.publish_timezone)
        return datetime.now(tz)

    def get_day_index_for_date(self, dt: datetime) -> int:
        """Map a date to a 1..30 calendar day using continuous day-of-year rotation."""
        day_of_year = dt.timetuple().tm_yday
        # 1-indexed modulo 30
        return ((day_of_year - 1) % 30) + 1

    def get_topic_for_date(self, target_date: Optional[datetime] = None) -> Tuple[str, CalendarEntry, ContentPillar, Dict[str, Any]]:
        """Retrieve topic, calendar entry, pillar, and relevant facts for a given date."""
        dt = target_date or self.get_current_kolkata_date()
        date_str = dt.strftime("%Y-%m-%d")
        day_index = self.get_day_index_for_date(dt)

        entry = self.schedule_by_day.get(day_index)
        if not entry:
            # Fallback to day 1 if somehow missing
            entry = self.schedule_by_day[1]

        pillar = self.pillars_by_id.get(entry.pillar_id)
        if not pillar:
            raise KeyError(f"Pillar ID '{entry.pillar_id}' defined in schedule day {day_index} not found in pillars list")

        # Extract relevant facts
        relevant_facts = self._extract_relevant_facts(entry.pillar_id)

        return date_str, entry, pillar, relevant_facts

    def _extract_relevant_facts(self, pillar_id: str) -> Dict[str, Any]:
        """Filter verified facts strictly relevant to the pillar to avoid prompt contamination."""
        context: Dict[str, Any] = {
            "founder": self.company_facts.get("founder", {}),
            "allowed_talking_points": [],
            "strictly_forbidden": []
        }

        companies = self.company_facts.get("companies", {})
        if "kodetocareer" in pillar_id.lower():
            ktc = companies.get("kodetocareer", {})
            context["company"] = {
                "name": ktc.get("name"),
                "mission": ktc.get("mission"),
                "domain": ktc.get("domain"),
                "core_pillars": ktc.get("core_pillars", [])
            }
            context["allowed_talking_points"] = ktc.get("allowed_talking_points", [])
            context["strictly_forbidden"] = ktc.get("strictly_forbidden", [])
        elif "viato" in pillar_id.lower():
            viato = companies.get("viato", {})
            context["company"] = {
                "name": viato.get("name"),
                "mission": viato.get("mission"),
                "domain": viato.get("domain"),
                "core_pillars": viato.get("core_pillars", [])
            }
            context["allowed_talking_points"] = viato.get("allowed_talking_points", [])
            context["strictly_forbidden"] = viato.get("strictly_forbidden", [])
        else:
            # General tech, AI, recruiting, productivity pillars
            context["company"] = None
            context["allowed_talking_points"] = [
                "Industry best practices and architectural trade-offs",
                "Hands-on engineering lessons and debugging methodologies",
                "Reflections on product engineering and workflow design"
            ]
            context["strictly_forbidden"] = [
                "Never invent specific revenue numbers, investments, customer logos, or imaginary testimonials"
            ]

        return context
