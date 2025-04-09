from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction
import json
import re
from datetime import datetime

# Helper function to load the JSON data
def load_sports_data():
    try:
        with open('../data/sports_results.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        try:
            with open('data/sports_results.json', 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            try:
                with open('sports_results.json', 'r', encoding='utf-8') as file:
                    return json.load(file)
            except:
                # If we can't find the file, return empty structure
                return {"Football": {}, "Basketball": {}}

# Function to determine which sport the user is talking about
def determine_sport(tracker, message=None):
    # First check if a sport slot is already set
    sport = tracker.get_slot('sport')
    if sport:
        return sport
        
    # If no message provided, use the latest message from tracker
    if not message:
        message = tracker.latest_message.get('text', '').lower()
    
    # Basketball-specific terms
    basketball_terms = ["nba", "euroleague", "points", "basketball", "celtics", "lakers", 
                        "warriors", "basketball", "arena", "boston celtics", "los angeles lakers",
                        "golden state", "bulls", "heat"]
    
    # Football-specific terms  
    football_terms = ["laliga", "premier", "football", "soccer", "barcelona", "madrid", 
                     "goal", "stadium", "liverpool", "manchester", "arsenal", "chelsea"]
    
    # Count mentions of sport-specific terms
    basketball_count = sum(1 for term in basketball_terms if term in message.lower())
    football_count = sum(1 for term in football_terms if term in message.lower())
    
    # Determine the most likely sport context
    if basketball_count > football_count:
        return "Basketball"
    else:
        return "Football"  # Default to Football

# Function to check if a match is upcoming (not played yet)
def is_upcoming_match(match):
    """Check if a match has not been played yet"""
    return "score" not in match or match["score"] == "Postponed"

# Function to normalize team names for more accurate matching
def normalize_team_name(team_name):
    """
    Normalizes team names to handle various ways teams might be referenced.
    Returns a standardized team name for consistent matching.
    """
    if not team_name:
        return ""
    
    team_name = team_name.lower().strip()
    
    # Comprehensive team name variations dictionary
    team_variations = {
        # FOOTBALL TEAMS
        
        # LaLiga Teams
        "barcelona": ["barcelona", "fc barcelona", "barca", "barça", "fcb", "blaugrana"],
        "real madrid": ["real madrid", "madrid", "real", "los blancos", "merengues", "rmcf"],
        "atletico madrid": ["atletico madrid", "atlético madrid", "atleti", "atletico", "atlético", "colchoneros"],
        "sevilla": ["sevilla", "sevilla fc", "sevillistas"],
        "real betis": ["betis", "real betis", "real betis balompié", "verdiblancos"],
        "valencia": ["valencia", "valencia cf", "valencia club de futbol", "los che"],
        "villarreal": ["villarreal", "villarreal cf", "el submarino amarillo", "yellow submarine"],
        "athletic bilbao": ["athletic bilbao", "athletic club", "los leones", "athletic"],
        "real sociedad": ["real sociedad", "la real", "txuri-urdin"],
        "osasuna": ["osasuna", "ca osasuna", "los rojillos"],
        "mallorca": ["mallorca", "rcd mallorca", "los bermellones"],
        "espanyol": ["espanyol", "rcd espanyol", "periquitos"],
        "celta vigo": ["celta vigo", "celta", "celta de vigo", "rc celta", "célticos"],
        "getafe": ["getafe", "getafe cf", "azulones"],
        "valladolid": ["valladolid", "real valladolid", "blanquivioletas", "pucelanos"],
        "leganes": ["leganes", "leganés", "cd leganés", "pepineros"],
        "alaves": ["alaves", "alavés", "deportivo alavés", "babazorros"],
        "girona": ["girona", "girona fc"],
        "rayo vallecano": ["rayo vallecano", "rayo", "los franjirrojos"],
        "las palmas": ["las palmas", "ud las palmas", "amarillos"],
        
        # Premier League Teams
        "liverpool": ["liverpool", "liverpool fc", "liverpool f.c.", "lfc", "the reds", "reds"],
        "manchester united": ["manchester united", "man united", "man utd", "united", "mufc", "red devils"],
        "manchester city": ["manchester city", "man city", "city", "mcfc", "citizens", "sky blues"],
        "chelsea": ["chelsea", "chelsea fc", "cfc", "blues", "the pensioners"],
        "arsenal": ["arsenal", "arsenal fc", "the gunners", "gunners", "afc"],
        "tottenham": ["tottenham", "tottenham hotspur", "spurs", "thfc"],
        "leicester": ["leicester", "leicester city", "foxes", "lcfc"],
        "west ham": ["west ham", "west ham united", "hammers", "irons", "whu"],
        "everton": ["everton", "everton fc", "the toffees", "toffees", "efc"],
        "newcastle": ["newcastle", "newcastle united", "magpies", "toon", "nufc"],
        "aston villa": ["aston villa", "villa", "villans", "avfc"],
        "wolverhampton": ["wolverhampton", "wolves", "wolverhampton wanderers", "wwfc"],
        "southampton": ["southampton", "saints", "soton", "southampton fc"],
        "crystal palace": ["crystal palace", "palace", "eagles", "cpfc"],
        "brighton": ["brighton", "brighton & hove albion", "brighton and hove albion", "seagulls", "bha"],
        "burnley": ["burnley", "burnley fc", "clarets"],
        "leeds": ["leeds", "leeds united", "leeds utd", "whites", "peacocks", "lufc"],
        "brentford": ["brentford", "brentford fc", "bees"],
        "norwich": ["norwich", "norwich city", "canaries", "ncfc"],
        "watford": ["watford", "watford fc", "hornets"],
        "nottingham forest": ["nottingham forest", "nottm forest", "forest", "nffc", "tricky trees"],
        "fulham": ["fulham", "fulham fc", "cottagers", "whites", "ffc"],
        "bournemouth": ["bournemouth", "afc bournemouth", "cherries"],
        "ipswich": ["ipswich", "ipswich town", "tractor boys", "itfc"],
        
        # BASKETBALL TEAMS
        
        # NBA Teams
        "lakers": ["lakers", "los angeles lakers", "la lakers", "los angeles", "purple and gold"],
        "celtics": ["celtics", "boston celtics", "boston", "c's"],
        "warriors": ["warriors", "golden state warriors", "golden state", "dubs", "gsw"],
        "bulls": ["bulls", "chicago bulls", "chicago"],
        "heat": ["heat", "miami heat", "miami"],
        "bucks": ["bucks", "milwaukee bucks", "milwaukee"],
        "mavericks": ["mavericks", "dallas mavericks", "dallas", "mavs"],
        "nets": ["nets", "brooklyn nets", "brooklyn"],
        "knicks": ["knicks", "new york knicks", "new york", "ny knicks"],
        "76ers": ["76ers", "philadelphia 76ers", "philadelphia", "phila", "sixers"],
        "suns": ["suns", "phoenix suns", "phoenix"],
        "spurs": ["spurs", "san antonio spurs", "san antonio"],
        "nuggets": ["nuggets", "denver nuggets", "denver"],
        "clippers": ["clippers", "los angeles clippers", "la clippers"],
        "cavaliers": ["cavaliers", "cleveland cavaliers", "cleveland", "cavs"],
        "hawks": ["hawks", "atlanta hawks", "atlanta"],
        "grizzlies": ["grizzlies", "memphis grizzlies", "memphis"],
        "pelicans": ["pelicans", "new orleans pelicans", "new orleans"],
        "rockets": ["rockets", "houston rockets", "houston"],
        "jazz": ["jazz", "utah jazz", "utah"],
        "kings": ["kings", "sacramento kings", "sacramento"],
        "magic": ["magic", "orlando magic", "orlando"],
        "pacers": ["pacers", "indiana pacers", "indiana"],
        "pistons": ["pistons", "detroit pistons", "detroit"],
        "raptors": ["raptors", "toronto raptors", "toronto"],
        "thunder": ["thunder", "oklahoma city thunder", "oklahoma city", "okc"],
        "timberwolves": ["timberwolves", "minnesota timberwolves", "minnesota", "wolves"],
        "trail blazers": ["trail blazers", "portland trail blazers", "portland", "blazers"],
        "wizards": ["wizards", "washington wizards", "washington"],
        "hornets": ["hornets", "charlotte hornets", "charlotte"],
        
        # EuroLeague Teams
        "real madrid": ["real madrid", "real madrid baloncesto", "madrid basketball"],
        "barcelona": ["barcelona", "fc barcelona", "barça basketball", "barça basket", "fcb basketball"],
        "olympiacos": ["olympiacos", "olympiacos piraeus", "oly", "olympiacos bc"],
        "panathinaikos": ["panathinaikos", "panathinaikos aktor", "pao", "panathinaikos bc"],
        "fenerbahce": ["fenerbahce", "fenerbahçe", "fenerbahce beko", "fenerbahçe beko"],
        "cska moscow": ["cska moscow", "cska", "cska moskva"],
        "anadolu efes": ["anadolu efes", "efes", "efes pilsen"],
        "monaco": ["monaco", "as monaco", "as monaco basket"],
        "baskonia": ["baskonia", "td systems baskonia", "saski baskonia"],
        "milano": ["milano", "olimpia milano", "emporio armani milano", "armani milano", "olimpia milan"],
        "zalgiris": ["zalgiris", "zalgiris kaunas"],
        "alba berlin": ["alba berlin", "alba", "berlin"],
        "asvel": ["asvel", "ldlc asvel", "ldlc asvel villeurbanne", "villeurbanne"]
    }
    
    # Check for team name in variations
    for standard_name, variations in team_variations.items():
        # First check exact matches
        if team_name in variations:
            return standard_name
        
        # Then check for partial matches (team name is contained within a variation or vice versa)
        for variant in variations:
            # Check if the variant contains the team name
            if team_name in variant:
                return standard_name
            # Check if the team name contains the variant (for when full name is given but we're looking for a shorter variant)
            if len(variant) > 3 and variant in team_name:  # Only for variants longer than 3 chars to avoid false matches
                return standard_name
    
    # Remove common prefixes/suffixes for better matching
    prefixes = ["fc ", "cf ", "afc ", "f.c. ", "ac ", "cd ", "sc ", "rcd ", "rc ", "ud ", "as "]
    for prefix in prefixes:
        if team_name.startswith(prefix):
            team_name = team_name[len(prefix):]
    
    return team_name


# Function to check if a team is involved in a match
def is_team_in_match(team_name, match):
    if not team_name:
        return False
    team_name = normalize_team_name(team_name)
    home_team = normalize_team_name(match.get("home_team", ""))
    away_team = normalize_team_name(match.get("away_team", ""))
    
    # Check for exact matches or if team name is part of the full name
    return team_name == home_team or team_name == away_team or \
           team_name in home_team or team_name in away_team

class ActionSetSport(Action):
    def name(self):
        return "action_set_sport"
    
    def run(self, dispatcher, tracker, domain):
        sport = tracker.get_slot('sport')
        message = tracker.latest_message.get('text', '').lower()
        
        # Detect if the message contains questions about specific information
        has_standings_query = any(term in message for term in ["standings", "table", "rankings", "positions"])
        has_fixture_query = any(term in message for term in ["match", "fixture", "playing next", "games", "upcoming"])
        has_score_query = any(term in message for term in ["score", "result", "win", "lose", "beat"])
        has_scorer_query = any(term in message for term in ["score", "scorer", "goal", "point", "basket"])
        has_stadium_query = any(term in message for term in ["stadium", "arena", "venue", "play", "home"])
        
        if sport:
            sport = sport.strip().title()
            if sport == "Football" or sport == "Soccer":
                # Set sport slot
                result = [SlotSet("sport", "Football")]
                
                # If the message also contains specific questions, follow up with the appropriate action
                if has_standings_query:
                    return result + [FollowupAction("action_get_standings")]
                elif has_fixture_query:
                    return result + [FollowupAction("action_get_fixture")]
                elif has_score_query:
                    return result + [FollowupAction("action_get_score")]
                elif has_scorer_query and sport == "Football":
                    return result + [FollowupAction("action_get_goal_scorers")]
                elif has_scorer_query and sport == "Basketball":
                    return result + [FollowupAction("action_get_top_scorers")]
                elif has_stadium_query:
                    return result + [FollowupAction("action_get_stadium")]
                else:
                    dispatcher.utter_message(text=f"I'll provide you with football information. What would you like to know?")
                    return result
                
            elif sport == "Basketball":
                # Set sport slot
                result = [SlotSet("sport", "Basketball")]
                
                # If the message also contains specific questions, follow up with the appropriate action
                if has_standings_query:
                    return result + [FollowupAction("action_get_standings")]
                elif has_fixture_query:
                    return result + [FollowupAction("action_get_fixture")]
                elif has_score_query:
                    return result + [FollowupAction("action_get_score")]
                elif has_scorer_query:
                    return result + [FollowupAction("action_get_top_scorers")]
                elif has_stadium_query:
                    return result + [FollowupAction("action_get_stadium")]
                else:
                    dispatcher.utter_message(text=f"I'll provide you with basketball information. What would you like to know?")
                    return result
            else:
                dispatcher.utter_message(text=f"I can only provide information about football or basketball. Let's talk about football by default.")
                return [SlotSet("sport", "Football")]
        else:
            # Determine sport from message context
            sport = determine_sport(tracker)
            result = [SlotSet("sport", sport)]
            
            # Direct request to appropriate handler if specific question is detected
            if has_standings_query:
                return result + [FollowupAction("action_get_standings")]
            elif has_fixture_query:
                return result + [FollowupAction("action_get_fixture")]
            elif has_score_query:
                return result + [FollowupAction("action_get_score")]
            elif has_scorer_query and sport == "Football":
                return result + [FollowupAction("action_get_goal_scorers")]
            elif has_scorer_query and sport == "Basketball":
                return result + [FollowupAction("action_get_top_scorers")]
            elif has_stadium_query:
                return result + [FollowupAction("action_get_stadium")]
            else:
                dispatcher.utter_message(text=f"I'm not sure which sport you're interested in. Let's talk about {sport} by default.")
                return result

class ActionGetStandings(Action):
    def name(self):
        return "action_get_standings"

    def run(self, dispatcher, tracker, domain):
        sport = determine_sport(tracker)
        league = tracker.get_slot('league')
        message = tracker.latest_message.get('text', '').lower()
        
        # Check if asking for the top team specifically
        is_asking_for_top = "top" in message or "leading" in message or "first" in message or "winner" in message
        
        if not league:
            # Try to extract from the message if no slot is set
            if "laliga" in message or "la liga" in message:
                league = "LaLiga"
                sport = "Football"
            elif any(term in message for term in ["premier", "premierleague", "premier league", "Premier League"]):
                league = "PremierLeague"
                sport = "Football"
            elif "nba" in message:
                league = "NBA"
                sport = "Basketball"
            elif "euroleague" in message:
                league = "EuroLeague"
                sport = "Basketball"
            else:
                if sport == "Football":
                    dispatcher.utter_message(text="Please specify which football league you're interested in (LaLiga or PremierLeague).")
                else:
                    dispatcher.utter_message(text="Please specify which basketball league you're interested in (NBA or EuroLeague).")
                return []
        
        league = league.strip()
        # Standardize league name based on sport
        if sport == "Football":
            if league.lower() == "laliga" or league.lower() == "la liga":
                league = "LaLiga"
            elif league.lower() == "premierleague" or league.lower() == "premier league":
                league = "PremierLeague"
        elif sport == "Basketball":
            if league.lower() == "nba":
                league = "NBA"
            elif league.lower() == "euroleague" or league.lower() == "euro league":
                league = "EuroLeague"
            
        data = load_sports_data()
        sport_data = data.get(sport, {})
        
        standings = sport_data.get(league, {}).get('standings', [])
        if standings:
            if is_asking_for_top:
                # Only show the top team
                top_team = standings[0]
                if sport == "Football":
                    response = f"The top team in {league} is {top_team['team']} with {top_team['points']} points " + \
                              f"({top_team['won']} wins, {top_team['drawn']} draws, {top_team['lost']} losses)."
                else:  # Basketball
                    response = f"The top team in {league} is {top_team['team']} with {top_team['win_percentage']} win percentage " + \
                              f"({top_team['won']}-{top_team['lost']})."
                dispatcher.utter_message(text=response)
                return []
            else:
                # Show complete standings
                response = f"Current top 5 standings in {league}:\n"
                for team in standings[:5]:
                    if sport == "Football":
                        response += f"{team['position']}. {team['team']} - {team['points']} pts ({team['won']}-{team['drawn']}-{team['lost']})\n"
                    else:  # Basketball
                        response += f"{team['position']}. {team['team']} - {team['win_percentage']} win% ({team['won']}-{team['lost']})\n"
                dispatcher.utter_message(text=response)
                return []
        else:
            response = f"No standings found for {league} in {sport}."
        
        dispatcher.utter_message(text=response)
        return []


class ActionGetFixture(Action):
    def name(self):
        return "action_get_fixture"

    def run(self, dispatcher, tracker, domain):
        sport = determine_sport(tracker)
        league = tracker.get_slot('league')
        matchday = tracker.get_slot('matchday')
        team = tracker.get_slot('team')
        
        message = tracker.latest_message.get('text', '').lower()
        is_upcoming_query = any(word in message for word in ["next", "upcoming", "future", "soon", "following", "scheduled"])
        
        data = load_sports_data()
        sport_data = data.get(sport, {})
        
        # Handle basketball-specific terminology
        fixtures_key = "fixtures"  # football default
        if sport == "Basketball":
            fixtures_key = "games"
            if matchday and "matchday" in matchday.lower():
                # Convert football-style "Matchday X" to "Week X" for basketball
                week_num = matchday.lower().replace("matchday", "").strip()
                matchday = f"Week {week_num}"
        
        # Extract team from text if not in slot
        if not team:
            # Sport-specific common teams
            common_teams = []
            if sport == "Football":
                common_teams = ["barcelona", "real madrid", "manchester", "liverpool", "arsenal", "chelsea"]
            else:  # Basketball
                common_teams = ["lakers", "los angeles", "celtics", "boston", "warriors", "bulls", "heat", "bucks"]
                
            for common_team in common_teams:
                if common_team in message:
                    team = common_team
                    break
        
        # If team is provided, find their next fixture
        if team:
            team = normalize_team_name(team)
            found_upcoming = False
            
            # First look for upcoming matches (without scores)
            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict):
                    for matchday_name, matchday_data in league_data.items():
                        # Skip the standings entry
                        if matchday_name == "standings":
                            continue
                            
                        if isinstance(matchday_data, dict) and fixtures_key in matchday_data:
                            for match in matchday_data[fixtures_key]:
                                # Skip matches with scores (already played)
                                if not is_upcoming_match(match):
                                    continue
                                    
                                if is_team_in_match(team, match):
                                    date = match.get("date", "Date not specified")
                                    time = match.get("time", "")
                                    location = match.get("stadium", match.get("arena", "Location not specified"))
                                    
                                    if sport == "Football":
                                        response = f"Next fixture: {match['home_team']} vs {match['away_team']} on {date}"
                                    else:  # Basketball
                                        response = f"Next game: {match['home_team']} vs {match['away_team']} on {date}"
                                        
                                    if time:
                                        response += f" at {time}"
                                    response += f", {location}"
                                    
                                    dispatcher.utter_message(text=response)
                                    found_upcoming = True
                                    return []
            
            # If no upcoming matches, show the most recent match
            if not found_upcoming:
                most_recent_match = None
                most_recent_date = "0000-00-00"
                
                for league_name, league_data in sport_data.items():
                    if isinstance(league_data, dict):
                        for matchday_name, matchday_data in league_data.items():
                            # Skip the standings entry
                            if matchday_name == "standings":
                                continue
                                
                            if isinstance(matchday_data, dict) and fixtures_key in matchday_data:
                                for match in matchday_data[fixtures_key]:
                                    if is_team_in_match(team, match) and "score" in match and match["score"] != "Postponed":
                                        match_date = match.get("date", "0000-00-00")
                                        if match_date > most_recent_date:
                                            most_recent_date = match_date
                                            most_recent_match = match
                
                if most_recent_match:
                    date = most_recent_match.get("date", "Date not specified")
                    time = most_recent_match.get("time", "")
                    location = most_recent_match.get("stadium", most_recent_match.get("arena", "Location not specified"))
                    score = most_recent_match.get("score", "Unknown score")
                    
                    if sport == "Football":
                        response = f"Most recent match: {most_recent_match['home_team']} vs {most_recent_match['away_team']} ended {score} on {date}"
                    else:  # Basketball
                        response = f"Most recent game: {most_recent_match['home_team']} vs {most_recent_match['away_team']} ended {score} on {date}"
                        
                    if time:
                        response += f" at {time}"
                    response += f", {location}"
                    
                    dispatcher.utter_message(text=response)
                    return []
                else:
                    dispatcher.utter_message(text=f"Couldn't find any matches for {team}.")
                    return []
        
        # If matchday is provided, show fixtures for that matchday
        if matchday:
            matchday = matchday.strip()
            responses = []
            leagues_with_data = []
            
            # If league is also provided
            if league:
                league_data = sport_data.get(league, {})
                matchday_data = league_data.get(matchday, {})
                fixtures = matchday_data.get(fixtures_key, [])
                
                if fixtures:
                    if sport == "Football":
                        response = f"{matchday} fixtures in {league}:\n"
                    else:  # Basketball
                        response = f"{matchday} games in {league}:\n"
                        
                    for match in fixtures:
                        fixture_info = f"{match['home_team']} vs {match['away_team']} on {match['date']}"
                        if "time" in match:
                            fixture_info += f" at {match['time']}"
                        response += fixture_info + "\n"
                    responses.append(response)
                    leagues_with_data.append(league)
            else:
                # If no league is specified, show fixtures from all leagues of the sport
                for league_name, league_data in sport_data.items():
                    if isinstance(league_data, dict) and matchday in league_data:
                        matchday_data = league_data[matchday]
                        fixtures = matchday_data.get(fixtures_key, [])
                        
                        if fixtures:
                            if sport == "Football":
                                response = f"{matchday} fixtures in {league_name}:\n"
                            else:  # Basketball
                                response = f"{matchday} games in {league_name}:\n"
                                
                            for match in fixtures:
                                fixture_info = f"{match['home_team']} vs {match['away_team']} on {match['date']}"
                                if "time" in match:
                                    fixture_info += f" at {match['time']}"
                                response += fixture_info + "\n"
                            responses.append(response)
                            leagues_with_data.append(league_name)
            
            if responses:
                # If not all leagues have data for this matchday
                if len(leagues_with_data) < len(sport_data):
                    missing_leagues = [name for name in sport_data.keys() if name not in leagues_with_data]
                    if missing_leagues:
                        dispatcher.utter_message(text=f"Note: {matchday} information is only available for {', '.join(leagues_with_data)}. No data for {', '.join(missing_leagues)}.")
                
                # Send each league's fixtures as a separate message
                for response in responses:
                    dispatcher.utter_message(text=response)
                return []
            else:
                dispatcher.utter_message(text=f"No fixtures found for {matchday} in {sport}.")
                return []
        
        # If just asking for upcoming fixtures in general
        if is_upcoming_query and not team and not matchday:
            upcoming_matches = []
            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict):
                    league_upcoming = []
                    for matchday_name, matchday_data in league_data.items():
                        # Skip the standings entry
                        if matchday_name == "standings":
                            continue
                            
                        if isinstance(matchday_data, dict) and fixtures_key in matchday_data:
                            for match in matchday_data[fixtures_key]:
                                if is_upcoming_match(match):
                                    league_upcoming.append({
                                        "matchday": matchday_name,
                                        "match": match
                                    })
                    
                    if league_upcoming:
                        # Sort by date if available
                        league_upcoming.sort(key=lambda x: x["match"].get("date", "9999-99-99"))
                        # Take the first 5 upcoming matches
                        if sport == "Football":
                            response = f"Upcoming matches in {league_name}:\n"
                        else:  # Basketball
                            response = f"Upcoming games in {league_name}:\n"
                            
                        for item in league_upcoming[:5]:
                            match = item["match"]
                            match_info = f"{match['home_team']} vs {match['away_team']} on {match.get('date', 'TBD')}"
                            if "time" in match:
                                match_info += f" at {match['time']}"
                            response += f"{match_info} ({item['matchday']})\n"
                        upcoming_matches.append(response)
            
            if upcoming_matches:
                for response in upcoming_matches:
                    dispatcher.utter_message(text=response)
                return []
            else:
                dispatcher.utter_message(text=f"No upcoming matches found for {sport}.")
                return []
                
        # If we're asking about upcoming fixtures for a specific league
        if league and is_upcoming_query:
            league_data = sport_data.get(league, {})
            upcoming_matches = []
            
            for matchday_name, matchday_data in league_data.items():
                # Skip the standings entry
                if matchday_name == "standings":
                    continue
                    
                if isinstance(matchday_data, dict) and fixtures_key in matchday_data:
                    for match in matchday_data[fixtures_key]:
                        if is_upcoming_match(match):
                            upcoming_matches.append({
                                "matchday": matchday_name,
                                "match": match
                            })
            
            if upcoming_matches:
                # Sort by date
                upcoming_matches.sort(key=lambda x: x["match"].get("date", "9999-99-99"))
                # Take the first 5 upcoming matches
                if sport == "Football":
                    response = f"Upcoming matches in {league}:\n"
                else:  # Basketball
                    response = f"Upcoming games in {league}:\n"
                    
                for item in upcoming_matches[:5]:
                    match = item["match"]
                    match_info = f"{match['home_team']} vs {match['away_team']} on {match.get('date', 'TBD')}"
                    if "time" in match:
                        match_info += f" at {match['time']}"
                    response += f"{match_info} ({item['matchday']})\n"
                dispatcher.utter_message(text=response)
                return []
            else:
                dispatcher.utter_message(text=f"No upcoming matches found for {league} in {sport}.")
                return []
        
        dispatcher.utter_message(text=f"Please provide more details about the fixtures you're looking for in {sport}.")
        return []


