import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from datetime import timedelta
from flask import Flask, request, redirect, url_for, render_template, flash, make_response, jsonify, send_file
from flask.ext.sqlalchemy import SQLAlchemy
import flask.ext.restless
from collections import Counter
from flask.ext.security import (Security, LoginForm, login_required, roles_accepted, user_datastore)
from flask.ext.security.datastore.sqlalchemy import SQLAlchemyUserDatastore
# from whooshalchemy import IndexService
import tablib

# create application
app = Flask('augur')

app.config.from_pyfile('settings.cfg')

# connect to database
db = SQLAlchemy(app)
Security(app, SQLAlchemyUserDatastore(db))


"""
MODELS
"""


tags = db.Table('tags', db.metadata,
    db.Column('event_id', db.Integer, db.ForeignKey('event.id')),
    db.Column('choice_id', db.Integer, db.ForeignKey('choice.id')),
)

message_tags = db.Table('message_tags',
    db.Column('message_id', db.Integer, db.ForeignKey('message.id')),
    db.Column('choice_id', db.Integer, db.ForeignKey('choice.id')),
)

message_libraries = db.Table('message_libraries',
    db.Column('library_id', db.Integer, db.ForeignKey('library.id')),
    db.Column('message_id', db.Integer, db.ForeignKey('message.id')),
)

subject_libraries = db.Table('subject_libraries',
    db.Column('library_id', db.Integer, db.ForeignKey('library.id')),
    db.Column('subject_id', db.Integer, db.ForeignKey('subject.id')),
)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime)
    choices = db.relationship('Choice', secondary=tags, backref='events')
    library_id = db.Column(db.Integer, db.ForeignKey('library.id'))
    note = db.Column(db.Text)

    def __init__(self, time, choices, note):
        self.choices = choices
        if time is None:
                time = datetime.now()
        self.time = time
        if note is None:
            note = None
        self.note = note

    def __repr__(self):
        return '<%r: %r>' % (self.time, self.choices)


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    choices = db.relationship('Choice', backref='subject')
    libraries = db.relationship('Library', secondary=subject_libraries,
        backref='subjects')
    metatag = db.Column(db.Boolean, default=False)

    def __init__(self, name, metatag):
        self.name = name
        if metatag is None:
            metatag = False
        self.metatag = metatag

    def __repr__(self):
        return '<Subject %r>' % self.name


class Choice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    choice = db.Column(db.String(80))
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'))
    metatag = db.Column(db.Boolean, default=False)

    def __init__(self, choice, metatag):
        self.choice = choice
        if metatag is None:
            metatag = False
        self.metatag = metatag

    def __repr__(self):
        return '<Choice %r>' % self.choice


class Library(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    events = db.relationship('Event', backref='library')

    def __repr__(self):
        return '<Library %r>' % self.name


class Message(db.Model):
    # __tablename__ = 'message'
    # __searchable__ = ['title', 'message']  # these fields will be indexed by whoosh

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text)
    message = db.Column(db.Text)
    author = db.Column(db.String(40))
    date = db.Column(db.DateTime)
    expiration = db.Column(db.DateTime)
    show = db.Column(db.Boolean, default=True)
    promoted = db.Column(db.Boolean, default=False)
    libraries = db.relationship('Library', secondary=message_libraries,
        backref='messages')
    message_tags = db.relationship('Choice', secondary=message_tags,
        backref='messages')

    def __init__(self, title, message, author, date, expiration, show, promoted, message_tags):
        self.title = title
        self.message = message
        if date is None:
                date = datetime.now()
        self.date = date
        self.author = author
        self.expiration = expiration
        self.show = show
        self.promoted = promoted
        self.message_tags = message_tags

    def __repr__(self):

        return '<Message %r>' % self.message

# index_service = IndexService(config=app.config)

