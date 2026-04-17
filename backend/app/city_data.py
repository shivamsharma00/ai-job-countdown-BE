"""Static city groupings for city suggestions without LLM."""

# Maps a lowercase city name → 6 cities in the same metro/region.
# The matched city is typically first in the list.
CITY_GROUPS: dict[str, list[str]] = {
    # US West Coast
    "san francisco": ["San Francisco", "Oakland", "San Jose", "Berkeley", "Palo Alto", "Fremont"],
    "oakland": ["Oakland", "San Francisco", "Berkeley", "San Jose", "Fremont", "Hayward"],
    "san jose": ["San Jose", "Santa Clara", "Sunnyvale", "Mountain View", "Palo Alto", "Cupertino"],
    "palo alto": ["Palo Alto", "San Jose", "Mountain View", "Sunnyvale", "Redwood City", "San Francisco"],
    "los angeles": ["Los Angeles", "Long Beach", "Santa Monica", "Pasadena", "Glendale", "Burbank"],
    "santa monica": ["Santa Monica", "Los Angeles", "Culver City", "Manhattan Beach", "Venice", "Burbank"],
    "seattle": ["Seattle", "Bellevue", "Redmond", "Kirkland", "Tacoma", "Renton"],
    "bellevue": ["Bellevue", "Seattle", "Redmond", "Kirkland", "Renton", "Issaquah"],
    "portland": ["Portland", "Beaverton", "Gresham", "Hillsboro", "Lake Oswego", "Vancouver"],
    "san diego": ["San Diego", "Chula Vista", "El Cajon", "Escondido", "Oceanside", "Carlsbad"],
    "las vegas": ["Las Vegas", "Henderson", "North Las Vegas", "Summerlin", "Boulder City", "Reno"],
    "sacramento": ["Sacramento", "Elk Grove", "Roseville", "Folsom", "Stockton", "Modesto"],
    # US Mountain
    "denver": ["Denver", "Aurora", "Lakewood", "Boulder", "Fort Collins", "Colorado Springs"],
    "boulder": ["Boulder", "Denver", "Fort Collins", "Broomfield", "Westminster", "Longmont"],
    "salt lake city": ["Salt Lake City", "Provo", "Orem", "Sandy", "West Valley City", "Ogden"],
    "phoenix": ["Phoenix", "Scottsdale", "Tempe", "Mesa", "Chandler", "Glendale"],
    "scottsdale": ["Scottsdale", "Phoenix", "Tempe", "Mesa", "Gilbert", "Chandler"],
    "albuquerque": ["Albuquerque", "Santa Fe", "Rio Rancho", "Roswell", "Las Cruces", "Taos"],
    # US Midwest
    "chicago": ["Chicago", "Evanston", "Oak Park", "Naperville", "Aurora", "Schaumburg"],
    "detroit": ["Detroit", "Dearborn", "Ann Arbor", "Livonia", "Sterling Heights", "Warren"],
    "ann arbor": ["Ann Arbor", "Detroit", "Ypsilanti", "Dearborn", "Livonia", "Lansing"],
    "minneapolis": ["Minneapolis", "Saint Paul", "Bloomington", "Plymouth", "Edina", "Eden Prairie"],
    "columbus": ["Columbus", "Dublin", "Westerville", "Hilliard", "Grove City", "Newark"],
    "indianapolis": ["Indianapolis", "Carmel", "Fishers", "Westfield", "Greenwood", "Noblesville"],
    "kansas city": ["Kansas City", "Overland Park", "Lenexa", "Olathe", "Independence", "Lee's Summit"],
    "st. louis": ["St. Louis", "Clayton", "Chesterfield", "Florissant", "O'Fallon", "Belleville"],
    "cincinnati": ["Cincinnati", "Lexington", "Dayton", "Covington", "Florence", "Mason"],
    "cleveland": ["Cleveland", "Akron", "Parma", "Lakewood", "Lorain", "Elyria"],
    "milwaukee": ["Milwaukee", "Madison", "Waukesha", "Racine", "Kenosha", "Green Bay"],
    # US East Coast
    "new york": ["New York", "Brooklyn", "Jersey City", "Newark", "Hoboken", "Yonkers"],
    "brooklyn": ["Brooklyn", "New York", "Queens", "Jersey City", "Hoboken", "Newark"],
    "manhattan": ["Manhattan", "Brooklyn", "Jersey City", "Hoboken", "Queens", "Newark"],
    "boston": ["Boston", "Cambridge", "Somerville", "Quincy", "Newton", "Waltham"],
    "cambridge": ["Cambridge", "Boston", "Somerville", "Medford", "Waltham", "Newton"],
    "washington": ["Washington", "Arlington", "Alexandria", "Bethesda", "Silver Spring", "Rockville"],
    "washington dc": ["Washington", "Arlington", "Alexandria", "Bethesda", "Silver Spring", "Rockville"],
    "arlington": ["Arlington", "Washington", "Alexandria", "Rosslyn", "Falls Church", "Bethesda"],
    "philadelphia": ["Philadelphia", "Camden", "Cherry Hill", "Wilmington", "Norristown", "Chester"],
    "miami": ["Miami", "Fort Lauderdale", "Coral Gables", "Hialeah", "West Palm Beach", "Boca Raton"],
    "fort lauderdale": ["Fort Lauderdale", "Miami", "Hollywood", "Boca Raton", "Pompano Beach", "West Palm Beach"],
    "atlanta": ["Atlanta", "Decatur", "Sandy Springs", "Alpharetta", "Marietta", "Roswell"],
    "charlotte": ["Charlotte", "Concord", "Gastonia", "Rock Hill", "Huntersville", "Matthews"],
    "raleigh": ["Raleigh", "Durham", "Chapel Hill", "Cary", "Research Triangle Park", "Apex"],
    "durham": ["Durham", "Raleigh", "Chapel Hill", "Cary", "Morrisville", "Research Triangle Park"],
    "nashville": ["Nashville", "Brentwood", "Franklin", "Murfreesboro", "Hendersonville", "Smyrna"],
    "austin": ["Austin", "Round Rock", "Cedar Park", "Georgetown", "San Marcos", "Kyle"],
    "dallas": ["Dallas", "Fort Worth", "Plano", "Irving", "Arlington", "Frisco"],
    "fort worth": ["Fort Worth", "Dallas", "Arlington", "Plano", "Irving", "Grand Prairie"],
    "houston": ["Houston", "Sugar Land", "Pearland", "The Woodlands", "Pasadena", "Baytown"],
    "tampa": ["Tampa", "St. Petersburg", "Clearwater", "Brandon", "Sarasota", "Wesley Chapel"],
    "orlando": ["Orlando", "Kissimmee", "Sanford", "Lake Mary", "Altamonte Springs", "Maitland"],
    "jacksonville": ["Jacksonville", "Orlando", "Gainesville", "St. Augustine", "Palm Coast", "Daytona Beach"],
    "pittsburgh": ["Pittsburgh", "Bethel Park", "Monroeville", "McKeesport", "New Kensington", "Greensburg"],
    "buffalo": ["Buffalo", "Rochester", "Niagara Falls", "Cheektowaga", "Amherst", "Tonawanda"],
    "richmond": ["Richmond", "Charlottesville", "Hampton", "Norfolk", "Virginia Beach", "Newport News"],
    # Canada
    "toronto": ["Toronto", "Mississauga", "Brampton", "Markham", "Vaughan", "Richmond Hill"],
    "mississauga": ["Mississauga", "Toronto", "Brampton", "Oakville", "Burlington", "Vaughan"],
    "vancouver": ["Vancouver", "Burnaby", "Richmond", "Surrey", "Coquitlam", "North Vancouver"],
    "montreal": ["Montreal", "Laval", "Longueuil", "Brossard", "Saint-Laurent", "LaSalle"],
    "calgary": ["Calgary", "Airdrie", "Cochrane", "Okotoks", "Chestermere", "Red Deer"],
    "edmonton": ["Edmonton", "St. Albert", "Sherwood Park", "Leduc", "Spruce Grove", "Fort Saskatchewan"],
    "ottawa": ["Ottawa", "Gatineau", "Kanata", "Orleans", "Nepean", "Gloucester"],
    "winnipeg": ["Winnipeg", "Steinbach", "Portage la Prairie", "Brandon", "Selkirk", "Morden"],
    # UK
    "london": ["London", "Croydon", "Bromley", "Ealing", "Kingston upon Thames", "Watford"],
    "manchester": ["Manchester", "Salford", "Stockport", "Bolton", "Oldham", "Rochdale"],
    "birmingham": ["Birmingham", "Solihull", "Wolverhampton", "Coventry", "Dudley", "Walsall"],
    "leeds": ["Leeds", "Bradford", "Sheffield", "Wakefield", "Harrogate", "Halifax"],
    "sheffield": ["Sheffield", "Leeds", "Rotherham", "Barnsley", "Doncaster", "Chesterfield"],
    "edinburgh": ["Edinburgh", "Glasgow", "Livingston", "Dundee", "Perth", "Stirling"],
    "glasgow": ["Glasgow", "Edinburgh", "Paisley", "Hamilton", "East Kilbride", "Motherwell"],
    "bristol": ["Bristol", "Bath", "Swindon", "Gloucester", "Cheltenham", "Newport"],
    "oxford": ["Oxford", "London", "Reading", "Milton Keynes", "Banbury", "Abingdon"],
    "cambridge uk": ["Cambridge", "London", "Peterborough", "Ely", "Huntingdon", "Northampton"],
    "liverpool": ["Liverpool", "Manchester", "Birkenhead", "Chester", "Warrington", "Runcorn"],
    # Europe
    "paris": ["Paris", "Boulogne-Billancourt", "Versailles", "Nanterre", "Argenteuil", "Montreuil"],
    "berlin": ["Berlin", "Potsdam", "Frankfurt (Oder)", "Cottbus", "Brandenburg", "Oranienburg"],
    "munich": ["Munich", "Augsburg", "Ingolstadt", "Nuremberg", "Regensburg", "Landshut"],
    "frankfurt": ["Frankfurt", "Wiesbaden", "Darmstadt", "Mainz", "Offenbach", "Hanau"],
    "hamburg": ["Hamburg", "Bremen", "Lübeck", "Lüneburg", "Kiel", "Flensburg"],
    "cologne": ["Cologne", "Düsseldorf", "Bonn", "Aachen", "Leverkusen", "Mönchengladbach"],
    "düsseldorf": ["Düsseldorf", "Cologne", "Dortmund", "Essen", "Bonn", "Wuppertal"],
    "amsterdam": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Leiden", "Haarlem"],
    "rotterdam": ["Rotterdam", "Amsterdam", "The Hague", "Utrecht", "Delft", "Dordrecht"],
    "brussels": ["Brussels", "Antwerp", "Ghent", "Liège", "Namur", "Leuven"],
    "antwerp": ["Antwerp", "Brussels", "Ghent", "Bruges", "Leuven", "Mechelen"],
    "zurich": ["Zurich", "Basel", "Bern", "Geneva", "Lausanne", "Winterthur"],
    "geneva": ["Geneva", "Lausanne", "Zurich", "Bern", "Lyon", "Annecy"],
    "bern": ["Bern", "Zurich", "Basel", "Lausanne", "Fribourg", "Solothurn"],
    "stockholm": ["Stockholm", "Uppsala", "Solna", "Gothenburg", "Malmö", "Linköping"],
    "gothenburg": ["Gothenburg", "Stockholm", "Malmö", "Mölndal", "Borås", "Kungsbacka"],
    "oslo": ["Oslo", "Bergen", "Stavanger", "Trondheim", "Drammen", "Fredrikstad"],
    "copenhagen": ["Copenhagen", "Malmö", "Aarhus", "Odense", "Aalborg", "Helsingborg"],
    "helsinki": ["Helsinki", "Espoo", "Tampere", "Vantaa", "Oulu", "Turku"],
    "madrid": ["Madrid", "Alcalá de Henares", "Getafe", "Leganés", "Móstoles", "Alcorcón"],
    "barcelona": ["Barcelona", "Badalona", "Terrassa", "Sabadell", "Hospitalet", "Girona"],
    "milan": ["Milan", "Monza", "Bergamo", "Brescia", "Como", "Varese"],
    "rome": ["Rome", "Naples", "Florence", "Bologna", "Turin", "Palermo"],
    "naples": ["Naples", "Rome", "Salerno", "Caserta", "Torre del Greco", "Pozzuoli"],
    "florence": ["Florence", "Pisa", "Livorno", "Siena", "Arezzo", "Pistoia"],
    "turin": ["Turin", "Milan", "Asti", "Novara", "Cuneo", "Alessandria"],
    "vienna": ["Vienna", "Graz", "Linz", "Salzburg", "Innsbruck", "Wels"],
    "warsaw": ["Warsaw", "Łódź", "Kraków", "Wrocław", "Poznań", "Gdańsk"],
    "krakow": ["Kraków", "Warsaw", "Wrocław", "Rzeszów", "Katowice", "Nowy Sącz"],
    "prague": ["Prague", "Brno", "Ostrava", "Pilsen", "Liberec", "Olomouc"],
    "budapest": ["Budapest", "Debrecen", "Miskolc", "Szeged", "Pécs", "Győr"],
    "bucharest": ["Bucharest", "Cluj-Napoca", "Timișoara", "Iași", "Constanța", "Brașov"],
    "kyiv": ["Kyiv", "Kharkiv", "Odessa", "Lviv", "Dnipro", "Zaporizhzhia"],
    "lviv": ["Lviv", "Kyiv", "Kharkiv", "Odessa", "Dnipro", "Ternopil"],
    "lisbon": ["Lisbon", "Porto", "Amadora", "Setúbal", "Almada", "Braga"],
    "porto": ["Porto", "Lisbon", "Braga", "Gaia", "Matosinhos", "Gondomar"],
    "athens": ["Athens", "Thessaloniki", "Piraeus", "Patras", "Heraklion", "Larissa"],
    # Middle East
    "dubai": ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Doha", "Muscat"],
    "abu dhabi": ["Abu Dhabi", "Dubai", "Sharjah", "Al Ain", "Ras Al Khaimah", "Doha"],
    "doha": ["Doha", "Dubai", "Abu Dhabi", "Riyadh", "Kuwait City", "Manama"],
    "tel aviv": ["Tel Aviv", "Jerusalem", "Haifa", "Rishon LeZion", "Petah Tikva", "Beersheba"],
    "jerusalem": ["Jerusalem", "Tel Aviv", "Haifa", "Beersheba", "Rishon LeZion", "Bethlehem"],
    "riyadh": ["Riyadh", "Jeddah", "Mecca", "Dammam", "Medina", "Tabuk"],
    "jeddah": ["Jeddah", "Riyadh", "Mecca", "Dammam", "Medina", "Taif"],
    "istanbul": ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana"],
    "ankara": ["Ankara", "Istanbul", "Izmir", "Konya", "Bursa", "Eskişehir"],
    # Asia-Pacific
    "singapore": ["Singapore", "Johor Bahru", "Batam", "Kuala Lumpur", "Jakarta", "Bangkok"],
    "hong kong": ["Hong Kong", "Shenzhen", "Guangzhou", "Macau", "Zhuhai", "Dongguan"],
    "tokyo": ["Tokyo", "Yokohama", "Kawasaki", "Osaka", "Nagoya", "Saitama"],
    "osaka": ["Osaka", "Kyoto", "Kobe", "Nara", "Hiroshima", "Nagoya"],
    "kyoto": ["Kyoto", "Osaka", "Nara", "Kobe", "Shiga", "Uji"],
    "seoul": ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju"],
    "busan": ["Busan", "Seoul", "Ulsan", "Changwon", "Daegu", "Gimhae"],
    "beijing": ["Beijing", "Tianjin", "Shijiazhuang", "Qinhuangdao", "Baoding", "Tangshan"],
    "shanghai": ["Shanghai", "Suzhou", "Hangzhou", "Nanjing", "Wuxi", "Ningbo"],
    "shenzhen": ["Shenzhen", "Guangzhou", "Hong Kong", "Dongguan", "Foshan", "Zhuhai"],
    "guangzhou": ["Guangzhou", "Shenzhen", "Foshan", "Dongguan", "Zhuhai", "Hong Kong"],
    "hangzhou": ["Hangzhou", "Shanghai", "Ningbo", "Suzhou", "Nanjing", "Wuxi"],
    "chengdu": ["Chengdu", "Chongqing", "Xi'an", "Kunming", "Wuhan", "Guiyang"],
    "chongqing": ["Chongqing", "Chengdu", "Xi'an", "Wuhan", "Guiyang", "Kunming"],
    "taipei": ["Taipei", "New Taipei", "Taoyuan", "Taichung", "Tainan", "Kaohsiung"],
    "mumbai": ["Mumbai", "Pune", "Thane", "Navi Mumbai", "Nashik", "Aurangabad"],
    "pune": ["Pune", "Mumbai", "Nashik", "Aurangabad", "Kolhapur", "Solapur"],
    "delhi": ["Delhi", "Gurgaon", "Noida", "Faridabad", "Ghaziabad", "Greater Noida"],
    "gurgaon": ["Gurgaon", "Delhi", "Noida", "Faridabad", "Ghaziabad", "Greater Noida"],
    "noida": ["Noida", "Delhi", "Gurgaon", "Ghaziabad", "Greater Noida", "Faridabad"],
    "bangalore": ["Bangalore", "Mysore", "Mangalore", "Hyderabad", "Chennai", "Coimbatore"],
    "bengaluru": ["Bangalore", "Mysore", "Mangalore", "Hyderabad", "Chennai", "Coimbatore"],
    "hyderabad": ["Hyderabad", "Secunderabad", "Vijayawada", "Warangal", "Bangalore", "Pune"],
    "chennai": ["Chennai", "Vellore", "Coimbatore", "Madurai", "Pondicherry", "Bangalore"],
    "kolkata": ["Kolkata", "Howrah", "Asansol", "Durgapur", "Siliguri", "Patna"],
    "jakarta": ["Jakarta", "Surabaya", "Bandung", "Bekasi", "Tangerang", "Depok"],
    "kuala lumpur": ["Kuala Lumpur", "Petaling Jaya", "Shah Alam", "Subang Jaya", "Cyberjaya", "Putrajaya"],
    "bangkok": ["Bangkok", "Nonthaburi", "Pak Kret", "Hat Yai", "Chiang Mai", "Pattaya"],
    "ho chi minh city": ["Ho Chi Minh City", "Hanoi", "Da Nang", "Bien Hoa", "Nha Trang", "Vung Tau"],
    "hanoi": ["Hanoi", "Ho Chi Minh City", "Da Nang", "Hai Phong", "Huế", "Can Tho"],
    "manila": ["Manila", "Quezon City", "Makati", "Cebu", "Davao", "Pasig"],
    "cebu": ["Cebu", "Manila", "Davao", "Lapu-Lapu", "Mandaue", "Zamboanga"],
    "dhaka": ["Dhaka", "Chittagong", "Sylhet", "Rajshahi", "Khulna", "Comilla"],
    "karachi": ["Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad", "Multan"],
    "lahore": ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad", "Gujranwala"],
    "islamabad": ["Islamabad", "Rawalpindi", "Lahore", "Peshawar", "Murree", "Attock"],
    "colombo": ["Colombo", "Kandy", "Galle", "Negombo", "Jaffna", "Trincomalee"],
    # Australia & NZ
    "sydney": ["Sydney", "Melbourne", "Brisbane", "Parramatta", "Wollongong", "Newcastle"],
    "melbourne": ["Melbourne", "Sydney", "Geelong", "Ballarat", "Bendigo", "Frankston"],
    "brisbane": ["Brisbane", "Gold Coast", "Sunshine Coast", "Ipswich", "Toowoomba", "Logan"],
    "perth": ["Perth", "Fremantle", "Mandurah", "Joondalup", "Rockingham", "Bunbury"],
    "adelaide": ["Adelaide", "Glenelg", "Port Adelaide", "Mount Barker", "Victor Harbor", "Murray Bridge"],
    "canberra": ["Canberra", "Sydney", "Wollongong", "Goulburn", "Queanbeyan", "Bateman's Bay"],
    "auckland": ["Auckland", "Wellington", "Christchurch", "Manukau", "Hamilton", "Tauranga"],
    "wellington": ["Wellington", "Auckland", "Christchurch", "Lower Hutt", "Upper Hutt", "Porirua"],
    # Latin America
    "sao paulo": ["São Paulo", "Campinas", "Guarulhos", "São Bernardo do Campo", "Santo André", "Osasco"],
    "são paulo": ["São Paulo", "Campinas", "Guarulhos", "São Bernardo do Campo", "Santo André", "Osasco"],
    "rio de janeiro": ["Rio de Janeiro", "Niterói", "Nova Iguaçu", "Duque de Caxias", "São Gonçalo", "Belford Roxo"],
    "buenos aires": ["Buenos Aires", "Córdoba", "Rosario", "La Plata", "Mar del Plata", "Mendoza"],
    "bogota": ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", "Cúcuta"],
    "bogotá": ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", "Cúcuta"],
    "medellin": ["Medellín", "Bogotá", "Cali", "Barranquilla", "Cartagena", "Pereira"],
    "medellín": ["Medellín", "Bogotá", "Cali", "Barranquilla", "Cartagena", "Pereira"],
    "santiago": ["Santiago", "Valparaíso", "Concepción", "La Serena", "Antofagasta", "Temuco"],
    "lima": ["Lima", "Arequipa", "Trujillo", "Chiclayo", "Piura", "Cusco"],
    "mexico city": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Toluca", "Tijuana"],
    "guadalajara": ["Guadalajara", "Mexico City", "Monterrey", "Zapopan", "Tlaquepaque", "León"],
    "monterrey": ["Monterrey", "Guadalajara", "Mexico City", "San Nicolás de los Garza", "Apodaca", "Saltillo"],
    # Africa
    "lagos": ["Lagos", "Abuja", "Kano", "Ibadan", "Port Harcourt", "Benin City"],
    "abuja": ["Abuja", "Lagos", "Kano", "Ibadan", "Jos", "Kaduna"],
    "cairo": ["Cairo", "Alexandria", "Giza", "Luxor", "Aswan", "Sharm el-Sheikh"],
    "johannesburg": ["Johannesburg", "Cape Town", "Durban", "Pretoria", "Port Elizabeth", "East London"],
    "cape town": ["Cape Town", "Johannesburg", "Durban", "Stellenbosch", "Paarl", "George"],
    "nairobi": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Kampala", "Dar es Salaam"],
    "accra": ["Accra", "Lagos", "Abidjan", "Dakar", "Kumasi", "Tema"],
    "addis ababa": ["Addis Ababa", "Nairobi", "Kampala", "Khartoum", "Djibouti", "Asmara"],
    "casablanca": ["Casablanca", "Rabat", "Marrakech", "Fez", "Tangier", "Agadir"],
    "tunis": ["Tunis", "Sfax", "Sousse", "Bizerte", "Kairouan", "Gabès"],
    "algiers": ["Algiers", "Oran", "Constantine", "Annaba", "Blida", "Tlemcen"],
}


def get_city_suggestions_static(city: str, region: str) -> list[str] | None:
    """
    Return 6 nearby cities without an LLM call.
    Returns None when the city is not in the static list (caller should fall back to LLM).
    """
    key = city.strip().lower()
    if not key:
        return None

    # Exact match
    if key in CITY_GROUPS:
        return CITY_GROUPS[key]

    # Partial match — key contained in a group key or vice versa
    for k, v in CITY_GROUPS.items():
        if key == k:
            return v
        if len(key) >= 4 and (key in k or k in key):
            # Bring the user's input city to front if it appears in the list
            result = v.copy()
            for i, c in enumerate(result):
                if city.strip().lower() in c.lower() or c.lower() in city.strip().lower():
                    result.insert(0, result.pop(i))
                    break
            return result[:6]

    return None