class ActionGetScore(Action):
    def name(self):
        return "action_get_score"

    def run(self, dispatcher, tracker, domain):
        sport = determine_sport(tracker)
        entities = tracker.latest_message.get('entities', [])
        teams = []
        
        # Extract team names from entities
        for entity in entities:
            if entity['entity'] == 'team':
                teams.append(entity['value'])
        
        # If no teams found in entities, try to extract from message
        if not teams:
            message = tracker.latest_message.get('text', '').lower()
            common_teams = []
            if sport == "Football":
                common_teams = ["barcelona", "real madrid", "liverpool", "manchester united", 
                              "arsenal", "chelsea", "atletico", "manchester city"]
            else:  # Basketball
                common_teams = ["lakers", "los angeles", "celtics", "boston", "warriors", 
                              "bulls", "heat", "bucks", "phoenix", "nuggets", "mavericks", "nets"]
                
            for team in common_teams:
                if team.lower() in message:
                    teams.append(team)
        
        # If still no team found
        if not teams:
            dispatcher.utter_message(text=f"Please specify which team's score you're interested in for {sport}.")
            return []
        
        data = load_sports_data()
        sport_data = data.get(sport, {})
        
        # Different keys for different sports
        fixtures_key = "fixtures" if sport == "Football" else "games"
        scorers_key = "goal_scorers" if sport == "Football" else "top_scorers"
        
        # First try to find matches with both teams if multiple teams are detected
        if len(teams) > 1:
            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict):
                    for matchday_name, matchday_data in league_data.items():
                        # Skip the standings entry
                        if matchday_name == "standings":
                            continue
                            
                        if isinstance(matchday_data, dict) and fixtures_key in matchday_data:
                            for match in matchday_data[fixtures_key]:
                                if "score" not in match or match["score"] == "Postponed":
                                    continue
                                
                                # Check if both teams are in this match
                                team_count = 0
                                for team in teams:
                                    if is_team_in_match(team, match):
                                        team_count += 1
                                
                                if team_count >= 2:
                                    score = match.get('score', 'Not available')
                                    date = match.get('date', 'Date unknown')
                                    
                                    if sport == "Football":
                                        response = f"{match['home_team']} vs {match['away_team']} ended {score} on {date}."
                                        
                                        # Add goal scorers if available
                                        if scorers_key in match and match[scorers_key]:
                                            response += "\n\nGoal scorers:"
                                            for team_name, scorers in match[scorers_key].items():
                                                if scorers:
                                                    scorer_list = ", ".join(scorers)
                                                    response += f"\n{team_name}: {scorer_list}"
                                    else:  # Basketball
                                        quarters = match.get('quarters', [])
                                        quarters_str = ", ".join(quarters) if quarters else ""
                                        
                                        response = f"{match['home_team']} vs {match['away_team']} ended {score} on {date}."
                                        if quarters_str:
                                            response += f"\nQuarter scores: {quarters_str}"
                                            
                                        # Add top scorers if available
                                        if scorers_key in match and match[scorers_key]:
                                            response += "\n\nTop scorers:"
                                            for team_name, scorers in match[scorers_key].items():
                                                if scorers:
                                                    for scorer in scorers[:3]:  # Show top 3 scorers
                                                        response += f"\n{team_name}: {scorer['name']} - {scorer['points']} pts"
                                    
                                    dispatcher.utter_message(text=response)
                                    return []
        
        # If we didn't find a match with both teams, search for matches with any of the teams
        for team in teams:
            normalized_team = normalize_team_name(team)
            
            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict):
                    for matchday_name, matchday_data in league_data.items():
                        # Skip the standings entry
                        if matchday_name == "standings":
                            continue
                            
                        if isinstance(matchday_data, dict) and fixtures_key in matchday_data:
                            for match in matchday_data[fixtures_key]:
                                if "score" not in match or match["score"] == "Postponed":
                                    continue
                                
                                # Try different normalization approaches to find the team
                                home_team_norm = normalize_team_name(match['home_team'])
                                away_team_norm = normalize_team_name(match['away_team'])
                                
                                if normalized_team in home_team_norm or normalized_team in away_team_norm:
                                    score = match.get('score', 'Not available')
                                    date = match.get('date', 'Date unknown')
                                    
                                    # Check if team won 
                                    win_status = ""
                                    if "did" in tracker.latest_message.get('text', '').lower() and "win" in tracker.latest_message.get('text', '').lower():
                                        if sport == "Football":
                                            home_score, away_score = score.split('-')
                                            home_score = int(home_score)
                                            away_score = int(away_score)
                                            
                                            if normalized_team in home_team_norm:
                                                if home_score > away_score:
                                                    win_status = f"Yes, {match['home_team']} won"
                                                elif home_score < away_score:
                                                    win_status = f"No, {match['home_team']} lost"
                                                else:
                                                    win_status = f"It was a draw"
                                            else:
                                                if away_score > home_score:
                                                    win_status = f"Yes, {match['away_team']} won"
                                                elif away_score < home_score:
                                                    win_status = f"No, {match['away_team']} lost"
                                                else:
                                                    win_status = f"It was a draw"
                                        else:  # Basketball
                                            home_score, away_score = map(int, score.split('-'))
                                            
                                            if normalized_team in home_team_norm:
                                                if home_score > away_score:
                                                    win_status = f"Yes, {match['home_team']} won"
                                                else:
                                                    win_status = f"No, {match['home_team']} lost"
                                            else:
                                                if away_score > home_score:
                                                    win_status = f"Yes, {match['away_team']} won"
                                                else:
                                                    win_status = f"No, {match['away_team']} lost"
                                    
                                    if win_status:
                                        response = f"{win_status}. {match['home_team']} vs {match['away_team']} ended {score} on {date}."
                                    else:
                                        response = f"{match['home_team']} vs {match['away_team']} ended {score} on {date}."
                                    
                                    # Add sport-specific information
                                    if sport == "Football":
                                        # Add goal scorers if available
                                        if scorers_key in match and match[scorers_key]:
                                            response += "\n\nGoal scorers:"
                                            for team_name, scorers in match[scorers_key].items():
                                                if scorers:
                                                    scorer_list = ", ".join(scorers)
                                                    response += f"\n{team_name}: {scorer_list}"
                                    else:  # Basketball
                                        quarters = match.get('quarters', [])
                                        if quarters:
                                            response += f"\nQuarter scores: {', '.join(quarters)}"
                                            
                                        # Add top scorers if available
                                        if scorers_key in match and match[scorers_key]:
                                            response += "\n\nTop scorers:"
                                            for team_name, scorers in match[scorers_key].items():
                                                if scorers:
                                                    for scorer in scorers[:3]:  # Show top 3 scorers
                                                        response += f"\n{team_name}: {scorer['name']} - {scorer['points']} pts"
                                    
                                    dispatcher.utter_message(text=response)
                                    return []

        team_list = ", ".join(teams)
        dispatcher.utter_message(text=f"No recent match results found for {team_list} in {sport}.")
        return []