# index_service.register_class(Message)
manager = flask.ext.restless.APIManager(app, flask_sqlalchemy_db=db)
manager.create_api(Event, methods=['GET', 'POST', 'DELETE'])
manager.create_api(Subject, methods=['GET', 'POST', 'DELETE'])
manager.create_api(Choice, methods=['GET', 'POST', 'DELETE'])
manager.create_api(Message, methods=['GET', 'POST', 'DELETE'])
manager.create_api(Library, methods=['GET', 'POST', 'DELETE'])
"""
LOGIC
"""


# Gets messages to display on the Homepage
def get_messages():
    test = Message.query.order_by(Message.id.desc())
    today = datetime.date(datetime.today())
    expiring_messages = []
    for message in test:
        expiration = datetime.date(message.expiration)
        if expiration <= today:
            expiring_messages.append(message)
    for expired_message in expiring_messages:
        expire_messages(expired_message.id)
    return test


# Set a message to no longer show up on the front page
def expire_messages(no):
    expiring = Message.query.filter_by(id=no).first()
    if expiring.show == True:
        expiring.show = False
    db.session.commit()


# Send an email
def send_email(sender, receiver, subject, body):
    msg = MIMEMultipart('alternative')
    msg['subject'] = subject
    msg['To'] = receiver
    msg['From'] = receiver
    html_body = MIMEText(body, 'html')

    msg.attach(html_body)

    # Credentials (if needed)
    username = 'augurlibrary'
    password = 'premonitio'

    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(username, password)
    server.sendmail(sender, receiver, msg.as_string())
    server.quit()


@app.context_processor
def get_library():
    default = Library.query.first()
    the_library = request.cookies.get('library_name') or default
    our_library = Library.query.filter_by(name=the_library).first()
    if not our_library:
        the_library = default.name
        our_library = default
    libraries = Library.query.all()

    return dict(the_library=the_library, the_library_id=our_library.id, libraries=libraries)


@app.template_filter()
def friendly_time(dt, past_="ago",
    future_="from now",
    default="just now"):
    """
    Returns string representing "time since"
    or "time until" e.g.
    3 days ago, 5 hours from now etc.
    """

    now = datetime.now()
    if now > dt:
        diff = now - dt
        dt_is_past = True
    else:
        diff = dt - now
        dt_is_past = False

    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:

        if period:
            return "%d %s %s" % (period, \
                singular if period == 1 else plural, \
                past_ if dt_is_past else future_)

    return default


@app.after_request
def shutdown_session(response):
    db.session.remove()
    return response


"""
URLS/VIEWS
"""


# View for the Homepage
@app.route('/', methods=['GET', 'POST'])
def front_page():
    library = request.cookies.get('library_id') or Library.query.first().id
    return redirect(url_for('show_entries', library_id=library))


@app.route('/<library_id>', methods=['GET', 'POST'])
@login_required
def show_entries(library_id):
    current_library = Library.query.filter_by(id=library_id).first() or Library.query.first()
    now = datetime.now()
    messages = get_messages()
    events = Event.query.filter_by(library=current_library).order_by(Event.time.desc()).limit(15).all()
    subjects = Subject.query.order_by(Subject.name).all()
    choices = Choice.query.all()
    output = render_template('show_entries.html', time=now, events=events, subjects=subjects, choices=choices,
        messages=messages)
    output = make_response(output)
    return output


# View for the /charts page
@app.route('/charts', methods=['GET', 'POST'])
@login_required
def charts():
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    today = datetime.today()
    today_int = datetime.date(today).weekday() + 1
    today = weekdays[today_int - 1]
    if request.method == 'POST':
        start_day = request.form['start_date']
        if start_day == '':
            start_day = '1900-01-01'
        start_date = datetime.strptime(start_day, '%Y-%m-%d').date()
        end_day = request.form['end_date']
        if end_day == '':
            end_day = '2100-01-01'
        end_date = datetime.strptime(end_day, '%Y-%m-%d').date()
        all_subjects = Subject.query.filter_by(metatag=False)
        flash('Now showing data between %s and %s' % (str(start_date), str(end_date)))
        return render_template('charts.html', start_date=start_day, end_date=end_day, today=today, today_int=today_int, weekdays=weekdays,
         chooser=all_subjects, timechart=None)
    DD = timedelta(days=30)
    DA = timedelta(days=1)
    end_date = datetime.today()
    start_date = end_date - DD
    end_date = end_date + DA
    start_date = datetime.strftime(start_date, '%Y-%m-%d')
    end_date = datetime.strftime(end_date, '%Y-%m-%d')
    subjects = Subject.query.filter_by(metatag=False)
    resp = make_response(render_template('charts.html', chooser=subjects, today=today, today_int=today_int, weekdays=weekdays,
        subjects=None, timechart=1, start_date=start_date, end_date=end_date))
    return resp


