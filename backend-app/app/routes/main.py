import os
import datetime
import json
from flask import request, redirect, url_for, flash, jsonify, abort, send_from_directory, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from openpyxl import Workbook
from app.extensions import db
from app.models import User, Attendance, PendingCard, FeeTransaction, Book, DisciplineCase, SchoolMessage, Grade, TimetableEntry, Setting
from app.utils.constants import *
from app.utils.decorators import role_required
from app.utils.helpers import get_setting, set_setting, attendance_for_student
from app.utils.rendering import page

def school_logo():
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    configured_filename = get_setting("school_logo", "").strip()
    if configured_filename:
        # Logo settings are filenames, never paths. Keep legacy/custom uploads
        # working while preventing a stale or malformed setting from breaking
        # the bundled school logo fallback.
        filename = secure_filename(os.path.basename(configured_filename))
        if filename and os.path.isfile(os.path.join(upload_folder, filename)):
            return send_from_directory(upload_folder, filename)

    # The school's bundled crest lives in app/static/images. The former
    # default (logo.png) does not exist, which caused /school-logo to return
    # 404 on a fresh database or when a previously uploaded logo was removed.
    fallback_filename = "school_logo.jpg"
    if os.path.isfile(os.path.join(upload_folder, fallback_filename)):
        return send_from_directory(upload_folder, fallback_filename)
    abort(404)

def home():
    body = """<div class="home-page">
<section class="home-hero" id="home" aria-labelledby="home-heading">
<header class="home-nav">
<a class="home-brand" href="/" aria-label="Lycée de Muhura home"><img src="{{ school_logo_url }}" alt=""><span><strong>LYCÉE DE MUHURA</strong><small>LYCÉE SAINT ALEXANDRE SAULI</small></span></a>
<nav class="home-nav-links" aria-label="School navigation"><a href="#school">Our school</a><a href="#learning">Learning</a><a href="#services">School life</a></nav>
<div class="home-nav-actions"><a class="home-nav-login" href="/login">Log in</a><a class="home-nav-register" href="/register">Parent access <i class="bi bi-arrow-up-right" aria-hidden="true"></i></a></div>
</header>
<div class="home-hero-content">
<div class="home-copy"><span class="home-eyebrow">EXCELLENCE · DISCIPLINE · INTEGRITY · INNOVATION</span><h1 id="home-heading">Welcome to <span>Lycée de Muhura.</span></h1>{% if school_motto %}<p class="home-motto">“{{ school_motto }}”</p>{% endif %}<p class="home-description">Empowering students through RFID attendance, transparent school services, meaningful learning, and connected families.</p><div class="home-hero-actions"><a class="home-primary-action" href="/login">Sign in to the portal <i class="bi bi-arrow-right" aria-hidden="true"></i></a><a class="home-secondary-action" href="#services">Discover school life</a></div></div>
<aside class="home-glass-panel" aria-label="Animated school-day overview">
<p class="visually-hidden">This decorative preview cycles through a school-day overview, its progress, and a completed summary.</p>
<div class="home-demo-stage" aria-hidden="true">
<section class="home-demo-scene home-demo-create">
<div class="home-glass-heading"><span class="home-glass-icon"><i class="bi bi-calendar2-plus" aria-hidden="true"></i></span><div><strong>Plan the school day</strong><span>Keep the essentials together</span></div></div>
<div class="home-demo-tags"><span><i class="bi bi-calendar-check" aria-hidden="true"></i> Attendance</span><span><i class="bi bi-journal-text" aria-hidden="true"></i> Timetable</span><span class="home-demo-add">+</span></div>
<div class="home-demo-prompt">Bring today's school activity into one clear overview.</div>
<div class="home-demo-action"><span>Prepare overview</span><i class="bi bi-arrow-up-right" aria-hidden="true"></i></div>
</section>
<section class="home-demo-scene home-demo-progress">
<div class="home-glass-heading"><span class="home-glass-icon"><i class="bi bi-stars" aria-hidden="true"></i></span><div><strong>Updating school overview</strong><span>Checking today's activity</span></div></div>
<ul class="home-demo-list"><li><i class="bi bi-check-circle-fill"></i><span>Attendance records</span><span>Complete</span></li><li><i class="bi bi-arrow-repeat"></i><span>Class timetable</span><span>Updating</span></li><li><i class="bi bi-circle"></i><span>Family notices</span><span>Waiting</span></li><li><i class="bi bi-circle"></i><span>School services</span><span>Waiting</span></li></ul>
</section>
<section class="home-demo-scene home-demo-complete">
<div class="home-glass-heading"><span class="home-glass-icon"><i class="bi bi-check-lg" aria-hidden="true"></i></span><div><strong>School overview ready</strong><span>Today's essentials, together</span></div></div>
<ul class="home-demo-list"><li><i class="bi bi-check-circle-fill"></i><span>Attendance records</span><span>Ready</span></li><li><i class="bi bi-check-circle-fill"></i><span>Class timetable</span><span>Ready</span></li><li><i class="bi bi-check-circle-fill"></i><span>Family notices</span><span>Ready</span></li><li><i class="bi bi-check-circle-fill"></i><span>School services</span><span>Ready</span></li></ul>
</section>
</div>
</aside>
</div>
<a class="home-scroll-cue" href="#school"><span>Discover Lycée de Muhura</span><i class="bi bi-arrow-down" aria-hidden="true"></i></a>
</section>
<section class="home-services" id="services" aria-labelledby="services-heading">
<div class="home-section-heading" id="school"><span class="home-section-kicker">A SCHOOL COMMUNITY</span><h2 id="services-heading">Room to learn. Support to thrive.</h2><p>From the classroom to the wider school community, every part of the day matters.</p></div>
<div class="home-feature-list" id="learning"><article class="home-feature"><span class="home-feature-number">01</span><h3>Excellence</h3><p>Build strong foundations with digital report cards and structured timetables.</p></article><article class="home-feature"><span class="home-feature-number">02</span><h3>Discipline</h3><p>Support each school day with reliable morning and afternoon attendance tracking.</p></article><article class="home-feature"><span class="home-feature-number">03</span><h3>Integrity</h3><p>Keep school services clear with transparent fee balances and secure access.</p></article><article class="home-feature"><span class="home-feature-number">04</span><h3>Innovation</h3><p>Bring families and school teams closer through timely communication.</p></article></div>
</section>
<footer class="home-footer"><span>© {{ year }} Lycée de Muhura</span><div><a href="/login">Portal sign in</a><a href="/student/rfid-login">RFID access</a></div></footer>
</div>"""
    return page("Home", body, "home", school_motto=get_setting("school_motto", "").strip())

def register_routes(app):
    app.add_url_rule('/school-logo', endpoint='school_logo', view_func=school_logo, methods=['GET'])
    app.add_url_rule('/', endpoint='home', view_func=home, methods=['GET'])