class ActionGetGoalScorers(Action):
    def name(self):
        return "action_get_goal_scorers"

    def run(self, dispatcher, tracker, domain):
        # This action is football-specific
        sport = "Football"
        entities = tracker.latest_message.get('entities', [])
        team = None
        matchday = None
        player = None
        
        for entity in entities:
            if entity['entity'] == 'team':
                team = entity['value']
            elif entity['entity'] == 'matchday':
                matchday = entity['value']
            elif entity['entity'] == 'player':
                player = entity['value']
        
        # If no entities found, try to extract from message
        message = tracker.latest_message.get('text', '').lower()
        if not team and not matchday and not player:
            # Check for team mentions
            common_teams = ["barcelona", "real madrid", "liverpool", "manchester united", 
                          "arsenal", "chelsea", "atletico", "manchester city"]
            for common_team in common_teams:
                if common_team.lower() in message:
                    team = common_team
                    break
                    
            # Check for matchday mentions
            matchday_pattern = re.compile(r'matchday\s+(\d+)', re.IGNORECASE)
            match = matchday_pattern.search(message)
            if match:
                matchday_num = match.group(1)
                matchday = f"Matchday {matchday_num}"
                
            # Check for player mentions
            players = ["lewandowski", "salah", "haaland", "messi", "ronaldo", "benzema"]
            for p in players:
                if p in message:
                    player = p
                    break
        
        data = load_sports_data()
        sport_data = data.get(sport, {})
        
        # If player name is provided, search for that player's goals
        if player:
            player = player.lower().strip()
            found = False
            
            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict):
                    for matchday_name, matchday_data in league_data.items():
                        # Skip the standings entry
                        if matchday_name == "standings":
                            continue
                            
                        if isinstance(matchday_data, dict) and 'fixtures' in matchday_data:
                            for match in matchday_data['fixtures']:
                                if "goal_scorers" not in match:
                                    continue
                                    
                                for team_name, scorers in match["goal_scorers"].items():
                                    for scorer in scorers:
                                        if player in scorer.lower():
                                            response = f"{scorer} scored for {team_name} in the match {match['home_team']} vs {match['away_team']}."
                                            dispatcher.utter_message(text=response)
                                            found = True
                                            return []
            
            if not found:
                dispatcher.utter_message(text=f"Could not find any goals scored by {player}.")
                return []
        
        # If team name is provided directly or found in message, find their goal scorers
        if team:
            normalized_team = normalize_team_name(team)
            found = False

            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict):
                    for matchday_name, matchday_data in league_data.items():
                        # Skip the standings entry
                        if matchday_name == "standings":
                            continue
                            
                        if isinstance(matchday_data, dict) and 'fixtures' in matchday_data:
                            for match in matchday_data['fixtures']:
                                if "score" not in match or match["score"] == "Postponed":
                                    continue
                                
                                # Try different approaches to find the team
                                home_team_norm = normalize_team_name(match['home_team'])
                                away_team_norm = normalize_team_name(match['away_team'])
                                
                                if normalized_team in home_team_norm or normalized_team in away_team_norm:
                                    goal_scorers = match.get('goal_scorers', {})
                                    if goal_scorers:
                                        response = f"Goal scorers in {match['home_team']} vs {match['away_team']}:\n"
                                        for team_name, scorers in goal_scorers.items():
                                            if scorers:
                                                scorers_list = ', '.join(scorers)
                                                response += f"{team_name}: {scorers_list}\n"
                                        dispatcher.utter_message(text=response)
                                    else:
                                        dispatcher.utter_message(text=f"No goals scored in the match {match['home_team']} vs {match['away_team']}.")
                                    found = True
                                    return []

            if not found:
                dispatcher.utter_message(text=f"Couldn't find recent matches involving {team}.")
                return []
                
        # If matchday is provided without team, list all goal scorers for that matchday
        if matchday and not team:
            found = False
            matchday = matchday.strip()
            responses = []
            
            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict) and matchday in league_data:
                    fixtures = league_data[matchday].get("fixtures", [])
                    response = f"Goal scorers for {matchday} in {league_name}:\n"
                    has_scorers = False
                    
                    for match in fixtures:
                        if "goal_scorers" in match and match["goal_scorers"]:
                            has_scorers = True
                            response += f"\n{match['home_team']} vs {match['away_team']}:\n"
                            
                            for team_name, scorers in match["goal_scorers"].items():
                                if scorers:
                                    scorers_list = ', '.join(scorers)
                                    response += f"  {team_name}: {scorers_list}\n"
                    
                    if has_scorers:
                        responses.append(response)
                        found = True
            
            if found:
                # Send each league's goal scorers as a separate message
                for response in responses:
                    dispatcher.utter_message(text=response)
                return []
            else:
                dispatcher.utter_message(text=f"No goal scorer information found for {matchday}.")
                return []
        
        dispatcher.utter_message(text="Please specify a football team, player, or matchday to get goal scorer information.")
        return []


