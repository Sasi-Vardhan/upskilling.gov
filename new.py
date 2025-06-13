from flask import Flask, render_template, request, session, redirect, url_for
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint
from select_skill import select_skills_bp  # ✅ import the skills blueprint
from quiz import quiz_bp
from reg import forms
from flask import send_from_directory

app = Flask(__name__)
app.secret_key = 'rural_income_portal_2024'
app.register_blueprint(select_skills_bp, url_prefix='/skills')
app.register_blueprint(quiz_bp)
app.register_blueprint(forms)

# Language mapping
LANGUAGES = {
    'english': {'code': 'en', 'name': 'English', 'native': 'English'},
    'hindi': {'code': 'hi', 'name': 'Hindi', 'native': 'हिंदी'},
    'tamil': {'code': 'ta', 'name': 'Tamil', 'native': 'தமிழ்'},
    'telugu': {'code': 'te', 'name': 'Telugu', 'native': 'తెలుగు'}
}

# Content dictionary with new entries for Government Initiatives section
CONTENT = {
    'page_title': 'Helping People to Raise their Income Levels',
    'govt_subtitle': 'Government of India Initiative',
    'select_language': 'Select Language',
    'farmer_title': 'Farmer',
    'farmer_description': 'Access agricultural schemes, crop insurance, direct benefit transfers, and modern farming techniques to increase your agricultural income and productivity.',
    'housewife_title': 'House Wife',
    'housewife_description': 'Join Self Help Groups, start micro-enterprises, access credit facilities, and learn skill development programs to achieve financial independence.',
    'village_youth_title': 'Village Youth',
    'village_youth_description': 'Explore employment opportunities, skill development programs, entrepreneurship support, and digital literacy initiatives for better career prospects.',
    'learn_more': 'Learn More',
    'get_started': 'Get Started',
    'available_schemes': 'Available Schemes',
    'footer_text': 'Empowering Rural India Through Digital Innovation',
    # New content for Government Initiatives section
    'gov_initiatives_title': 'Empowering Rural India',
    'gov_initiatives_description': 'The Government of India is committed to uplifting rural communities through skill development and income generation programs. Initiatives like Skill India and Pradhan Mantri Kaushal Vikas Yojana (PMKVY) provide training in various trades, enabling farmers, housewives, and village youth to earn sustainable livelihoods. Increasing income through skill development not only improves quality of life but also contributes to the nation\'s economic growth. Join us to build a stronger, self-reliant India!'
}

def translate_text(text, target_lang_code):
    """Translate text using GoogleTranslator."""
    if target_lang_code == 'en':
        return text
    try:
        return GoogleTranslator(source='en', target=target_lang_code).translate(text)
    except Exception as e:
        print(f"Translation failed: {text} - {e}")
        return text

def parallel_translate(text_dict, lang_code):
    """Translate a dict of text values in parallel"""
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(translate_text, v, lang_code): k for k, v in text_dict.items()}
        results = {}
        for future in as_completed(futures):
            k = futures[future]
            results[k] = future.result()
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    # session.clear()
    sdict = dict(session)
    for key, value in sdict.items():
        if key != 'L' and key != 'language' and key != 'category':
            session.pop(key)
    if request.method == "POST":
        user_type = request.form.get("user_type", "none")
        session["category"] = user_type
        return redirect(url_for('select_skills.show_skills'))
    selected_lang = session.get('language', 'english')
    print(selected_lang)
    lang_code = LANGUAGES[selected_lang]['code']

    translated_content = parallel_translate(CONTENT, lang_code)

    return render_template('index.html',
                           content=translated_content,
                           languages=LANGUAGES,
                           current_lang=selected_lang)

@app.route('/set_language/<language>')
def set_language(language):
    if language in LANGUAGES:
        session['language'] = language
        session["L"] = language
        print(language)
    return redirect(url_for('index'))

@app.route('/favicon.png')
def favicon():
    return url_for('static', filename='images/favicon.png')



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
