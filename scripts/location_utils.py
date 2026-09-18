import re
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple, Any

# Standardized Allowed Countries
DEFAULT_ALLOWED_COUNTRIES = ["US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"]

# ISO 2-letter country codes to canonical Country Name
COUNTRY_CODES_MAP = {
    "US": "United States", "USA": "United States",
    "MY": "Malaysia", "MYS": "Malaysia",
    "IN": "India", "IND": "India",
    "DE": "Germany", "DEU": "Germany",
    "PL": "Poland", "POL": "Poland",
    "CA": "Canada", "CAN": "Canada",
    "BR": "Brazil", "BRA": "Brazil",
    "SG": "Singapore", "SGP": "Singapore",
    "CN": "China", "CHN": "China",
    "HR": "Croatia", "HRV": "Croatia",
    "RS": "Serbia", "SRB": "Serbia",
    "BG": "Bulgaria", "BGR": "Bulgaria",
    "SK": "Slovakia", "SVK": "Slovakia",
    "GB": "United Kingdom", "UK": "United Kingdom", "GBR": "United Kingdom",
    "AU": "Australia", "AUS": "Australia",
    "FR": "France", "FRA": "France",
    "IE": "Ireland", "IRL": "Ireland",
    "NL": "Netherlands", "NLD": "Netherlands",
    "ES": "Spain", "ESP": "Spain",
    "JP": "Japan", "JPN": "Japan",
    "PH": "Philippines", "PHL": "Philippines",
    "MX": "Mexico", "MEX": "Mexico",
    "IL": "Israel", "ISR": "Israel",
    "RO": "Romania", "ROU": "Romania",
    "UA": "Ukraine", "UKR": "Ukraine",
    "CZ": "Czech Republic", "CZE": "Czech Republic",
    "SE": "Sweden", "SWE": "Sweden",
    "CH": "Switzerland", "CHE": "Switzerland",
    "AT": "Austria", "AUT": "Austria",
    "IT": "Italy", "ITA": "Italy",
    "NZ": "New Zealand", "NZL": "New Zealand",
    "VN": "Vietnam", "VNM": "Vietnam",
    "KR": "South Korea", "KOR": "South Korea",
    "TH": "Thailand", "THA": "Thailand",
    "ID": "Indonesia", "IDN": "Indonesia",
    "PK": "Pakistan", "PAK": "Pakistan",
    "BD": "Bangladesh", "BGD": "Bangladesh",
    "EG": "Egypt", "EGY": "Egypt",
    "NG": "Nigeria", "NGA": "Nigeria",
    "ZA": "South Africa", "ZAF": "South Africa",
    "AR": "Argentina", "ARG": "Argentina",
    "CO": "Colombia", "COL": "Colombia",
    "CL": "Chile", "CHL": "Chile",
    "CR": "Costa Rica", "CRI": "Costa Rica",
    "PT": "Portugal", "PRT": "Portugal",
    "GR": "Greece", "GRC": "Greece",
    "HU": "Hungary", "HUN": "Hungary",
    "FI": "Finland", "FIN": "Finland",
    "DK": "Denmark", "DNK": "Denmark",
    "NO": "Norway", "NOR": "Norway",
    "BE": "Belgium", "BEL": "Belgium",
    "TR": "Turkey", "TUR": "Turkey",
    "AE": "United Arab Emirates", "ARE": "United Arab Emirates"
}

