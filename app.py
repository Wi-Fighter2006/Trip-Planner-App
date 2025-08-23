# app.py

import os
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__, template_folder='.')

# It is recommended to set the API key as an environment variable for security.
# In your terminal, run: export GOOGLE_API_KEY='your_api_key_here'
try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
except AttributeError:
    print("API Key not found. Please set the GOOGLE_API_KEY environment variable.")
    exit()

# Create the model
model = genai.GenerativeModel('gemini-1.5-flash')

# Approximate conversion rates to 1 USD.
# In a real-world application, you would use a live API for this.
CURRENCY_RATES_TO_USD = {
    "USD": 1.0,
    "INR": 83.5,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 157.0,
    "AUD": 1.5,
    "CAD": 1.37,
}

def get_llm_response(prompt):
    """Sends a prompt to the Gemini API and returns the response."""
    try:
        response = model.generate_content(prompt)
        return ''.join(part.text for part in response.parts)
    except Exception as e:
        print(f"An error occurred with the Gemini API: {e}")
        return "Sorry, I couldn't process your request at the moment. Please try again later."

def generate_google_maps_link(city, locations):
    """Generates a Google Maps link with the specified locations."""
    if not locations:
        return ""
    base_url = "https://www.google.com/maps/dir/"
    encoded_locations = [f"{loc.replace(' ', '+')},{city.replace(' ', '+')}" for loc in locations]
    return base_url + "/".join(encoded_locations)

@app.route('/')
def index():
    """Renders the main page."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Handles the form submission and generates the itinerary."""
    city = request.form['city']
    budget_original = float(request.form['budget'])
    currency = request.form['currency']
    days = request.form['days']

    # Convert the budget to USD for the LLM
    conversion_rate = CURRENCY_RATES_TO_USD.get(currency, 1.0)
    budget_usd = round(budget_original / conversion_rate)

    # --- Prompt Chaining ---
    prompt1 = (f"Generate a high-level travel plan for a {days}-day trip to {city}. "
               f"The user's budget is approximately {budget_original} {currency} (which is about ${budget_usd} USD). "
               f"Keep this budget in mind for all recommendations. Include a brief summary and a list of key attractions.")
    high_level_plan = get_llm_response(prompt1)

    prompt2 = (f"Based on this high-level plan, create a detailed day-by-day itinerary. "
               f"IMPORTANT: For each day, you must start the line with a bold heading like '**Day 1: [Theme of the Day]**'. "
               f"Follow this format strictly for every day. High-level plan: {high_level_plan}")
    daily_itinerary = get_llm_response(prompt2)

    prompt3 = f"Based on this itinerary, recommend budget-friendly dining options (breakfast, lunch, dinner) near the locations mentioned: {daily_itinerary}"
    dining_recommendations = get_llm_response(prompt3)

    prompt4 = f"From the following itinerary, extract only the key place names (attractions, restaurants) and list them separated by '|'. Do not add any other text or explanation. Itinerary: {daily_itinerary} and {dining_recommendations}"
    locations_string = get_llm_response(prompt4)
    locations_list = [loc.strip() for loc in locations_string.split('|') if loc.strip()]
    
    maps_link = generate_google_maps_link(city, locations_list)
    
    return jsonify({
        'high_level_plan': high_level_plan,
        'daily_itinerary': daily_itinerary,
        'dining_recommendations': dining_recommendations,
        'maps_link': maps_link
    })

if __name__ == '__main__':
    app.run(debug=True)