# JSON for the Javascript Events chart
@app.route('/jchartevents/<library>/<start_date>/<end_date>')
@login_required
def jchart(library, start_date, end_date):
    chosen_library = Library.query.filter_by(name=library).first()
    if start_date == '1900-01-01':
        DD = timedelta(days=30)
        end_date = datetime.today()
        start_date = end_date - DD
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    if library == 'all':
        result = db.session.query(Event).filter(Event.time.between(start_date, end_date)).order_by(Event.time)
    else:
        result = db.session.query(Event).filter(Event.time.between(start_date, end_date)).filter_by(library=chosen_library).order_by(Event.time)
    events = [x.time for x in result]
    event_days = []
    events = sorted(events)
    data = []

    event_days = [datetime.date(event) for event in events]
    counted = dict(Counter(event_days))
    for key in sorted(counted.iterkeys()):
        formatted_key = key.strftime("%Y-%m-%d %H:%M:%S")
        item = [formatted_key, counted[key]]
        data.append(item)

    return jsonify(output=data)


# JSON for the Weekly chart
@app.route('/jchartweekly/<library>/<start_date>/<end_date>')
@login_required
def jchart_weekly(library, start_date, end_date):
    chosen_library = Library.query.filter_by(name=library).first()
    if start_date == '1900-01-01':
        DD = timedelta(days=30)
        end_date = datetime.today()
        start_date = end_date - DD
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    if library == 'all':
        result = db.session.query(Event).filter(Event.time.between(start_date, end_date)).order_by(Event.time)
    else:
        result = db.session.query(Event).filter(Event.time.between(start_date, end_date)).filter_by(library=chosen_library).order_by(Event.time)
    delta = (end_date - start_date) / 7

    events = sorted([x.time for x in result])
    events = [x.strftime('%A') for x in events]
    data = []
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    counted = dict(Counter(events))
    for day in weekdays:
        for key in counted.iterkeys():
            if day == key:
                item = [key, counted[key] / int(delta.days)]
                data.append(item)
    return jsonify(output=data)


# JSON For an hourly chart
@app.route('/jcharthourly/<library>/<start_date>/<end_date>/<day>')
@login_required
def jchart_hourly(library, start_date, end_date, day):
    chosen_library = Library.query.filter_by(name=library).first()
    if start_date == '1900-01-01':
        DD = timedelta(days=30)
        end_date = datetime.today()
        start_date = end_date - DD
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    if library == 'all':
        result = db.session.query(Event).filter(Event.time.between(start_date, end_date)).order_by(Event.time)
    else:
        result = db.session.query(Event).filter(Event.time.between(start_date, end_date)).filter_by(library=chosen_library).order_by(Event.time)
    delta = (end_date - start_date) / 7
    times = ['07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00']
    events = sorted([x.time for x in result])
    formatted_events = sorted([x.strftime('%H:00') for x in events if x.strftime('%A') == day])
    counted = dict(Counter(formatted_events))
    data = []
    for time in times:
        if time not in counted.iterkeys():
            counted[time] = 0
    for key, value in counted.iteritems():
        try:
            counted[key] = int(value) / int(delta.days)
        except:
            # If DivideByZero
            counted[key] = int(value) / 1
        item = [key, counted[key]]
        data.append(item)
    data = sorted(data)
    return jsonify(output=data)