class ActionGetTopScorers(Action):
    def name(self):
        return "action_get_top_scorers"

    def run(self, dispatcher, tracker, domain):
        # This action is basketball-specific
        sport = "Basketball"
        entities = tracker.latest_message.get('entities', [])
        team = None
        matchday = None
        player = None
        
        for entity in entities:
            if entity['entity'] == 'team':
                team = entity['value']
            elif entity['entity'] == 'matchday':
                matchday = entity['value']
            elif entity['entity'] == 'player':
                player = entity['value']
        
        # If no entities found, try to extract from message
        message = tracker.latest_message.get('text', '').lower()
        if not team and not matchday and not player:
            # Check for team mentions
            common_teams = ["lakers", "los angeles", "celtics", "boston", "warriors", "bulls", "heat", "bucks", 
                          "phoenix suns", "nuggets", "mavericks", "nets"]
            for common_team in common_teams:
                if common_team.lower() in message:
                    team = common_team
                    break
                    
            # Check for week/round mentions for basketball
            week_pattern = re.compile(r'week\s+(\d+)', re.IGNORECASE)
            match = week_pattern.search(message)
            if match:
                week_num = match.group(1)
                matchday = f"Week {week_num}"
                
            round_pattern = re.compile(r'round\s+(\d+)', re.IGNORECASE)
            match = round_pattern.search(message)
            if match:
                round_num = match.group(1)
                matchday = f"Round {round_num}"
                
            # Check for player mentions
            players = ["lebron", "curry", "jokić", "antetokounmpo", "tatum"]
            for p in players:
                if p in message:
                    player = p
                    break
        
        data = load_sports_data()
        sport_data = data.get(sport, {})
        
        # If player name is provided, search for that player's scoring
        if player:
            player = player.lower().strip()
            found = False
            
            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict):
                    for matchday_name, matchday_data in league_data.items():
                        # Skip the standings entry
                        if matchday_name == "standings":
                            continue
                            
                        if isinstance(matchday_data, dict) and 'games' in matchday_data:
                            for game in matchday_data['games']:
                                if "top_scorers" not in game:
                                    continue
                                    
                                for team_name, scorers in game["top_scorers"].items():
                                    for scorer in scorers:
                                        if player in scorer['name'].lower():
                                            response = f"{scorer['name']} scored {scorer['points']} points for {team_name} in the game {game['home_team']} vs {game['away_team']}."
                                            dispatcher.utter_message(text=response)
                                            found = True
                                            return []
            
            if not found:
                dispatcher.utter_message(text=f"Could not find any points scored by {player}.")
                return []
        
        # If team name is provided directly or found in message, find their top scorers
        if team:
            normalized_team = normalize_team_name(team)
            found = False

            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict):
                    for matchday_name, matchday_data in league_data.items():
                        # Skip the standings entry
                        if matchday_name == "standings":
                            continue
                            
                        if isinstance(matchday_data, dict) and 'games' in matchday_data:
                            for game in matchday_data['games']:
                                if "score" not in game or game["score"] == "Postponed":
                                    continue
                                
                                # Try different approaches to find the team
                                home_team_norm = normalize_team_name(game['home_team'])
                                away_team_norm = normalize_team_name(game['away_team'])
                                
                                if normalized_team in home_team_norm or normalized_team in away_team_norm:
                                    top_scorers = game.get('top_scorers', {})
                                    if top_scorers:
                                        response = f"Top scorers in {game['home_team']} vs {game['away_team']}:\n"
                                        for team_name, scorers in top_scorers.items():
                                            if scorers:
                                                response += f"\n{team_name}:\n"
                                                for scorer in scorers:
                                                    response += f"  {scorer['name']}: {scorer['points']} points\n"
                                        dispatcher.utter_message(text=response)
                                    else:
                                        dispatcher.utter_message(text=f"No scoring information available for the game {game['home_team']} vs {game['away_team']}.")
                                    found = True
                                    return []

            if not found:
                dispatcher.utter_message(text=f"Couldn't find recent games involving {team}.")
                return []
                
        # If matchday is provided without team, list all top scorers for that matchday
        if matchday and not team:
            found = False
            matchday = matchday.strip()
            responses = []
            
            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict) and matchday in league_data:
                    games = league_data[matchday].get("games", [])
                    response = f"Top scorers for {matchday} in {league_name}:\n"
                    has_scorers = False
                    
                    for game in games:
                        if "top_scorers" in game and game["top_scorers"]:
                            has_scorers = True
                            response += f"\n{game['home_team']} vs {game['away_team']}:\n"
                            
                            for team_name, scorers in game["top_scorers"].items():
                                if scorers:
                                    response += f"  {team_name}:\n"
                                    for scorer in scorers[:3]:  # Show top 3 scorers
                                        response += f"    {scorer['name']}: {scorer['points']} points\n"
                    
                    if has_scorers:
                        responses.append(response)
                        found = True
            
            if found:
                # Send each league's top scorers as a separate message
                for response in responses:
                    dispatcher.utter_message(text=response)
                return []
            else:
                dispatcher.utter_message(text=f"No scoring information found for {matchday}.")
                return []
        
        dispatcher.utter_message(text="Please specify a basketball team, player, or matchday to get scoring information.")
        return []

