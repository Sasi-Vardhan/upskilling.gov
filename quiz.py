from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, abort
import csv
import os
import logging
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed
from gtts import gTTS
import io
import uuid

quiz_bp = Blueprint('quiz', __name__, template_folder='templates')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Global in-memory cache ---
quiz_cache = {}

# Skill and language setup
SKILL_NAMES = {
    'poultry': 'Poultry Farming',
    'mushroom': 'Mushroom Cultivation',
    'mobile_repair': 'Mobile Repair'
}
csv_files = {
    'poultry': 'data/poultry_quiz.csv',
    'mushroom': 'data/mushroom_quiz.csv',
    'mobile_repair': 'data/mobile_repair_quiz.csv'
}
LANGUAGES = {
    'english': {'code': 'en', 'name': 'English', 'native': 'English'},
    'hindi': {'code': 'hi', 'name': 'Hindi', 'native': 'हिंदी'},
    'tamil': {'code': 'ta', 'name': 'Tamil', 'native': 'தமிழ்'},
    'telugu': {'code': 'te', 'name': 'Telugu', 'native': 'తెలుగు'}
}

@quiz_bp.before_request
def clear_session_on_navigation():
    exempt = {'quiz.quiz', 'quiz.speak', 'static', 'forms.reg'}
    if request.endpoint not in exempt:
        session.clear()
        logger.info("Session cleared on route change.")

def translate_field(field, text, lang):
    try:
        if text and lang != 'en':
            return field, GoogleTranslator(source='en', target=lang).translate(text)
        return field, text
    except Exception as e:
        logger.error(f"Translation error on {field}: {e}")
        return field, text

def translator(questions, lang_code):
    translated = []
    fields = ['question', 'option1', 'option2', 'option3', 'option4', 'correct_answer', 'explanation']
    for q in questions:
        t_data = q.copy()
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(translate_field, f, q[f], lang_code) for f in fields if f in q]
            for future in as_completed(futures):
                f, t = future.result()
                t_data[f] = t
        translated.append(t_data)
    return translated

def load_quiz_data(skill, lang_code):
    if skill not in csv_files:
        return []

    path = csv_files[skill]
    if not os.path.exists(path):
        return []

    questions = []
    try:
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                opts = row['Options'].split(';')
                if len(opts) != 4:
                    continue
                questions.append({
                    'question': row['Question'].strip(),
                    'option1': opts[0].strip(),
                    'option2': opts[1].strip(),
                    'option3': opts[2].strip(),
                    'option4': opts[3].strip(),
                    'correct_answer': row['Correct Answer'].strip(),
                    'explanation': row['Explanation Why Correct Answer is Good'].strip()
                })
    except Exception as e:
        logger.error(f"CSV load error: {e}")
        return []

    return translator(questions, lang_code) if lang_code != 'en' else questions

@quiz_bp.route('/quiz', methods=['GET', 'POST'])
def quiz():
    # Ensure session has necessary info
    if 'selected_skill' not in session or session['selected_skill'] not in SKILL_NAMES:
        return redirect(url_for('index'))

    skill = session['selected_skill']
    lang = LANGUAGES.get(session.get('language', 'english'), {'code': 'en'})['code']

    # Load quiz into memory/cache
    if 'quiz_id' not in session:
        questions = load_quiz_data(skill, lang)
        if not questions:
            return render_template('error.html', message="Quiz not found.")
        quiz_id = str(uuid.uuid4())
        quiz_cache[quiz_id] = questions
        session['quiz_id'] = quiz_id
        session['current_question'] = 0
        session['score'] = 0
        session['answered'] = False
        session['feedback'] = ''
        session['correct_answer'] = ''
        session['explanation'] = ''
        session.modified = True
    else:
        questions = quiz_cache.get(session['quiz_id'], [])

    index = session['current_question']
    total = len(questions)

    if request.method == 'POST':
        action = request.form.get('submit_type')
        logger.info(f"Submit type: {action}, Current Q: {index}")

        if action == 'submit':
            user_answer = request.form.get('answer', '').strip()
            correct = questions[index]['correct_answer']
            session['answered'] = True
            session['feedback'] = 'Correct!' if user_answer == correct else 'Incorrect!'
            if user_answer == correct:
                session['score'] += 1
            session['correct_answer'] = correct
            session['explanation'] = questions[index]['explanation']

        elif action == 'next':
            session['current_question'] += 1
            if session['current_question'] >= total:
                final_score = session['score']
                # session.clear()
                return redirect(url_for('forms.reg'))
            # reset for next
            session['answered'] = False
            session['feedback'] = ''
            session['correct_answer'] = ''
            session['explanation'] = ''

        session.modified = True
        return redirect(url_for('quiz.quiz'))

    # Render current question
    if index < total:
        q_data = questions[index]
        return render_template(
            'quiz.html',
            question=q_data,
            question_number=index + 1,
            total_questions=total,
            skill_name=SKILL_NAMES[skill],
            answered=session['answered'],
            feedback=session['feedback'],
            correct_answer=session['correct_answer'],
            explanation=session['explanation'],
            language=session.get("language", "english")
        )

    return redirect(url_for('forms.reg'))

@quiz_bp.route('/speak', methods=['GET'])
def speak():
    text = request.args.get('text')
    lang = LANGUAGES.get(request.args.get('lang', 'english'), {'code': 'en'})['code']
    try:
        audio = io.BytesIO()
        gTTS(text=text, lang=lang).write_to_fp(audio)
        audio.seek(0)
        return send_file(audio, mimetype='audio/mpeg')
    except Exception as e:
        return abort(500, f"TTS failed: {e}")

@quiz_bp.route('/index')
def index():
    session.clear()
    return render_template('index.html', skills=SKILL_NAMES)