# JSON for the Javascript Pie chart
@app.route('/jchartpie/<library>/<int:subject_id>/<start_date>/<end_date>')
@login_required
def jchartpie(library, subject_id, start_date, end_date):
    subject = Subject.query.filter_by(id=subject_id).first()
    if start_date == '1900-01-01':
        DD = timedelta(days=30)
        end_date = datetime.today()
        start_date = end_date - DD
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    subject_choices = [choice.choice for choice in subject.choices]
    # Query returns the number of times a Choice was made in an Event
    counted = {(made_choice[:20] + '..') if len(made_choice) > 20 else made_choice: Event.query.join(Event.choices).filter(Choice.choice == made_choice).count() for made_choice in subject_choices}

    data = []
    for key in sorted(counted.iterkeys()):
        item = [key, counted[key]]
        data.append(item)
    return jsonify(output=data)


# View for the /knowledgebase page
@app.route('/knowledgebase', methods=['GET', 'POST'])
@login_required
def knowledge_base():
    if request.method == 'POST':
        search = request.form['search']
        entries = Message.search_query(search)
        output = render_template('knowledge_base.html', entries=entries)
        return output
    entries = Message.query.order_by(Message.date).limit(10)
    subjects = Subject.query.order_by(Subject.name)
    choices = Choice.query.all()
    output = render_template('knowledge_base.html', entries=entries, subjects=subjects, choices=choices)
    return output


# TEST
@app.route('/test', methods=['GET', 'POST'])
@login_required
def test():
    if request.method == 'POST':
        start_day = request.form['start_date']
        if start_day == '':
            start_day = '1900-01-01'
        start_date = datetime.strptime(start_day, '%Y-%m-%d').date()
        end_day = request.form['end_date']
        if end_day == '':
            end_day = '2100-01-01'
        end_date = datetime.strptime(end_day, '%Y-%m-%d').date()
        all_subjects = Subject.query.filter_by(metatag=False)
        flash('Now showing data between %s and %s' % (str(start_date), str(end_date)))
        return render_template('charts.html', start_date=start_day, end_date=end_day,
         chooser=all_subjects, timechart=None)
    DD = timedelta(days=30)
    DA = timedelta(days=1)
    end_date = datetime.today()
    start_date = end_date - DD
    end_date = end_date + DA
    start_date = datetime.strftime(start_date, '%Y-%m-%d')
    end_date = datetime.strftime(end_date, '%Y-%m-%d')
    subjects = Subject.query.filter_by(metatag=False)
    chosen_library = 'all'
    resp = make_response(render_template('test.html', chooser=subjects,
        subjects=None, timechart=1, library=chosen_library, start_date=start_date, end_date=end_date))
    return resp


# View for the /data page, and to create CSVs
@app.route('/data', methods=['GET', 'POST'])
@login_required
def data():
    the_library = request.cookies.get('library_name')
    the_library = Library.query.filter_by(name=the_library).first()
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        if start_date == '1900-01-01':
            DD = timedelta(days=30)
            end_date = datetime.today()
            start_date = end_date - DD
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        subjects = Subject.query.filter_by(metatag=False).filter(Subject.libraries.contains(the_library)).all()
        events = db.session.query(Event).filter(Event.time.between(start_date, end_date)).filter_by(library=the_library).order_by(Event.time)
        data = tablib.Dataset()
        data.headers = [subject.name for subject in subjects]
        data.headers.append(u'Time')
        for event in events:
            a = [tag.choice for tag in event.choices]
            a.append(str(event.time))
            data.append(a)
        with open('output.csv', 'wb') as f:
            f.write(data.csv)
            f.seek(0)
        return send_file('output.csv', 'csv', as_attachment=True)

    the_library = request.cookies.get('library_name')
    events = Event.query.order_by(Event.time.desc()).limit(100)
    subjects = Subject.query.all()
    choices = Choice.query.all()
    output = render_template('data.html', the_library=the_library, events=events, subjects=subjects, choices=choices)
    return output


