from flaskext.script import Manager
from augur import *
import tablib
import csv

manager = Manager(app)

@manager.command
def restart_db():
    db.drop_all()
    db.create_all()

    # Make users
    user_datastore.create_role(name='user')
    user_datastore.create_role(name='admin')
    user_datastore.create_user(username='augur', email='someone@gmail.com', password='premonition', roles=['admin'])

    library = Library(name='Main')

    format = Subject(name='Format', metatag=False)
    asked_by = Subject(name='Patron', metatag=False)
    location = Subject(name='Location', metatag=False)
    duration = Subject(name='Duration', metatag=False)
    question_type = Subject(name='Question Type', metatag=False)
    department = Subject(name='Department', metatag=False)

    db.session.add(library)

    db.session.commit()

    # Libraries
    some_subjects = [Subject(name='Format', metatag=False), Subject('Question Type', metatag=False), Subject('Patron', metatag=False),
        Subject('Location', metatag=False), Subject('Duration', metatag=False),
         Subject('Department', metatag=False)]
    for subject in some_subjects:
        library.subjects.append(subject)
    db.session.commit()

    # Format
    new_tags = [Choice('Email', metatag=False), Choice('Walkup', metatag=False), Choice('Phone', metatag=False), Choice('Text', metatag=False)]
    format = Subject.query.filter_by(name='Format').first()
    for tag in new_tags:
        format.choices.append(tag)
    db.session.commit()
    # Asked By
    new_tags = [Choice('Student', metatag=False), Choice('Staff', metatag=False), Choice('Faculty', metatag=False), Choice('Alumnus', metatag=False)]
    asked_by = Subject.query.filter_by(name='Patron').first()
    for tag in new_tags:
        asked_by.choices.append(tag)
    db.session.commit()
    # Location
    new_tags = [Choice('Reference Desk', metatag=False), Choice('Circulation', metatag=False)]
    location = Subject.query.filter_by(name='Location').first()
    for tag in new_tags:
        location.choices.append(tag)
    db.session.commit()
    # Duration
    new_tags = [Choice('0-5', metatag=False), Choice('5-10', metatag=False), Choice('10+', metatag=False)]
    duration = Subject.query.filter_by(name='Duration').first()
    for tag in new_tags:
        duration.choices.append(tag)
    db.session.commit()
    # Question Type
    new_tags = [Choice('Research Consultation', metatag=False), Choice('Reference', metatag=False), Choice('Directional', metatag=False), Choice('Technical', metatag=False)]
    question_type = Subject.query.filter_by(name='Question Type').first()
    for tag in new_tags:
        question_type.choices.append(tag)
    db.session.commit()
    # Department
    new_tags = [Choice('English', metatag=False), Choice('Chemistry', metatag=False), Choice('Metaphysics', metatag=False), Choice('Geology', metatag=False)]
    department = Subject.query.filter_by(name='Department').first()
    for tag in new_tags:
        department.choices.append(tag)
    db.session.commit()


@manager.command
def csv_import(which):
    try:
        csvReader = csv.reader(open(which, 'rb'), delimiter=',')
    except Exception, e:
        raise e
    headline = []
    for row in csvReader:
        header = str(row).rsplit(',')
        for word in header:
            newstr = word.replace("[", "")
            newstr = newstr.replace("]", "")
            newstr = newstr.replace("\\", "")
            newstr = newstr.replace("'", "")
            newstr = newstr.strip()
            headline.append(newstr)
        break
    data = tablib.Dataset()
    data.headers = headline
    for row in csvReader:
        data.append(row)
    del data[0]

    library = Library(name='Imported')


    db.session.add(library)
    db.session.commit()

    library = Library.query.filter_by(name='Imported').first()

    new_subjects = []
    full_subjects = []
    for index, row in enumerate(data.headers):
        if 2 < index < 8 or index == 9:
            new_subjects.append(Subject(name=row, metatag=False).name)
            if index != 9:
                full_subjects.append(Subject(name=row, metatag=False))

    for subject in full_subjects:
        library.subjects.append(subject)
    db.session.commit()

    Location = []
    Duration = []
    Format = []
    Questioner = []
    Question_Type = []
    Asked_At = []

    formatted_data = tablib.Dataset()
    formatted_data.headers = new_subjects
    for row in data:
        formatted_data.append([row[3], row[4], row[5], row[6], row[7], row[9]])
        Location.append(row[3])
        Duration.append(row[4])
        Format.append(row[5])
        Questioner.append(row[6])
        Question_Type.append(row[7])
        Asked_At.append(row[9])

    Location = set(Location)
    Duration = set(Duration)
    Format = set(Format)
    Questioner = set(Questioner)
    Question_Type = set(Question_Type)

    # Format
    for subject in full_subjects:
        if subject.name == 'Format':
            new_tags = list(Format)
            format = subject
            for tag in new_tags:
                format.choices.append(Choice(choice=tag, metatag=False))
            db.session.commit()

    # Duration
        if subject.name == 'Duration':
            new_tags = list(Duration)
            format = subject
            for tag in new_tags:
                format.choices.append(Choice(choice=tag, metatag=False))
            db.session.commit()

    # Question Type
        if subject.name == 'Question Type':
            new_tags = list(Question_Type)
            format = subject
            for tag in new_tags:
                format.choices.append(Choice(choice=tag, metatag=False))
            db.session.commit()

    # Location
        if subject.name == 'Location':
            new_tags = list(Location)
            format = subject
            for tag in new_tags:
                format.choices.append(Choice(choice=tag, metatag=False))
            db.session.commit()

    # Questioner
        if subject.name == 'Questioner':
            new_tags = list(Questioner)
            format = subject
            for tag in new_tags:
                format.choices.append(Choice(choice=tag, metatag=False))
            db.session.commit()


    library = Library.query.filter_by(name='Imported').first()

    for row in formatted_data:
        new_row = []
        for tag in row:

            choices_by_tag = Choice.query.filter_by(choice=tag).all()
            for choice in choices_by_tag:
                for library in choice.subject.libraries:
                    if library.name == 'Imported':
                        new_row.append(choice)
        the_time = row[5]
        the_time = datetime.strftime(datetime.strptime(the_time, '%Y-%m-%d %I:%M:%S %p'), '%Y-%m-%d %H:%M:%S')
        a = Event(time=the_time, choices=new_row, note='Imported')
        library.events.append(a)
    db.session.commit()




if __name__ == "__main__":
    manager.run()