# Major international cities and regions for fast keyword detection in location/title/JD
FOREIGN_LOCATIONS_MAP = {
    # Pakistan
    "pakistan": "Pakistan", "islamabad": "Pakistan", "karachi": "Pakistan", "lahore": "Pakistan", "rawalpindi": "Pakistan", "faisalabad": "Pakistan",
    # Qatar & Middle East
    "qatar": "Qatar", "doha": "Qatar",
    "united arab emirates": "United Arab Emirates", "uae": "United Arab Emirates", "dubai": "United Arab Emirates", "abu dhabi": "United Arab Emirates", "sharjah": "United Arab Emirates",
    "saudi arabia": "Saudi Arabia", "riyadh": "Saudi Arabia", "jeddah": "Saudi Arabia", "dammam": "Saudi Arabia",
    "kuwait": "Kuwait", "bahrain": "Bahrain", "manama": "Bahrain", "oman": "Oman", "muscat": "Oman",
    "jordan": "Jordan", "amman": "Jordan", "lebanon": "Lebanon", "beirut": "Lebanon",
    # Malaysia
    "kulim": "Malaysia", "penang": "Malaysia", "kuala lumpur": "Malaysia", "selangor": "Malaysia",
    "johor": "Malaysia", "malacca": "Malaysia", "sarawak": "Malaysia", "sabah": "Malaysia", "malaysia": "Malaysia",
    # India
    "hyderabad": "India", "bangalore": "India", "bengaluru": "India", "chennai": "India", "mumbai": "India",
    "pune": "India", "delhi": "India", "new delhi": "India", "noida": "India", "gurgaon": "India",
    "gurugram": "India", "kolkata": "India", "ahmedabad": "India", "india": "India", "coimbatore": "India", "kochi": "India", "trivandrum": "India",
    # Germany
    "münchen": "Germany", "munich": "Germany", "berlin": "Germany", "frankfurt": "Germany",
    "hamburg": "Germany", "stuttgart": "Germany", "cologne": "Germany", "köln": "Germany", "germany": "Germany", "deutschland": "Germany",
    # Poland
    "kraków": "Poland", "krakow": "Poland", "warsaw": "Poland", "warszawa": "Poland", "wrocław": "Poland",
    "wroclaw": "Poland", "gdańsk": "Poland", "gdansk": "Poland", "poznan": "Poland", "poznań": "Poland", "poland": "Poland", "katowice": "Poland",
    # Canada
    "montréal": "Canada", "montreal": "Canada", "toronto": "Canada", "vancouver, bc": "Canada", "vancouver, canada": "Canada",
    "ottawa": "Canada", "calgary": "Canada", "quebec": "Canada", "québec": "Canada", "ontario": "Canada", "alberta": "Canada", "canada": "Canada", "waterloo": "Canada", "edmonton": "Canada",
    # Brazil
    "são paulo": "Brazil", "sao paulo": "Brazil", "rio de janeiro": "Brazil", "curitiba": "Brazil", "brazil": "Brazil", "brasil": "Brazil", "porto alegre": "Brazil", "belo horizonte": "Brazil",
    # Singapore
    "singapore": "Singapore",
    # China & East Asia
    "beijing": "China", "shanghai": "China", "shenzhen": "China", "guangzhou": "China", "hangzhou": "China",
    "wuhan": "China", "chengdu": "China", "nanjing": "China", "china": "China", "hong kong": "China", "taiwan": "Taiwan", "taipei": "Taiwan",
    # UK
    "london": "United Kingdom", "manchester": "United Kingdom", "birmingham, uk": "United Kingdom", "edinburgh": "United Kingdom",
    "glasgow": "United Kingdom", "united kingdom": "United Kingdom", "england": "United Kingdom", "scotland": "United Kingdom", "cambridge, uk": "United Kingdom", "oxford, uk": "United Kingdom", "belfast": "United Kingdom",
    # Australia & NZ
    "sydney": "Australia", "melbourne": "Australia", "brisbane": "Australia", "perth": "Australia", "australia": "Australia",
    "new zealand": "New Zealand", "auckland": "New Zealand", "wellington": "New Zealand", "christchurch": "New Zealand",
    # France
    "paris": "France", "lyon": "France", "marseille": "France", "france": "France", "toulouse": "France", "nantes": "France",
    # Ireland
    "dublin": "Ireland", "cork": "Ireland", "ireland": "Ireland", "galway": "Ireland", "limerick": "Ireland",
    # Netherlands
    "amsterdam": "Netherlands", "rotterdam": "Netherlands", "utrecht": "Netherlands", "netherlands": "Netherlands", "eindhoven": "Netherlands", "the hague": "Netherlands",
    # Japan
    "tokyo": "Japan", "osaka": "Japan", "kyoto": "Japan", "japan": "Japan", "fukuoka": "Japan", "yokohama": "Japan",
    # Croatia & Balkans
    "croatia": "Croatia", "zagreb": "Croatia", "split": "Croatia", "hrvatska": "Croatia",
    "serbia": "Serbia", "belgrade": "Serbia", "bulgaria": "Bulgaria", "sofia": "Bulgaria",
    # South & Central America
    "mexico": "Mexico", "mexico city": "Mexico", "guadalajara": "Mexico", "monterrey": "Mexico",
    "argentina": "Argentina", "buenos aires": "Argentina", "cordoba, argentina": "Argentina",
    "colombia": "Colombia", "bogota": "Colombia", "bogotá": "Colombia", "medellin": "Colombia", "medellín": "Colombia",
    "chile": "Chile", "santiago": "Chile",
    "costa rica": "Costa Rica", "san jose, costa rica": "Costa Rica",
    "peru": "Peru", "perú": "Peru", "lima": "Peru",
    "uruguay": "Uruguay", "montevideo": "Uruguay",
    # Africa
    "egypt": "Egypt", "cairo": "Egypt", "alexandria": "Egypt",
    "nigeria": "Nigeria", "lagos": "Nigeria", "abuja": "Nigeria",
    "south africa": "South Africa", "johannesburg": "South Africa", "cape town": "South Africa", "pretoria": "South Africa", "durban": "South Africa",
    "kenya": "Kenya", "nairobi": "Kenya",
    "ghana": "Ghana", "accra": "Ghana",
    # Other Europe
    "israel": "Israel", "tel aviv": "Israel", "jerusalem": "Israel", "haifa": "Israel",
    "romania": "Romania", "bucharest": "Romania", "cluj": "Romania", "timisoara": "Romania",
    "ukraine": "Ukraine", "kyiv": "Ukraine", "lviv": "Ukraine",
    "czech republic": "Czech Republic", "czechia": "Czech Republic", "prague": "Czech Republic", "brno": "Czech Republic",
    "sweden": "Sweden", "stockholm": "Sweden", "gothenburg": "Sweden", "malmö": "Sweden", "malmo": "Sweden",
    "switzerland": "Switzerland", "zurich": "Switzerland", "geneva": "Switzerland", "lausanne": "Switzerland", "basel": "Switzerland",
    "austria": "Austria", "vienna": "Austria", "salzburg": "Austria",
    "italy": "Italy", "milan": "Italy", "rome": "Italy", "turin": "Italy",
    "spain": "Spain", "madrid": "Spain", "barcelona": "Spain", "valencia": "Spain", "seville": "Spain",
    "portugal": "Portugal", "lisbon": "Portugal", "porto": "Portugal", "braga": "Portugal",
    "belgium": "Belgium", "brussels": "Belgium", "antwerp": "Belgium", "ghent": "Belgium",
    "denmark": "Denmark", "copenhagen": "Denmark", "aarhus": "Denmark",
    "norway": "Norway", "oslo": "Norway", "bergen": "Norway",
    "finland": "Finland", "helsinki": "Finland", "tampere": "Finland", "espoo": "Finland",
    "greece": "Greece", "athens": "Greece", "thessaloniki": "Greece",
    "hungary": "Hungary", "budapest": "Hungary",
    "iceland": "Iceland", "reykjavik": "Iceland",
    "estonia": "Estonia", "tallinn": "Estonia", "tartu": "Estonia",
    "lithuania": "Lithuania", "vilnius": "Lithuania", "kaunas": "Lithuania",
    "latvia": "Latvia", "riga": "Latvia",
    "slovakia": "Slovakia", "bratislava": "Slovakia",
    "slovenia": "Slovenia", "ljubljana": "Slovenia",
    "luxembourg": "Luxembourg",
    "cyprus": "Cyprus", "nicosia": "Cyprus", "limassol": "Cyprus",
    "malta": "Malta", "valletta": "Malta",
    "turkey": "Turkey", "türkiye": "Turkey", "istanbul": "Turkey", "ankara": "Turkey", "izmir": "Turkey",
    "russia": "Russia", "moscow": "Russia", "saint petersburg": "Russia",
    # Asia
    "philippines": "Philippines", "manila": "Philippines", "cebu": "Philippines",
    "south korea": "South Korea", "korea": "South Korea", "seoul": "South Korea", "busan": "South Korea",
    "vietnam": "Vietnam", "hanoi": "Vietnam", "ho chi minh": "Vietnam", "da nang": "Vietnam",
    "thailand": "Thailand", "bangkok": "Thailand", "chiang mai": "Thailand",
    "indonesia": "Indonesia", "jakarta": "Indonesia", "bali": "Indonesia", "bandung": "Indonesia",
    "bangladesh": "Bangladesh", "dhaka": "Bangladesh",
    "sri lanka": "Sri Lanka", "colombo": "Sri Lanka",
    "nepal": "Nepal", "kathmandu": "Nepal"
}

