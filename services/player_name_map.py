"""
Player Name Mapping

Maps player names from the Odds API to their official NBA API names.
This handles variations like:
- Missing suffixes (Jr., III, II)
- Accent marks (é, ć, etc.)
- Nicknames vs legal names

To add new mappings:
1. Run: python scripts/find_player_mismatches.py
2. Add the suggested mappings below
3. Restart the data collection

The normalize_player_name() function is used in collect_today.py
to ensure props match correctly with NBA players.
"""

# Odds API name -> NBA API official name
PLAYER_NAME_MAP = {
    # Suffix variations
    'Jimmy Butler': 'Jimmy Butler III',
    'Gary Trent': 'Gary Trent Jr.',
    'Michael Porter': 'Michael Porter Jr.',
    'Kelly Oubre': 'Kelly Oubre Jr.',
    'Jaren Jackson': 'Jaren Jackson Jr.',
    'Larry Nance': 'Larry Nance Jr.',
    'Tim Hardaway': 'Tim Hardaway Jr.',
    'Wendell Carter': 'Wendell Carter Jr.',
    'Kevin Porter': 'Kevin Porter Jr.',
    'Marcus Morris': 'Marcus Morris Sr.',
    'Dennis Smith': 'Dennis Smith Jr.',
    'Derrick Walton': 'Derrick Walton Jr.',
    'Troy Brown': 'Troy Brown Jr.',
    'Otto Porter': 'Otto Porter Jr.',
    'Kenyon Martin': 'Kenyon Martin Jr.',
    'Gary Payton': 'Gary Payton II',
    'Scottie Pippen': 'Scottie Pippen Jr.',
    'Walker Kessler': 'Walker Kessler',

    # Accent marks
    'Moussa Diabate': 'Moussa Diabaté',
    'Nikola Jokic': 'Nikola Jokić',
    'Luka Doncic': 'Luka Dončić',
    'Bojan Bogdanovic': 'Bojan Bogdanović',
    'Bogdan Bogdanovic': 'Bogdan Bogdanović',
    'Jusuf Nurkic': 'Jusuf Nurkić',
    'Dario Saric': 'Dario Šarić',
    'Jonas Valanciunas': 'Jonas Valančiūnas',
    'Kristaps Porzingis': 'Kristaps Porziņģis',
    'Goran Dragic': 'Goran Dragić',
    'Vlatko Cancar': 'Vlatko Čančar',
    'Aleksej Pokusevski': 'Aleksej Pokuševski',
    'Vasilije Micic': 'Vasilije Micić',
    'Nikola Vucevic': 'Nikola Vučević',
    'Svi Mykhailiuk': 'Sviatoslav Mykhailiuk',
    'Alperen Sengun': 'Alperen Şengün',

    # Nickname vs legal name variations
    'Nic Claxton': 'Nicolas Claxton',
    'Herb Jones': 'Herbert Jones',
    'PJ Washington': 'P.J. Washington',
    'OG Anunoby': 'O.G. Anunoby',
    'RJ Barrett': 'R.J. Barrett',
    'TJ McConnell': 'T.J. McConnell',
    'CJ McCollum': 'C.J. McCollum',
    'JT Thor': 'J.T. Thor',
    'AJ Griffin': 'A.J. Griffin',
    'KJ Martin': 'K.J. Martin',
    'Trey Murphy': 'Trey Murphy III',

    # Other variations
    'Moe Wagner': 'Moritz Wagner',
    'Ish Wainright': 'Ishmail Wainright',
    'Naz Reid': 'Naz Reid',
    'Lu Dort': 'Luguentz Dort',
}

# Build reverse map for lookups
_REVERSE_MAP = {v.lower(): v for v in PLAYER_NAME_MAP.values()}


def normalize_player_name(name: str) -> str:
    """
    Normalize a player name from Odds API to match NBA API format.

    Args:
        name: Player name from Odds API

    Returns:
        Normalized name that matches NBA API, or original if no mapping exists
    """
    if not name:
        return name

    # Check direct mapping first
    if name in PLAYER_NAME_MAP:
        return PLAYER_NAME_MAP[name]

    # Check case-insensitive
    name_lower = name.lower()
    for odds_name, nba_name in PLAYER_NAME_MAP.items():
        if odds_name.lower() == name_lower:
            return nba_name

    # No mapping needed
    return name


def add_mapping(odds_name: str, nba_name: str):
    """
    Add a new mapping at runtime (useful for testing).
    For permanent mappings, add them to PLAYER_NAME_MAP above.
    """
    PLAYER_NAME_MAP[odds_name] = nba_name


def get_all_mappings() -> dict:
    """Return all current mappings"""
    return PLAYER_NAME_MAP.copy()
