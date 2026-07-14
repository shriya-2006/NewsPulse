"""
Predefined industry tags for the search bar. Newspaper/edition data used
to live here too as a static dict — it's now in the database instead
(see app/models/newspaper.py, app/services/newspaper_service.py), so a
new newspaper or edition can be added with a row insert instead of a
code change.
"""


# Predefined industry tags shown in the Dashboard search bar. Editable
# here without a migration since they're reference data, not user data
# (custom, per-user tags live in the `custom_tags` table instead).
#
# Telugu/Hindi tags are machine-assisted translations of the same 23
# English industry terms, not verified by a native speaker — treat as a
# reasonable starting point and correct any that read oddly to a fluent
# reader before relying on them for a real deployment.
PREDEFINED_TAGS_BY_LANGUAGE: dict[str, list[str]] = {
    "en": [
        "Steel", "Steel Plant", "RINL", "Iron Ore", "Coal", "Blast Furnace",
        "Manufacturing", "Mining", "Mines", "Steel Export", "Steel Import",
        "Tax", "Government Policy", "Tender", "Railways", "Port",
        "Industrial Safety", "Accident", "Power Plant", "Raw Material",
        "Supply Chain", "Employee Welfare", "Production",
    ],
    "te": [
        "ఉక్కు", "ఉక్కు కర్మాగారం", "RINL", "ఇనుప ఖనిజం", "బొగ్గు", "బ్లాస్ట్ ఫర్నేస్",
        "తయారీ", "మైనింగ్", "గనులు", "ఉక్కు ఎగుమతి", "ఉక్కు దిగుమతి",
        "పన్ను", "ప్రభుత్వ విధానం", "టెండర్", "రైల్వేలు", "ఓడరేవు",
        "పారిశ్రామిక భద్రత", "ప్రమాదం", "విద్యుత్ కేంద్రం", "ముడి పదార్థం",
        "సరఫరా గొలుసు", "ఉద్యోగుల సంక్షేమం", "ఉత్పత్తి",
    ],
    "hi": [
        "इस्पात", "इस्पात संयंत्र", "RINL", "लौह अयस्क", "कोयला", "ब्लास्ट फर्नेस",
        "विनिर्माण", "खनन", "खदानें", "इस्पात निर्यात", "इस्पात आयात",
        "कर", "सरकारी नीति", "निविदा", "रेलवे", "बंदरगाह",
        "औद्योगिक सुरक्षा", "दुर्घटना", "बिजली संयंत्र", "कच्चा माल",
        "आपूर्ति श्रृंखला", "कर्मचारी कल्याण", "उत्पादन",
    ],
}


def get_predefined_tags(language: str) -> list[str]:
    return PREDEFINED_TAGS_BY_LANGUAGE.get(language, PREDEFINED_TAGS_BY_LANGUAGE["en"])


def all_predefined_tags() -> list[str]:
    """Flattened across every language — used only to block a custom tag
    that duplicates ANY language's predefined list, not just the current one."""
    return [tag for tags in PREDEFINED_TAGS_BY_LANGUAGE.values() for tag in tags]