# Canonical 50 US States + DC
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "Washington D.C."
}

# Major US Cities mapped to (StateCode, StateName)
US_MAJOR_CITIES: Dict[str, Tuple[str, str]] = {
    # Washington (Puget Sound Corridor & Major WA Cities)
    "seattle": ("WA", "Washington"),
    "bellevue": ("WA", "Washington"),
    "kirkland": ("WA", "Washington"),
    "redmond": ("WA", "Washington"),
    "renton": ("WA", "Washington"),
    "bothell": ("WA", "Washington"),
    "everett": ("WA", "Washington"),
    "issaquah": ("WA", "Washington"),
    "woodinville": ("WA", "Washington"),
    "lynnwood": ("WA", "Washington"),
    "kent": ("WA", "Washington"),
    "auburn": ("WA", "Washington"),
    "federal way": ("WA", "Washington"),
    "mercer island": ("WA", "Washington"),
    "sammamish": ("WA", "Washington"),
    "kenmore": ("WA", "Washington"),
    "edmonds": ("WA", "Washington"),
    "puyallup": ("WA", "Washington"),
    "tukwila": ("WA", "Washington"),
    "tacoma": ("WA", "Washington"),
    "olympia": ("WA", "Washington"),
    "spokane": ("WA", "Washington"),
    "bellingham": ("WA", "Washington"),
    "bremerton": ("WA", "Washington"),
    "vancouver, wa": ("WA", "Washington"),
    # California
    "san francisco": ("CA", "California"),
    "los angeles": ("CA", "California"),
    "san jose": ("CA", "California"),
    "san diego": ("CA", "California"),
    "mountain view": ("CA", "California"),
    "sunnyvale": ("CA", "California"),
    "palo alto": ("CA", "California"),
    "irvine": ("CA", "California"),
    "oakland": ("CA", "California"),
    "sacramento": ("CA", "California"),
    "menlo park": ("CA", "California"),
    "santa clara": ("CA", "California"),
    "cupertino": ("CA", "California"),
    "fremont": ("CA", "California"),
    "foster city": ("CA", "California"),
    "san mateo": ("CA", "California"),
    "redwood city": ("CA", "California"),
    # Texas
    "austin": ("TX", "Texas"),
    "dallas": ("TX", "Texas"),
    "houston": ("TX", "Texas"),
    "san antonio": ("TX", "Texas"),
    "plano": ("TX", "Texas"),
    "fort worth": ("TX", "Texas"),
    "irving": ("TX", "Texas"),
    "frisco": ("TX", "Texas"),
    "richardson": ("TX", "Texas"),
    # Oregon
    "portland": ("OR", "Oregon"),
    "eugene": ("OR", "Oregon"),
    "bend": ("OR", "Oregon"),
    "corvallis": ("OR", "Oregon"),
    "hillsboro": ("OR", "Oregon"),
    "beaverton": ("OR", "Oregon"),
    "salem": ("OR", "Oregon"),
    # New York
    "new york city": ("NY", "New York"),
    "new york": ("NY", "New York"),
    "nyc": ("NY", "New York"),
    "brooklyn": ("NY", "New York"),
    "manhattan": ("NY", "New York"),
    "albany": ("NY", "New York"),
    "buffalo": ("NY", "New York"),
    # New Jersey
    "atlantic city": ("NJ", "New Jersey"),
    "newark": ("NJ", "New Jersey"),
    "jersey city": ("NJ", "New Jersey"),
    "princeton": ("NJ", "New Jersey"),
    "hoboken": ("NJ", "New Jersey"),
    "trenton": ("NJ", "New Jersey"),
    # Indiana
    "indianapolis": ("IN", "Indiana"),
    "michigan city": ("IN", "Indiana"),
    "fort wayne": ("IN", "Indiana"),
    "bloomington": ("IN", "Indiana"),
    "south bend": ("IN", "Indiana"),
    # Kansas & Missouri
    "wichita": ("KS", "Kansas"),
    "overland park": ("KS", "Kansas"),
    "kansas city": ("MO", "Missouri"),
    "st. louis": ("MO", "Missouri"),
    "saint louis": ("MO", "Missouri"),
    # Massachusetts
    "boston": ("MA", "Massachusetts"),
    "cambridge": ("MA", "Massachusetts"),
    "waltham": ("MA", "Massachusetts"),
    # Illinois
    "chicago": ("IL", "Illinois"),
    "evanston": ("IL", "Illinois"),
    "naperville": ("IL", "Illinois"),
    # Colorado
    "denver": ("CO", "Colorado"),
    "boulder": ("CO", "Colorado"),
    "colorado springs": ("CO", "Colorado"),
    # Georgia
    "atlanta": ("GA", "Georgia"),
    "alpharetta": ("GA", "Georgia"),
    # Florida
    "miami": ("FL", "Florida"),
    "orlando": ("FL", "Florida"),
    "tampa": ("FL", "Florida"),
    "jacksonville": ("FL", "Florida"),
    "fort lauderdale": ("FL", "Florida"),
    # North Carolina
    "charlotte": ("NC", "North Carolina"),
    "raleigh": ("NC", "North Carolina"),
    "durham": ("NC", "North Carolina"),
    "cary": ("NC", "North Carolina"),
    # Arizona
    "phoenix": ("AZ", "Arizona"),
    "scottsdale": ("AZ", "Arizona"),
    "tempe": ("AZ", "Arizona"),
    "tucson": ("AZ", "Arizona"),
    "chandler": ("AZ", "Arizona"),
    # Pennsylvania
    "philadelphia": ("PA", "Pennsylvania"),
    "pittsburgh": ("PA", "Pennsylvania"),
    # Michigan
    "detroit": ("MI", "Michigan"),
    "ann arbor": ("MI", "Michigan"),
    "grand rapids": ("MI", "Michigan"),
    # Minnesota
    "minneapolis": ("MN", "Minnesota"),
    "st. paul": ("MN", "Minnesota"),
    # Utah
    "salt lake city": ("UT", "Utah"),
    "lehi": ("UT", "Utah"),
    "provo": ("UT", "Utah"),
    # Ohio
    "columbus": ("OH", "Ohio"),
    "cleveland": ("OH", "Ohio"),
    "cincinnati": ("OH", "Ohio"),
    # Tennessee
    "nashville": ("TN", "Tennessee"),
    "memphis": ("TN", "Tennessee"),
    # Virginia / Maryland / DC Area
    "mclean": ("VA", "Virginia"),
    "reston": ("VA", "Virginia"),
    "arlington": ("VA", "Virginia"),
    "alexandria": ("VA", "Virginia"),
    "richmond": ("VA", "Virginia"),
    "baltimore": ("MD", "Maryland"),
    "bethesda": ("MD", "Maryland"),
    "silver spring": ("MD", "Maryland"),
    "washington d.c.": ("DC", "Washington D.C."),
    "washington dc": ("DC", "Washington D.C.")
}