# View for the /admin page, register a user
@app.route('/admin', methods=['GET', 'POST'])
@roles_accepted('admin', 'super_admin')
def admin():
    if request.method == 'POST':
        new_user = request.form['user']
        new_email = request.form['email']
        new_pass = request.form['pass']
        new_role = request.form['role']
        if new_role == 'admin':
            user_datastore.create_user(username=new_user, email=new_email, password=new_pass, roles=['admin'])
        else:
            user_datastore.create_user(username=new_user, email=new_email, password=new_pass, roles=['user'])
        flash('Thanks for registering')
        return redirect(url_for('admin'))
    subjects = Subject.query.order_by(Subject.name)
    choices = Choice.query.order_by(Choice.choice.desc())
    output = render_template('admin.html', subjects=subjects, choices=choices)
    return output


# Promotes a message to the knowledgebase
# ERROR: Redirects to homepage even if you started on the knowledgebase page.
@app.route('/promote/<int:message_id>')
@login_required
def promote_message(message_id):
    item = Message.query.filter_by(id=message_id).first()
    if item.promoted == False:
        item.promoted = True
        flash('Item promoted to knowledge base!')
    else:
        item.promoted = False
        flash('Item removed from knowledge base.')
    db.session.commit()
    library_id = request.cookies.get('library_id') or Library.query.first().id
    return redirect(url_for('show_entries', library_id=library_id))


# Edit a post
# Add Expiration as editable??????????
@app.route('/edit/<int:message_id>', methods=['GET', 'POST'])
@login_required
def edit_message(message_id):
    the_library = request.cookies.get('library_name')
    if request.method == 'POST':
        all_tags = []
        today = datetime.today()
        title = None
        new_tags = None
        if request.form['title']:
            title = request.form['title']
        new_tags = request.form.getlist('tags')
        for tag in new_tags:
            if tag == None:
                continue
            a = Choice.query.filter_by(choice=tag).first()
            all_tags.append(a)
        new_message = request.form['message']
        current_user = request.form['user']
        new_date = request.form['date']
        expire = request.form['expire']
        # Add Expiration as editable??????????
        message_id = request.form['message_id']
        expire = today + timedelta(days=int(expire))
        old_message = Message.query.filter_by(id=message_id).first()
        old_message.title = title
        old_message.author = current_user
        old_message.date = new_date
        old_message.message = new_message
        old_message.message_tags = all_tags
        db.session.commit()
        flash('Changes saved.')
        return redirect(url_for('show_message', message_id=message_id))
    item = Message.query.filter_by(id=message_id).first()
    subjects = Subject.query.order_by(Subject.name)
    choices = Choice.query.order_by(Choice.choice.desc())
    return render_template('edit_entry.html', subjects=subjects, the_library=the_library,
     choices=choices, message=item)


# Show a single post
@app.route('/show/<int:message_id>')
@login_required
def show_message(message_id):
    entry = Message.query.filter_by(id=message_id).first()
    output = render_template('show_entry.html', message=entry)
    return output


# Show Metatag info
@app.route('/tag/<int:tag_id>', methods=['GET', 'POST'])
@login_required
def show_tag(tag_id):
    metatag = Choice.query.filter_by(id=tag_id).first()
    if request.method == 'POST':
        start_day = request.form['start_date']
        if start_day == '':
            start_day = '1900-01-01'
        start_date = datetime.strptime(start_day, '%Y-%m-%d').date()
        end_day = request.form['end_date']
        if end_day == '':
            end_day = '2100-01-01'
        end_date = datetime.strptime(end_day, '%Y-%m-%d').date()
        flash('Now showing data between %s and %s' % (str(start_date), str(end_date)))
        the_count = Event.query.join(Event.choices).filter(Event.time.between(start_date, end_date)).filter(Choice.id == tag_id).count()
        return render_template('metatag.html', the_count=the_count, start_date=start_day, end_date=end_day, metatag=metatag)
    DD = timedelta(days=30)
    DA = timedelta(days=1)
    end_date = datetime.today()
    start_date = end_date - DD
    end_date = end_date + DA
    start_date = datetime.strftime(start_date, '%Y-%m-%d')
    end_date = datetime.strftime(end_date, '%Y-%m-%d')
    the_count = Event.query.join(Event.choices).filter(Event.time.between(start_date, end_date)).filter(Choice.id == tag_id).count()
    resp = make_response(render_template('metatag.html', start_date=start_date, end_date=end_date, the_count=the_count, metatag=metatag))
    return resp


