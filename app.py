import os
import itertools
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__, template_folder='.')

try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
except AttributeError:
    print("API Key not found. Please set the GOOGLE_API_KEY environment variable.")
    exit()

model = genai.GenerativeModel('gemini-1.5-flash')

LOADING_TIPS = itertools.cycle([
    "Pro Tip: Roll your clothes to save space in your luggage...",
    "Did you know? Booking flights on a Tuesday can sometimes be cheaper...",
    "Remember to download offline maps of your destination...",
    "Learning a few basic phrases in the local language goes a long way...",
])

@app.route('/loading_text')
def loading_text():
    return jsonify(tip=next(LOADING_TIPS))

@app.route('/suggest_destinations', methods=['POST'])
def suggest_destinations():
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify([])

    prompt = (f"List 5 popular and real travel destinations (cities or famous regions) that start with the letters '{query}'. "
              f"Return ONLY a comma-separated list. For example: Paris France, Parma Italy, Paro Bhutan.")
    
    try:
        response = model.generate_content(prompt)
        suggestions = ''.join(part.text for part in response.parts).strip()
        destination_list = [dest.strip() for dest in suggestions.split(',') if dest.strip()]
        return jsonify(destination_list)
    except Exception as e:
        print(f"Error suggesting destinations: {e}")
        return jsonify([])

CURRENCY_RATES_TO_USD = {
    "USD": 1.0, "INR": 83.5, "EUR": 0.92, "GBP": 0.79, "JPY": 157.0, "AUD": 1.5, "CAD": 1.37
}

def get_llm_response(prompt):
    try:
        response = model.generate_content(prompt)
        return ''.join(part.text for part in response.parts)
    except Exception as e:
        print(f"An error occurred with the Gemini API: {e}")
        return "An error occurred while generating the response."

def generate_google_maps_link(city, locations):
    if not locations: return ""
    base_url = "https://www.google.com/maps/dir/"
    encoded_locations = [f"{loc.replace(' ', '+')},{city.replace(' ', '+')}" for loc in locations]
    return base_url + "/".join(encoded_locations)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    city = request.form['destination']
    budget_original = float(request.form['budget'])
    currency = request.form['currency']
    days = request.form['days']
    
    conversion_rate = CURRENCY_RATES_TO_USD.get(currency, 1.0)
    budget_usd = round(budget_original / conversion_rate)

    prompt1 = (f"Generate a high-level travel plan for a {days}-day trip to {city}. "
               f"The user's budget is {budget_original} {currency} (~${budget_usd} USD). "
               f"Include a captivating one-paragraph summary and a list of 3-4 key attractions.")
    high_level_plan = get_llm_response(prompt1)
    
    prompt2 = (f"Based on this plan, create a detailed day-by-day itinerary. "
               f"IMPORTANT: For each day, start with a bold heading like '**Day 1: [Theme]**'. Follow this strictly.")
    daily_itinerary = get_llm_response(prompt2)
    
    prompt3 = f"Based on the itinerary, recommend budget-friendly dining options (breakfast, lunch, dinner)."
    dining_recommendations = get_llm_response(prompt3)
    
    prompt5_packing = f"Generate a smart packing list for a {days}-day trip to {city}. Format it as a simple bulleted list."
    packing_list = get_llm_response(prompt5_packing)
    
    prompt6_fact = f"Tell me one surprising or fun fact about {city}. Start directly with the fact, no preamble."
    fun_fact = get_llm_response(prompt6_fact)
    
    prompt4_locations = f"From the itinerary, extract only key place names (attractions, restaurants) and list them separated by '|'."
    locations_string = get_llm_response(prompt4_locations)
    locations_list = [loc.strip() for loc in locations_string.split('|') if loc.strip()]
    
    maps_link = generate_google_maps_link(city, locations_list)
    
    return jsonify({
        'high_level_plan': high_level_plan,
        'daily_itinerary': daily_itinerary,
        'dining_recommendations': dining_recommendations,
        'maps_link': maps_link,
        'packing_list': packing_list,
        'fun_fact': fun_fact
    })

if __name__ == '__main__':
    app.run(debug=True)