class ActionGetStadium(Action):
    def name(self):
        return "action_get_stadium"

    def run(self, dispatcher, tracker, domain):
        sport = determine_sport(tracker)
        entities = tracker.latest_message.get('entities', [])
        team = None
        matchday = None
        
        for entity in entities:
            if entity['entity'] == 'team':
                team = entity['value']
            elif entity['entity'] == 'matchday':
                matchday = entity['value']
        
        # If no entities found, try to extract from message text
        message = tracker.latest_message.get('text', '').lower()
        
        # Try to detect sport more specifically from message context if needed
        if "basketball" in message or "nba" in message or "arena" in message:
            sport = "Basketball"
        elif "football" in message or "soccer" in message or "stadium" in message:
            sport = "Football"
            
        # Explicit handling for problem cases
        if "boston celtics" in message or "celtics" in message:
            team = "celtics"
            sport = "Basketball"
        elif "lakers" in message or "los angeles lakers" in message:
            team = "lakers"
            sport = "Basketball"
        
        if not team and not matchday:
            # Check for team mentions based on sport context
            common_teams = []
            if sport == "Football":
                common_teams = ["barcelona", "real madrid", "liverpool", "manchester united", 
                              "arsenal", "chelsea", "atletico", "manchester city"]
            else:  # Basketball
                common_teams = ["lakers", "los angeles", "celtics", "boston", "warriors", "bulls", "heat", "bucks"]
                
            for common_team in common_teams:
                if common_team.lower() in message:
                    team = common_team
                    break
                    
            # Check for matchday mentions using patterns appropriate for the sport
            if sport == "Football":
                matchday_pattern = re.compile(r'matchday\s+(\d+)', re.IGNORECASE)
                match = matchday_pattern.search(message)
                if match:
                    matchday_num = match.group(1)
                    matchday = f"Matchday {matchday_num}"
            else:  # Basketball
                week_pattern = re.compile(r'week\s+(\d+)', re.IGNORECASE)
                match = week_pattern.search(message)
                if match:
                    week_num = match.group(1)
                    matchday = f"Week {week_num}"
                    
                round_pattern = re.compile(r'round\s+(\d+)', re.IGNORECASE)
                match = round_pattern.search(message)
                if match:
                    round_num = match.group(1)
                    matchday = f"Round {round_num}"
            
        if not team and not matchday:
            if sport == "Football":
                dispatcher.utter_message(text="Please specify either a team or matchday to get stadium information.")
            else:  # Basketball
                dispatcher.utter_message(text="Please specify either a team or matchday to get arena information.")
            return []
            
        data = load_sports_data()
        sport_data = data.get(sport, {})
        
        # Use appropriate terminology and fields based on the sport
        venue_type = "stadium" if sport == "Football" else "arena"
        fixtures_key = "fixtures" if sport == "Football" else "games"
        
        # If a matchday is provided and the query is about venues, show all venues for that matchday
        if matchday:
            matchday = matchday.strip()
            responses = []
            leagues_with_data = []
            
            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict) and matchday in league_data:
                    leagues_with_data.append(league_name)
                    matches = league_data[matchday].get(fixtures_key, [])
                    
                    if matches:
                        if sport == "Football":
                            response = f"Stadium information for {matchday} in {league_name}:\n"
                        else:  # Basketball
                            response = f"Arena information for {matchday} in {league_name}:\n"
                            
                        for match in matches:
                            venue = match.get(venue_type, "Unknown venue")
                            location = match.get("city", match.get("state", ""))
                            
                            match_info = f"{match['home_team']} vs {match['away_team']} at {venue}"
                            if location:
                                match_info += f", {location}"
                            
                            response += match_info + "\n"
                        
                        responses.append(response)
            
            if responses:
                # First explain which leagues have data for this matchday
                if len(leagues_with_data) < len(sport_data):
                    missing_leagues = [name for name in sport_data.keys() if name not in leagues_with_data]
                    if missing_leagues:
                        dispatcher.utter_message(text=f"Note: {matchday} information is only available for {', '.join(leagues_with_data)}. No data for {', '.join(missing_leagues)}.")
                
                # Then send each league's venue info as a separate message
                for response in responses:
                    dispatcher.utter_message(text=response)
                return []
            else:
                if sport == "Football":
                    dispatcher.utter_message(text=f"No stadium information found for {matchday} in any football league.")
                else:  # Basketball
                    dispatcher.utter_message(text=f"No arena information found for {matchday} in any basketball league.")
                return []
        
        # If a team is provided, find their home venue
        if team:
            normalized_team = normalize_team_name(team)
            
            # First look for home venue in matches where this team is the home team
            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict):
                    for matchday_name, matchday_data in league_data.items():
                        # Skip the standings entry
                        if matchday_name == "standings":
                            continue
                            
                        if isinstance(matchday_data, dict) and fixtures_key in matchday_data:
                            for match in matchday_data[fixtures_key]:
                                home_team = normalize_team_name(match.get("home_team", ""))
                                
                                # matching logic
                                if normalized_team == home_team or normalized_team in home_team or home_team in normalized_team:
                                    venue = match.get(venue_type, "Unknown venue")
                                    location = match.get("city", match.get("state", ""))
                                    
                                    if sport == "Football":
                                        response = f"{match['home_team']} plays their home games at {venue}"
                                    else:  # Basketball
                                        response = f"{match['home_team']} plays their home games at {venue}"
                                        
                                    if location:
                                        response += f" in {location}"
                                    response += "."
                                    
                                    # Add next match info if available and this is a future match
                                    if is_upcoming_match(match):  # Not played yet
                                        response += f"\n\nTheir next home match is against {match['away_team']} on {match['date']}"
                                        if "time" in match:
                                            response += f" at {match['time']}"
                                        response += "."
                                    
                                    dispatcher.utter_message(text=response)
                                    return []
            
            # If not found as home team, check if they play away soon
            for league_name, league_data in sport_data.items():
                if isinstance(league_data, dict):
                    for matchday_name, matchday_data in league_data.items():
                        # Skip the standings entry
                        if matchday_name == "standings":
                            continue
                            
                        if isinstance(matchday_data, dict) and fixtures_key in matchday_data:
                            for match in matchday_data[fixtures_key]:
                                if not is_upcoming_match(match):
                                    continue  # Skip already played matches
                                
                                away_team = normalize_team_name(match.get("away_team", ""))
                                
                                # Improved matching logic
                                if normalized_team == away_team or normalized_team in away_team or away_team in normalized_team:
                                    venue = match.get(venue_type, "Unknown venue")
                                    location = match.get("city", match.get("state", ""))
                                    
                                    if sport == "Football":
                                        response = f"{match['away_team']}'s next away match is against {match['home_team']} at {venue}"
                                    else:  # Basketball
                                        response = f"{match['away_team']}'s next away game is against {match['home_team']} at {venue}"
                                        
                                    if location:
                                        response += f" in {location}"
                                    response += f" on {match['date']}"
                                    if "time" in match:
                                        response += f" at {match['time']}"
                                    response += "."
                                    
                                    dispatcher.utter_message(text=response)
                                    return []
            
            # Special handling for basketball teams that may not have current matches
            if sport == "Basketball":
                # Hardcoded arenas for common teams that might be missing in the fixtures
                arena_info = {
                    "lakers": {"arena": "Crypto.com Arena", "location": "Los Angeles, California"},
                    "celtics": {"arena": "TD Garden", "location": "Boston, Massachusetts"},
                    "warriors": {"arena": "Chase Center", "location": "San Francisco, California"},
                    "heat": {"arena": "Kaseya Center", "location": "Miami, Florida"},
                    "bulls": {"arena": "United Center", "location": "Chicago, Illinois"},
                    "knicks": {"arena": "Madison Square Garden", "location": "New York, New York"}
                }
                
                if normalized_team in arena_info:
                    arena_data = arena_info[normalized_team]
                    team_display = normalized_team.capitalize()
                    if normalized_team == "lakers":
                        team_display = "Los Angeles Lakers"
                    elif normalized_team == "celtics":
                        team_display = "Boston Celtics"
                    elif normalized_team == "warriors":
                        team_display = "Golden State Warriors"
                    
                    response = f"{team_display} plays their home games at {arena_data['arena']} in {arena_data['location']}."
                    dispatcher.utter_message(text=response)
                    return []
            
            if sport == "Football":
                dispatcher.utter_message(text=f"I couldn't find stadium information for {team}.")
            else:  # Basketball
                dispatcher.utter_message(text=f"I couldn't find arena information for {team}.")
            return []
        
        if sport == "Football":
            dispatcher.utter_message(text="I couldn't find any stadium information for your request.")
        else:  # Basketball
            dispatcher.utter_message(text="I couldn't find any arena information for your request.")
        return []