"""
Seed data for the `newspapers` / `newspaper_editions` tables.

This module is intentionally the ONLY place this data is written down —
it's read once, at startup, to populate an empty database (see
`app.services.newspaper_service.seed_if_empty`). After that, this file
is never consulted again: every request is served straight from the
database, and adding a new newspaper or edition going forward means
inserting rows (via SQL, an admin tool, etc.), never editing this file
or any frontend code.

Edition lists for The Hindu, Times of India, Eenadu, Sakshi, and Dainik
Jagran are exact deployment requirements. The remaining newspapers'
edition lists are a reasonable real-world approximation, not verified
against each publication's actual current edition list — safe to
correct via a simple UPDATE/INSERT once you know the real ones you want.
"""

NEWSPAPER_SEED_DATA = [
    # --- English ---
    {
        "key": "the_hindu",
        "label": "The Hindu",
        "language": "en",
        "domain": "thehindu.com",
        "edition_query_supported": False,
        "editions": ["Visakhapatnam", "Hyderabad", "Chennai", "Bengaluru", "Delhi"],
    },
    {
        "key": "times_of_india",
        "label": "The Times of India",
        "language": "en",
        "domain": "timesofindia.indiatimes.com",
        "edition_query_supported": False,
        "editions": ["Hyderabad", "Mumbai", "Delhi", "Chennai", "Bengaluru", "Visakhapatnam"],
    },
    {
        "key": "indian_express",
        "label": "The Indian Express",
        "language": "en",
        "domain": "indianexpress.com",
        "edition_query_supported": False,
        "editions": ["Delhi", "Mumbai", "Chennai", "Bengaluru", "Hyderabad", "Kochi"],
    },
    {
        "key": "business_standard",
        "label": "Business Standard",
        "language": "en",
        "domain": "business-standard.com",
        "edition_query_supported": False,
        "editions": [
            "Delhi", "Mumbai", "Kolkata", "Chennai", "Ahmedabad",
            "Hyderabad", "Bengaluru", "Chandigarh", "Pune",
        ],
    },
    {
        "key": "economic_times",
        "label": "The Economic Times",
        "language": "en",
        "domain": "economictimes.indiatimes.com",
        "edition_query_supported": False,
        "editions": [
            "Delhi", "Mumbai", "Kolkata", "Chennai", "Bengaluru",
            "Hyderabad", "Pune", "Ahmedabad", "Chandigarh",
        ],
    },
    # --- Telugu ---
    {
        "key": "eenadu",
        "label": "Eenadu",
        "language": "te",
        "domain": "eenadu.net",
        "edition_query_supported": False,
        "editions": [
            "Visakhapatnam", "Gajuwaka", "Ukkunagaram", "Anakapalle",
            "Vizianagaram", "Srikakulam", "Vijayawada", "Hyderabad",
        ],
    },
    {
        "key": "sakshi",
        "label": "Sakshi",
        "language": "te",
        "domain": "sakshi.com",
        "edition_query_supported": False,
        "editions": ["Visakhapatnam", "Hyderabad", "Vijayawada", "Tirupati", "Kurnool"],
    },
    {
        "key": "andhra_jyothy",
        "label": "Andhra Jyothy",
        "language": "te",
        "domain": "andhrajyothy.com",
        "edition_query_supported": False,
        "editions": ["Visakhapatnam", "Vijayawada", "Hyderabad", "Guntur", "Rajahmundry"],
    },
    {
        "key": "namasthe_telangana",
        "label": "Namasthe Telangana",
        "language": "te",
        "domain": "ntnews.com",
        "edition_query_supported": False,
        "editions": ["Hyderabad", "Warangal", "Karimnagar", "Nizamabad", "Khammam"],
    },
    # --- Hindi ---
    {
        "key": "dainik_jagran",
        "label": "Dainik Jagran",
        "language": "hi",
        "domain": "jagran.com",
        "edition_query_supported": False,
        "editions": ["Delhi", "Lucknow", "Kanpur", "Patna", "Varanasi"],
    },
    {
        "key": "amar_ujala",
        "label": "Amar Ujala",
        "language": "hi",
        "domain": "amarujala.com",
        "edition_query_supported": False,
        "editions": ["Delhi", "Lucknow", "Dehradun", "Agra", "Meerut"],
    },
    {
        "key": "hindustan",
        "label": "Hindustan",
        "language": "hi",
        "domain": "livehindustan.com",
        "edition_query_supported": False,
        "editions": ["Delhi", "Patna", "Lucknow", "Ranchi", "Varanasi"],
    },
]

LANGUAGE_SEED_DATA = [
    {"code": "en", "label": "English"},
    {"code": "te", "label": "Telugu"},
    {"code": "hi", "label": "Hindi"},
]
