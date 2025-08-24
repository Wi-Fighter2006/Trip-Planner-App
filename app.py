import os
import itertools
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

# Use the 'index.html' from the same directory
app = Flask(__name__, template_folder='.')  

# --- API Key Configuration ---
try:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API Key not found. Please set the GOOGLE_API_KEY environment variable.")
    genai.configure(api_key=api_key)
except (ValueError, AttributeError) as e:
    print(f"Error configuring API: {e}")
    exit()

# --- Model Initialization ---
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Loading Tips for Frontend ---
LOADING_TIPS = itertools.cycle([
    "Pro Tip: Roll your clothes to save space in your luggage...",
    "Did you know? Booking flights on a Tuesday can sometimes be cheaper...",
    "Remember to download offline maps of your destination...",
    "Learning a few basic phrases in the local language goes a long way...",
    "Don't forget to inform your bank about your travel plans...",
    "Packing a portable charger can be a lifesaver...",
    "Always leave a little extra room in your suitcase for souvenirs..."
])

@app.route('/loading_text')
def loading_text():
    """Provides a new loading tip for the frontend."""
    return jsonify(tip=next(LOADING_TIPS))

# --- Currency Data ---
CURRENCY_RATES_TO_USD = {
    "USD": 1.0, "INR": 83.5, "EUR": 0.92, "GBP": 0.79
}

# --- Helper Functions ---
def get_llm_response(prompt):
    """Sends a prompt to the Gemini model and returns the text response."""
    try:
        response = model.generate_content(prompt)
        if not response.parts:
            return "I'm sorry, I couldn't generate a response for that. Please try again."
        return response.text
    except Exception as e:
        print(f"An error occurred with the Gemini API: {e}")
        return "An error occurred while generating the response. Please check the server logs."

def generate_google_maps_link(city, locations):
    """Creates a Google Maps directions URL from a list of locations."""
    if not locations:
        return ""
    base_url = "https://www.google.com/maps/dir/"
    encoded_locations = [f"{loc.replace(' ', '+')},{city.replace(' ', '+')}" for loc in locations]
    return base_url + "/".join(encoded_locations)

# --- Flask Routes ---
@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Handles the form submission and generates the trip plan."""
    try:
        # --- Read all form data, including new fields ---
        city = request.form.get('city')
        budget_original = float(request.form.get('budget', 0))
        currency = request.form.get('currency', 'USD')
        days = int(request.form.get('days', '1'))
        males = int(request.form.get('males', '0'))
        females = int(request.form.get('females', '0'))
        journey_date = request.form.get('journey-date')
        trip_type = request.form.get('trip-type', 'domestic')
        notes = request.form.get('notes', '').strip()

        total_people = males + females

    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid input. Please check that budget, days, and traveler numbers are valid numbers.'}), 400

    # --- Validation for all fields ---
    if not city or budget_original <= 0 or days <= 0 or total_people <= 0 or not journey_date:
        return jsonify({'error': 'Please fill out all required fields: city, budget, dates, and number of travelers.'}), 400

    # --- Currency conversion ---
    conversion_rate = CURRENCY_RATES_TO_USD.get(currency, 1.0)
    budget_usd = round(budget_original / conversion_rate)

    # --- Construct a detailed prompt context for the AI ---
    prompt_context = (
        f"The trip is a {trip_type} journey to {city} for {days} days, starting around {journey_date}. "
        f"The group consists of {total_people} people ({males} male(s) and {females} female(s)). "
        f"Their total budget is {budget_original} {currency}. "
    )
    if notes:
        prompt_context += f"The user has provided the following specific requests: '{notes}'. Please try to incorporate these."

    # --- Generate different parts of the itinerary using the AI ---
    high_level_plan = get_llm_response(
        f"Generate a high-level, exciting travel plan summary for the following trip: {prompt_context} "
        f"IMPORTANT: All cost estimations and monetary values in your response MUST be in {currency}. "
        "Write a captivating one-paragraph summary. Then, list 3-4 key attractions suitable for the group."
    )

    daily_itinerary = get_llm_response(
        f"Based on this plan: '{high_level_plan}', create a detailed day-by-day itinerary. "
        f"Here are the trip details: {prompt_context} "
        f"IMPORTANT: Frame all budget advice and cost mentions in {currency}. "
        "For each day, start with a bolded heading like '**Day 1: Arrival and Exploration**'. "
        "Then, detail the plan for Morning, Afternoon, and Evening, considering the group's composition and the travel date for seasonal relevance."
    )

    dining_recommendations = get_llm_response(
        f"Based on an itinerary for a trip to {city}, recommend dining options. "
        f"The trip details are: {prompt_context} "
        "Include one budget-friendly, one mid-range, and one local favorite spot. "
        f"Briefly describe why each is suitable and provide a general price range in {currency}."
    )

    packing_list = get_llm_response(
        f"Generate a smart, bulleted packing list for this trip: {prompt_context} "
        "Consider the destination's climate around the travel date and common activities there."
    )

    fun_fact = get_llm_response(
        f"Tell me one surprising and fun fact about {city}. Start directly with the fact, no preamble."
    )
    
    locations_string = get_llm_response(
        f"From this itinerary: '{daily_itinerary}', extract up to 8 key place names (attractions, specific restaurants). "
        "Do not explain. Just give the names separated only by a vertical bar '|'. Example: Eiffel Tower|Louvre Museum|Seine River Cruise"
    )
    locations_list = [loc.strip() for loc in locations_string.split('|') if loc.strip()]
    maps_link = generate_google_maps_link(city, locations_list)

    # --- Return the complete data to the frontend ---
    return jsonify({
        'high_level_plan': high_level_plan,
        'daily_itinerary': daily_itinerary,
        'dining_recommendations': dining_recommendations,
        'packing_list': packing_list,
        'fun_fact': fun_fact,
        'maps_link': maps_link
    })

if __name__ == '__main__':
    app.run(debug=True)