# Creates a new Library
@app.route('/library', methods=['POST'])
def new_library():
    new_library = request.form['library']
    library = Library(name=new_library)
    if request.form['new_library'] == 'True':
        db.session.add(library)
        db.session.commit()
        flash('New Library Added')
    else:
        edit_library = request.form['no']
        library = Library.query.filter_by(id=edit_library).first()
        library.name = new_library
        db.session.commit()
        flash('Library Name Edited.')
    output = make_response(redirect(url_for('admin')))
    output.set_cookie('library_id', library.id)
    output.set_cookie('library_name', library.name)
    return output


# Creates a new Event
@app.route('/add', methods=['POST'])
@login_required
def add_entry():
    all_tags = []
    library_id= request.cookies.get('library_id') or Library.query.first().id
    if request.form.getlist('values'):
        new_tags = request.form.getlist('values')  # Get every form item with name='values' and create a list
    else:
        flash('Please choose at least one option.')
        return redirect(url_for('show_entries', library_id=library_id))
    library = request.form['library']
    for tag in new_tags:
        a = Choice.query.filter_by(id=tag).first()
        all_tags.append(a)
    new_time_asked = request.form['time_asked']
    new_question = Event(time=new_time_asked, choices=all_tags, note=None)
    library = Library.query.filter_by(name=library).first()
    library.events.append(new_question)
    db.session.commit()
    flash('New event was successfully posted')
    return redirect(url_for('show_entries', library_id=library_id))


# Creates a new message
@app.route('/message', methods=['POST'])
@login_required
def message():
    library_id = request.cookies.get('library_id') or Library.query.first().id
    all_tags = []
    today = datetime.today()
    title = None
    new_tags = None
    page = request.form['page']
    if request.form['title']:
        title = request.form['title']
    new_tags = request.form.getlist('tags')
    for tag in new_tags:
        a = Choice.query.filter_by(id=tag).first()
        all_tags.append(a)
    new_message = request.form['message']
    current_user = request.form['user']
    new_date = today
    expire = request.form['expire']
    expire = today + timedelta(days=int(expire))
    the_library = Library.query.filter_by(id=library_id).first()
    if page == 'knowledgebase':
        new_message = Message(title=title, message=new_message, author=current_user, date=new_date,
         expiration=expire, show=False, promoted=True, message_tags=all_tags)
        db.session.add(new_message)
        new_message.libraries.append(the_library)
        db.session.commit()
        return redirect(url_for('knowledge_base'))
    new_message = Message(title=title, message=new_message, author=current_user, date=new_date,
        expiration=expire, show=True, promoted=False, message_tags=all_tags)
    db.session.add(new_message)
    new_message.libraries.append(the_library)
    db.session.commit()
    return redirect(url_for('show_entries', library_id=library_id))


# Creates a new Subject
@app.route('/adminsubject', methods=['POST'])
@login_required
def admin_subject():
    new_subject = request.form['subject']
    is_new_or_not = request.form['new_subject']
    library = request.form['library']
    subject_id = request.form['no']
    subject_choice_id = request.form['choice_no']
    library = Library.query.filter_by(name=library).first()
    if request.form['metatag'] == 'tag':
        if is_new_or_not == 'True':
            made_subject = Subject(new_subject, metatag=True)
            made_subject.choices.append(Choice(new_subject, metatag=True))
            library.subjects.append(made_subject)
            flash('Added New Subject.')
        else:
            made_subject = Subject.query.filter_by(id=subject_id).first()
            made_subject.name = new_subject
            made_choice = Choice.query.filter_by(id=subject_choice_id).first()
            made_choice.choice = new_subject
            made_subject.name = new_subject
            flash('Edited Subject.')
    else:
        if is_new_or_not == 'True':
            made_subject = Subject(new_subject, metatag=False)
            library.subjects.append(made_subject)
            flash('Added New Subject.')
        else:

            made_subject = Subject.query.filter_by(id=subject_id).first()
            made_subject.name = new_subject
            flash('Edited Subject.')
    db.session.commit()
    return redirect(url_for('admin'))