# Backward compatible dictionary of other US states and cities (excluding WA)
OTHER_US_STATES = {k: v[1] for k, v in US_MAJOR_CITIES.items() if v[0] != "WA"}
for s_code, s_name in US_STATES.items():
    if s_code != "WA":
        OTHER_US_STATES[s_code.lower()] = s_name
        OTHER_US_STATES[s_name.lower()] = s_name


def normalize_country(country_str: Optional[str]) -> Optional[str]:
    """Normalize raw country string or code to standard format."""
    if not country_str:
        return None
    raw = country_str.strip().upper()
    if raw in COUNTRY_CODES_MAP:
        return COUNTRY_CODES_MAP[raw]
    
    # Check case-insensitive match against values
    for code, name in COUNTRY_CODES_MAP.items():
        if raw == name.upper() or raw == code:
            return name
            
    return country_str.strip()


def is_allowed_country(country_str: Optional[str], allowed_countries: Optional[List[str]] = None) -> bool:
    """Check if the provided country string is within allowed countries (defaults to US only)."""
    if allowed_countries is None:
        allowed_countries = DEFAULT_ALLOWED_COUNTRIES
    
    if not country_str:
        return True  # Cannot determine strictly from country field alone
        
    c_upper = country_str.strip().upper()
    allowed_upper = [a.strip().upper() for a in allowed_countries if a]
    
    # Check direct match
    if c_upper in allowed_upper:
        return True
        
    # Check normalized name
    norm = normalize_country(country_str)
    if norm and norm.upper() in allowed_upper:
        return True
        
    # If allowed contains US/USA/United States, check synonyms
    us_synonyms = {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"}
    if any(a in us_synonyms for a in allowed_upper) and (c_upper in us_synonyms or (norm and norm.upper() in us_synonyms)):
        return True
        
    return False


def detect_foreign_country(text: str) -> Optional[Tuple[str, str]]:
    """
    Search text for foreign country or international city mentions.
    Returns (detected_term, country_name) if found, else None.
    """
    if not text:
        return None
    t_lower = f" {text.lower()} "
    
    # 1. Check international cities and regions
    for loc_key, country in FOREIGN_LOCATIONS_MAP.items():
        pattern = rf'(?:^|[\s,;/\(\)\[\]\-]){re.escape(loc_key)}(?:$|[\s,;/\(\)\[\]\-])'
        if re.search(pattern, t_lower):
            return (loc_key, country)
            
    # 2. Check canonical country names from COUNTRY_CODES_MAP
    for code, country in COUNTRY_CODES_MAP.items():
        if country.upper() not in ("UNITED STATES", "US", "USA"):
            c_low = country.lower()
            pattern = rf'(?:^|[\s,;/\(\)\[\]\-]){re.escape(c_low)}(?:$|[\s,;/\(\)\[\]\-])'
            if re.search(pattern, t_lower):
                return (c_low, country)

    return None


def detect_foreign_country_from_url(url: str) -> Optional[Tuple[str, str]]:
    """
    Detect foreign country from URL subdomain or country-code TLD.
    e.g. hr.linkedin.com -> ('hr', 'Croatia')
         ca.indeed.com -> ('ca', 'Canada')
         careers.example.de -> ('.de', 'Germany')
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
        hostname = (parsed.netloc or "").lower().strip()
        if not hostname:
            return None
            
        parts = hostname.split(".")
        if len(parts) >= 2:
            # 1. Check subdomain prefix (e.g. hr.linkedin.com, ca.indeed.com, uk.indeed.com)
            subdomain = parts[0]
            if len(subdomain) == 2 and subdomain.upper() in COUNTRY_CODES_MAP and subdomain not in ("us", "ww", "m", "go", "tv", "me", "io", "ai", "co"):
                return (subdomain, COUNTRY_CODES_MAP[subdomain.upper()])
            elif len(subdomain) == 3 and subdomain.upper() in COUNTRY_CODES_MAP and subdomain not in ("usa", "www", "app", "api", "job", "dev"):
                return (subdomain, COUNTRY_CODES_MAP[subdomain.upper()])

            # 2. Check ccTLD suffix (e.g. .de, .pl, .ca, .hr, .my, .in)
            tld = parts[-1]
            if len(tld) == 2 and tld.upper() in COUNTRY_CODES_MAP and tld not in ("us", "io", "ai", "co", "tv", "me", "to", "so"):
                return (f".{tld}", COUNTRY_CODES_MAP[tld.upper()])
    except Exception:
        pass
    return None


def is_redmond_oregon(text: str) -> bool:
    """Check specifically if text refers to Redmond, Oregon (OR) rather than Redmond, Washington (WA)."""
    if not text:
        return False
    t_lower = text.lower()
    if "redmond" not in t_lower:
        return False
        
    or_patterns = [
        r'\bredmond\s*,\s*or\b',
        r'\bredmond\s*,\s*oregon\b',
        r'\bredmond\s+or\b',
        r'\bredmond\s+oregon\b',
        r'\bor\s*,\s*redmond\b',
        r'\boregon\s*,\s*redmond\b',
    ]
    return any(re.search(p, t_lower) for p in or_patterns)


def is_washington_location(text: str) -> bool:
    """Check if location explicitly specifies Washington State (excluding Redmond, OR)."""
    if not text:
        return False
    t_lower = text.lower()
    
    if is_redmond_oregon(t_lower):
        return False
        
    wa_keywords = [
        r'\bseattle\b',
        r'\bbellevue\b',
        r'\bkirkland\b',
        r'\brenton\b',
        r'\bbothell\b',
        r'\bissaquah\b',
        r'\bwoodinville\b',
        r'\blynnwood\b',
        r'\bkent\b',
        r'\bauburn\b',
        r'\bfederal\s+way\b',
        r'\bmercer\s+island\b',
        r'\bsammamish\b',
        r'\bkenmore\b',
        r'\bedmonds\b',
        r'\bpuyallup\b',
        r'\btukwila\b',
        r'\beverett\b',
        r'\btacoma\b',
        r'\bolympia\b',
        r'\bspokane\b',
        r'\bbellingham\b',
        r'\bbremerton\b',
        r'\bpuget\s+sound\b',
        r'\bredmond\s*,\s*wa\b',
        r'\bredmond\s*,\s*washington\b',
        r'\bredmond\b',
        r'\bwashington\s+state\b',
        r'(?:^|[\s,])wa(?:$|[\s,\.])',
        r'(?:^|[\s,])washington(?:$|[\s,\.])'
    ]
    
    if "washington d.c" in t_lower or "washington dc" in t_lower or "district of columbia" in t_lower:
        return False
        
    return any(re.search(p, t_lower) for p in wa_keywords)


def detect_us_state(text: str) -> Optional[str]:
    """
    Identify US state name from text (e.g. 'Austin, TX' -> 'Texas', 'Redmond, OR' -> 'Oregon').
    Returns canonical state name or None.
    """
    if not text:
        return None
    t_lower = text.lower()
    
    if is_redmond_oregon(t_lower):
        return "Oregon"
        
    if "washington d.c" in t_lower or "washington dc" in t_lower or "district of columbia" in t_lower:
        return "Washington D.C."
        
    # Check major cities first (more specific)
    for city, (code, state_name) in US_MAJOR_CITIES.items():
        if re.search(rf'\b{re.escape(city)}\b', t_lower):
            return state_name
            
    # Check full state names
    for code, name in US_STATES.items():
        if name.lower() == "washington":
            if re.search(r'\bwashington\s+state\b', t_lower) or re.search(r'(?:^|[\s,])washington(?:$|[\s,\.])', t_lower):
                return "Washington"
        else:
            if re.search(rf'\b{re.escape(name.lower())}\b', t_lower):
                return name
                
    # Check 2-letter state codes with delimiter/boundary
    for code, name in US_STATES.items():
        pattern = rf'(?:,\s*|\b|[\s/\[\(]){re.escape(code)}(?:$|[\s,\.\]\)\-\d])'
        if re.search(pattern, text):
            return name
            
    return None


def is_target_location(
    text: str,
    target_states: Optional[List[str]] = None,
    preferred_cities: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check if text matches user's target states or preferred cities dynamically.
    Handles state disambiguation (e.g. Redmond, OR vs Redmond, WA).
    Returns (is_target, matched_entity).
    """
    if not text:
        return (False, None)
        
    if target_states is None:
        target_states = ["WA", "Washington"]
    if preferred_cities is None:
        preferred_cities = ["Seattle", "Redmond", "Bellevue", "Kirkland", "Bothell", "Issaquah"]
        
    t_lower = text.lower()
    
    # Normalize target states to sets of codes and uppercase names
    normalized_codes = set()
    normalized_names = set()
    for s in target_states:
        s_clean = s.strip()
        s_upper = s_clean.upper()
        if s_upper in US_STATES:
            normalized_codes.add(s_upper)
            normalized_names.add(US_STATES[s_upper].upper())
        else:
            for code, name in US_STATES.items():
                if s_upper == name.upper():
                    normalized_codes.add(code)
                    normalized_names.add(name.upper())
                    break
            else:
                normalized_names.add(s_upper)

    # 1. Check preferred cities
    for city in preferred_cities:
        c_clean = city.strip().lower()
        if not c_clean:
            continue
        if c_clean == "redmond":
            if is_redmond_oregon(t_lower):
                if "OR" in normalized_codes or "OREGON" in normalized_names:
                    return (True, "Redmond, OR")
                else:
                    continue  # Redmond OR does not match non-OR target
            else:
                if re.search(r'\bredmond\b', t_lower):
                    return (True, "Redmond")
        else:
            if re.search(rf'\b{re.escape(c_clean)}\b', t_lower):
                return (True, city)

    # 2. Check target state names
    for name in normalized_names:
        if name == "WASHINGTON":
            if is_washington_location(t_lower):
                return (True, "Washington")
        elif name in ("WASHINGTON D.C.", "WASHINGTON DC", "DISTRICT OF COLUMBIA"):
            if "washington d.c" in t_lower or "washington dc" in t_lower or "district of columbia" in t_lower:
                return (True, "Washington D.C.")
        else:
            if re.search(rf'\b{re.escape(name.lower())}\b', t_lower):
                return (True, name.title())

    # 3. Check target state codes
    for code in normalized_codes:
        if code == "WA":
            if is_washington_location(t_lower):
                return (True, "WA")
        else:
            pattern = rf'(?:,\s*|\b|[\s/\[\(]){re.escape(code)}(?:$|[\s,\.\]\)\-\d])'
            if re.search(pattern, text):
                return (True, code)

    return (False, None)


def is_remote_role(text: str) -> Tuple[bool, bool]:
    """
    Detects if a role is remote, and whether it is US-wide / anywhere remote.
    Returns (is_remote, is_us_remote).
    Uses strict remote phrases to prevent false positives on 'virtual casino', 'nationwide discount', etc.
    """
    if not text:
        return (False, False)
        
    t_lower = text.lower()
    remote_patterns = [
        r'\b(?:100%|fully|strictly|optional)?\s*remote\b',
        r'\bwork\s+from\s+home\b',
        r'\bwfh\b',
        r'\btelecommute\b',
        r'\btelecommuting\b',
        r'\bvirtual\s+(?:role|position|opportunity|employment|opening|work|job|status)\b',
        r'\bwork\s+from\s+anywhere\b',
        r'\bremote\s+(?:eligible|first|option|friendly|work|position|role|job|status)\b',
        r'\bposition\s+is\s+remote\b',
        r'\brole\s+is\s+remote\b'
    ]
    
    is_remote = any(re.search(p, t_lower) for p in remote_patterns)
    if not is_remote:
        return (False, False)
        
    # Check if restricted to non-US remote (e.g. "Remote, Qatar", "Remote - India")
    foreign = detect_foreign_country(text)
    if foreign:
        foreign_term, _ = foreign
        has_us_indication = bool(re.search(r'\b(us|usa|united states|nationwide|national|us only|within the us|in the us|us remote|remote - us|remote \(us\))\b', t_lower))
        if not has_us_indication:
            return (True, False)
            
    is_us_remote = bool(re.search(r'\b(us|usa|united states|nationwide|national|anywhere in the us|anywhere in us|us remote|remote - us|remote \(us\)|remote, us|remote, usa)\b', t_lower))
    if not foreign and not is_us_remote:
        is_us_remote = True
        
    return (True, is_us_remote)


def evaluate_job_location(
    location: str = "",
    country: str = "",
    title: str = "",
    jd_text: str = "",
    company: str = "",
    url: str = "",
    profile_location: Optional[Dict[str, Any]] = None,
    allowed_countries: Optional[List[str]] = None,
    require_local_or_remote: Optional[bool] = None,
    require_wa_or_remote: Optional[bool] = None,
    target_states: Optional[List[str]] = None,
    preferred_cities: Optional[List[str]] = None,
    allow_remote: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Comprehensive dynamic location evaluation for TalentScout.
    Evaluates country code, location text, title, company, url, and job description against the active profile.
    """
    # Extract from profile_location dict if supplied
    if profile_location:
        if allowed_countries is None:
            allowed_countries = profile_location.get("allowed_countries")
        if target_states is None:
            target_states = profile_location.get("target_states") or profile_location.get("preferred_locations")
        if preferred_cities is None:
            preferred_cities = profile_location.get("preferred_cities") or profile_location.get("preferred_locations")
        if allow_remote is None:
            allow_remote = profile_location.get("allow_remote", True)
        if require_local_or_remote is None:
            require_local_or_remote = profile_location.get("require_local_or_remote", profile_location.get("require_wa_or_remote"))

    # Fallback defaults
    if allowed_countries is None:
        allowed_countries = DEFAULT_ALLOWED_COUNTRIES
    if target_states is None:
        target_states = ["WA", "Washington"]
    if preferred_cities is None:
        preferred_cities = ["Seattle", "Redmond", "Bellevue", "Kirkland", "Bothell", "Issaquah"]
    if allow_remote is None:
        allow_remote = True
    if require_local_or_remote is None:
        require_local_or_remote = require_wa_or_remote if require_wa_or_remote is not None else True

    loc_clean = (location or "").strip()
    country_clean = (country or "").strip()
    title_clean = (title or "").strip()
    company_clean = (company or "").strip()
    url_clean = (url or "").strip()
    jd_clean = (jd_text or "").strip()
    
    norm_country = normalize_country(country_clean) if country_clean else None
    
    # 0a. Check Foreign Country in URL Domain / Subdomain
    if url_clean:
        url_foreign = detect_foreign_country_from_url(url_clean)
        if url_foreign:
            term, cname = url_foreign
            if not is_allowed_country(cname, allowed_countries):
                return {
                    "is_disqualified": True,
                    "reason": f"Non-US URL Domain: {term} ({cname})",
                    "detected_country": cname,
                    "detected_state": None,
                    "is_remote": False,
                    "is_target": False,
                    "is_wa": False,
                    "is_us": False
                }

    # 0b. Check Foreign Country in Company Name
    if company_clean:
        comp_foreign = detect_foreign_country(company_clean)
        if comp_foreign:
            term, cname = comp_foreign
            if not is_allowed_country(cname, allowed_countries):
                return {
                    "is_disqualified": True,
                    "reason": f"Non-US Company: {company_clean} ({cname})",
                    "detected_country": cname,
                    "detected_state": None,
                    "is_remote": False,
                    "is_target": False,
                    "is_wa": False,
                    "is_us": False
                }

    # 1. Explicit Country Field Disqualification
    if country_clean and not is_allowed_country(country_clean, allowed_countries):
        return {
            "is_disqualified": True,
            "reason": f"Non-US Country: {norm_country or country_clean}",
            "detected_country": norm_country or country_clean,
            "detected_state": None,
            "is_remote": False,
            "is_target": False,
            "is_wa": False,
            "is_us": False
        }
        
    # 2. Check for Foreign Country in Location Header or Title
    foreign_loc = detect_foreign_country(loc_clean) or detect_foreign_country(title_clean)
    if foreign_loc:
        term, cname = foreign_loc
        if not is_allowed_country(cname, allowed_countries):
            return {
                "is_disqualified": True,
                "reason": f"Non-US Location: {term.title()} ({cname})",
                "detected_country": cname,
                "detected_state": None,
                "is_remote": False,
                "is_target": False,
                "is_wa": False,
                "is_us": False
            }
        
    # 3. Foreign Country in Job Description text
    if jd_clean:
        foreign_jd = detect_foreign_country(jd_clean)
        if foreign_jd:
            term, cname = foreign_jd
            if not is_allowed_country(cname, allowed_countries):
                # Disqualify unless the job description explicitly verifies a Washington location
                jd_is_wa = is_washington_location(jd_clean[:1500])
                if not jd_is_wa:
                    return {
                        "is_disqualified": True,
                        "reason": f"Non-US Location in JD: {term.title()} ({cname})",
                        "detected_country": cname,
                        "detected_state": None,
                        "is_remote": False,
                        "is_target": False,
                        "is_wa": False,
                        "is_us": False
                    }

    target_st_normalized = set()
    for s in target_states:
        s_clean = s.strip().upper()
        if s_clean in US_STATES:
            target_st_normalized.add(US_STATES[s_clean])
        else:
            target_st_normalized.add(s.strip().title())

    target_display = target_states[0] if target_states else "WA"

    # 4. Out-of-State in Title (Title has highest specificity for designated location)
    title_st = detect_us_state(title_clean)
    if title_st and title_st not in target_st_normalized:
        if not is_remote_role(title_clean)[0]:
            return {
                "is_disqualified": True,
                "reason": f"SafetyNet: Not remote and not in {target_display} ({title_st})",
                "detected_country": "United States",
                "detected_state": title_st,
                "is_remote": False,
                "is_target": False,
                "is_wa": False,
                "is_us": True
            }

    # 5. Out-of-State in Location Header
    header_st = detect_us_state(loc_clean)
    is_header_target_state = bool(header_st and header_st in target_st_normalized)
    is_header_remote = is_remote_role(loc_clean)[0] or is_remote_role(title_clean)[0]
    is_target_loc_h, _ = is_target_location(loc_clean, target_states, preferred_cities)

    if header_st and not is_header_target_state and not is_header_remote:
        return {
            "is_disqualified": True,
            "reason": f"SafetyNet: Not remote and not in {target_display} ({header_st})",
            "detected_country": "United States",
            "detected_state": header_st,
            "is_remote": False,
            "is_target": False,
            "is_wa": False,
            "is_us": True
        }

    # Non-target specific location header (e.g. 'Wichita Metro Area')
    if loc_clean and not is_target_loc_h and not is_header_remote:
        if not is_remote_role(title_clean)[0]:
            loc_st_detect = detect_us_state(loc_clean)
            st_label = loc_st_detect or loc_clean
            return {
                "is_disqualified": True,
                "reason": f"SafetyNet: Not remote and not in {target_display} ({st_label})",
                "detected_country": "United States",
                "detected_state": loc_st_detect,
                "is_remote": False,
                "is_target": False,
                "is_wa": False,
                "is_us": True
            }

    # 6. Out-of-State in Job Description
    jd_st = detect_us_state(jd_clean[:1200]) if jd_clean else None
    jd_is_target, _ = is_target_location(jd_clean[:1200], target_states, preferred_cities)

    if jd_st and jd_st not in target_st_normalized and not jd_is_target and not is_header_remote:
        return {
            "is_disqualified": True,
            "reason": f"SafetyNet: Not remote and not in {target_display} ({jd_st})",
            "detected_country": "United States",
            "detected_state": jd_st,
            "is_remote": False,
            "is_target": False,
            "is_wa": False,
            "is_us": True
        }

    # 7. Hybrid in Distant Location
    if ("hybrid" in loc_clean.lower() or (jd_clean and "hybrid" in jd_clean[:600].lower())) and not is_target_loc_h and not jd_is_target:
        loc_label = header_st or jd_st or loc_clean or f"Non-{target_display}"
        return {
            "is_disqualified": True,
            "reason": f"SafetyNet: Hybrid in non-target location ({loc_label})",
            "detected_country": norm_country or "United States",
            "detected_state": header_st or jd_st,
            "is_remote": False,
            "is_target": False,
            "is_wa": False,
            "is_us": True
        }

    # Remote detection
    is_rem, is_us_rem = is_remote_role(f"{loc_clean} {title_clean} {jd_clean}")
    if not is_header_remote and loc_clean and not is_target_loc_h:
        is_rem = False
        is_us_rem = False

    # Target location match
    is_target_loc_t, _ = is_target_location(title_clean, target_states, preferred_cities)
    is_target_loc = is_target_loc_h or is_target_loc_t or (jd_is_target and (header_st is None or is_header_target_state))
    is_wa = is_washington_location(loc_clean) or is_washington_location(title_clean) or (is_washington_location(jd_clean[:1200]) and (header_st is None or is_header_target_state))
    detected_st = header_st or jd_st or title_st

    # 8. Local / Target State Requirement Check
    if require_local_or_remote:
        if not is_target_loc and not (allow_remote and is_rem and is_us_rem):
            loc_label = loc_clean or detected_st or "Unspecified"
            return {
                "is_disqualified": True,
                "reason": f"SafetyNet: Not remote and not confirmed in {target_display} ({loc_label})",
                "detected_country": norm_country or ("United States" if (detected_st or is_rem) else "Unknown"),
                "detected_state": detected_st,
                "is_remote": is_rem,
                "is_target": False,
                "is_wa": False,
                "is_us": True if (norm_country == "United States" or detected_st or is_rem) else False
            }

    return {
        "is_disqualified": False,
        "reason": None,
        "detected_country": norm_country or ("United States" if (is_target_loc or is_wa or detected_st or (is_rem and is_us_rem)) else "United States"),
        "detected_state": detected_st,
        "is_remote": is_rem,
        "is_us_remote": is_us_rem,
        "is_target": is_target_loc,
        "is_wa": is_wa,
        "is_us": True
    }