# Creates a new Choice
@app.route('/adminnewchoice', methods=['POST'])
def admin_new_choice():
    new_choice = request.form['choice']
    subject_id = request.form['subject_id']
    subject = Subject.query.filter_by(id=subject_id).first()
    if request.form['new_choice'] == 'True':
        new_tag = Choice(new_choice, metatag=False)
        subject.choices.append(new_tag)
        db.session.commit()
        flash('Added new option.')
    else:
        edit_choice = request.form['no']
        choice = Choice.query.filter_by(id=edit_choice).first()
        choice.choice = new_choice
        db.session.commit()
        flash('Choice Name Edited.')
    return redirect(url_for('admin'))


# Deletes a Message, Event, Subject, Library or Choice
@app.route('/admindelete', methods=['POST'])
@login_required
def admin_delete():
    no = request.form['no']
    library_id = request.cookies.get('library_id') or Library.query.first().id
    table = request.form['table']
    if table == 'messages':
        tag = Message.query.filter_by(id=no).first()
        association_table_rows = message_tags.delete().where(message_tags.c.message_id == no)
        db.session.execute(association_table_rows)
        db.session.delete(tag)
        db.session.commit()
        flash('FAQ item deleted.')
        return redirect(url_for('show_entries', library_id=library_id))
    elif table == 'questions':
        event = Event.query.filter_by(id=no).first()
        association_table_rows = tags.delete().where(tags.c.event_id == no)
        db.session.execute(association_table_rows)
        db.session.delete(event)
        db.session.commit()
        flash('Event deleted.')
        return redirect(url_for('show_entries', library_id=library_id))
    elif table == 'subject':
        tag = Subject.query.filter_by(id=no).first()
        db.session.delete(tag)
        db.session.commit()
        flash('Subject deleted.')
        return redirect(url_for('admin'))
    elif table == 'libraries':
        library = Library.query.filter_by(id=no).first()
        db.session.delete(library)
        db.session.commit()
        flash('Library deleted.')
        which_library = Library.query.first()
        output = redirect(url_for('admin'))
        output = make_response(output)
        output.set_cookie('library_name', which_library.name)
        output.set_cookie('library_id', which_library.id)
        return output
    tag = Choice.query.filter_by(id=no).first()
    db.session.delete(tag)
    db.session.commit()
    flash('Option deleted.')
    return redirect(url_for('admin'))


# Creates the email to be sent
@app.route('/email', methods=['POST'])
def email():
    library_id = request.cookies.get('library_id') or Library.query.first().id
    title = request.form['title']
    body = request.form['body']
    recipient = request.form['recipient']
    send_email('augurlibrary@gmail.com', recipient, title, body)
    flash('Email sent!')
    return redirect(url_for('show_entries', library_id=library_id))


# Change the Cookie that sets which library is being used
@app.route('/change_library', methods=['POST'])
@login_required
def change_library_cookie():
    which_page = request.form['which_page']
    which_library_id = request.form['which_library_id']
    which_library = Library.query.filter_by(id=which_library_id).first()
    if which_page == 'show_entries':
        output = redirect(url_for(which_page, library_id=which_library_id))
    else:
        output = redirect(url_for(which_page))
    output = make_response(output)
    output.set_cookie('library_name', which_library.name)
    output.set_cookie('library_id', which_library.id)
    return output


@app.route("/upload", methods=['POST'])
def upload():
    from manage import csv_import
    file = request.files['file']
    csv_import(file.filename)
    flash('CSV Imported')
    return redirect(url_for('admin'))


@app.route("/login")
def login():
    return render_template('login.html', form=LoginForm())


@app.route('/profile')
@login_required
def profile():
    return render_template('show_entries.html')


if __name__ == '__main__':
    # app.debug = True
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    # app.run()
