import sqlite3, os
import xml.etree.ElementTree as ET
import penguicontrax as penguicontrax
from submission import Submission, Track, Resource
from tag import Tag, normalize_tag_name
from user import Presenter, User
from event import Convention, Rooms, Events
import datetime, random
from user.Login import generate_account_name, gravatar_image_update
import sys

def setup_predefined():
    penguicontrax.db.session.add(
        Resource('Projector', 'This event CANNOT happen without a projector', True)
    )
    penguicontrax.db.session.add(
        Resource('Microphone/sound system',
                 'This event CANNOT happen without a microphone and sound system',
                 True)
    )
    penguicontrax.db.session.add(Resource('Drinking water', 'Drinking water', False))
    penguicontrax.db.session.add(Resource('Quiet (no airwalls)', 'Quiet (no airwalls)', False))

    official_tags_tracks = \
    [
        ('diy','Making, building, and tinkering.'),
        ('action-adventure','Weapons, guns, martial arts.'),
        ('penguicon','All about Penguicon iteself.'),
        ('costuming','Costumes and accessories, masks, special effects makeup.'),
        ('music','Listening to, creating, and discussing music.'),
        ('tech','Software, hardware, and engineering.'),
        ('eco','The environment, energy efficiency, self-sufficiency.'),
        ('after-dark','Sex, alcohol, parties, adult pastimes. '),
        ('mayhem','Fun that happens outside our event spaces.'),
        ('film','Watching or discussing film or TV.'),
        ('food','Cooking demos, tastings, what we eat.'),
        ('literature','Genre fiction, the craft and profession of writing.'),
        ('science','Talks and demos from the lab, in the field, or even outer space.'),
        ('video-gaming','Playing or discussing electronic interactive entertainment.'),
        ('life','Lifestyles, skills, wellness, money, career, and fun!'),
        ('gaming','Playing or discussing board games, card games, and roleplaying games.')
    ]

    for track in official_tags_tracks:
        penguicontrax.db.session.add(Track(track[0],None))
    for tag in official_tags_tracks:
        penguicontrax.db.session.add(Tag(tag[0],tag[1],True))
    penguicontrax.db.session.commit()

def import_old(path, as_convention = False, random_rsvp_users = 0, submission_limit = sys.maxint, timeslot_limit = sys.maxint):
    
    if as_convention == True:
        convention = Convention()
        convention.name = 'Penguicon 2013'
        convention.url = '2013'
        convention.description = 'Penguicon 2013 schedule imported from schedule2013.html'
        convention.start_dt = datetime.datetime(year=2013, month=4, day=26, hour=16)
        convention.end_dt = datetime.datetime(year=2013, month=4, day=28, hour=16)
        convention.timeslot_duration = datetime.timedelta(hours=1)
        penguicontrax.db.session.add(convention)
        current_day = convention.start_dt.date()
        current_time = None

    existing_tags = {}
    for tag in Tag.query.all():
        existing_tags[tag.name] = tag
        
    existing_people = {}
    for person in Presenter.query.all():
        existing_people[person.name] = person

    existing_tracks = {}
    for track in Track.query.all():
        existing_tracks[track.name] = track

    existing_rooms = {}
    existing_submissions = []

    submission_count = 0
    with penguicontrax.app.open_resource(path, mode='r') as f:
        tree = ET.fromstring(f.read())
        events = tree.find('document')
        for section in events:
            if submission_count == submission_limit:
                break
            if as_convention == True and section.tag == 'time':
                time_text= section.text.split(' ')
                hour = int(time_text[0])
                if time_text[1] == 'PM' and hour != 12:
                    hour += 12
                elif time_text[1] == 'AM' and hour == 12:
                    hour = 0
                new_time = datetime.time(hour = hour)
                if not current_time is None and new_time.hour < current_time.hour:
                    current_day = current_day + datetime.timedelta(days=1)
                current_time = new_time                 
            elif section.tag == 'div' and section.attrib['class'] == 'section':
                name = section[0].text
                tag_list = section[1].text # Tag doesn't seem to be in the DB yet
                room = section[2].text
                presenters = section[3][0].text
                description = section[3][0].tail
                submission = Submission() if as_convention == False else Events()
                submission.title = name
                submission.description = description
                submission.duration = 1
                submission.setupTime = 0
                submission.repetition = 0
                submission.followUpState = 0
                submission.eventType = 'talk'
                #Load presenters
                submission.presenters = []
                for presentername in [presenter.strip() for presenter in presenters.split(',')]:
                    if presenter == 'Open':
                        continue #"Open" person will cause the schedule to become infesible
                    presenter = None
                    if not presentername in existing_people:
                        presenter = Presenter(presentername)
                        penguicontrax.db.session.add(presenter)
                        existing_people[presentername] = presenter
                    else:
                        presenter = existing_people[presentername]
                    submission.presenters.append(presenter)
                #Load Tags
                submission.tags = []
                for tag in tag_list.split(','):
                    tag = normalize_tag_name(tag)
                    db_tag = None
                    if not tag in existing_tags:
                        db_tag = Tag(tag, tag, True)
                        penguicontrax.db.session.add(db_tag)
                        existing_tags[tag] = db_tag
                    else:
                        db_tag = existing_tags[tag]
                    # Set track -- pick any tag that is also a track
                    if submission.track is None:
                        if tag in existing_tracks:
                            submission.track = existing_tracks[tag]
                    submission.tags.append(db_tag)
                #Load rooms
                if as_convention == True:
                    submission.convention = convention
                    db_room = None
                    if not room in existing_rooms:
                        db_room = Rooms()
                        db_room.room_name = room
                        db_room.convention = convention
                        penguicontrax.db.session.add(db_room)
                        existing_rooms[room] = db_room
                    else:
                        db_room = existing_rooms[room]
                    if not current_day is None and not current_time is None:
                        submission.rooms.append(db_room)
                        submission.start_dt = datetime.datetime(year=current_day.year, month=current_day.month, day=current_day.day,\
                            hour = current_time.hour, minute=current_time.minute)
                        submission.duration = 4 #1 hour
                existing_submissions.append(submission)
                penguicontrax.db.session.add(submission)
                submission_count = submission_count + 1
        print "New submission"
        penguicontrax.db.session.commit()

    if random_rsvp_users > 0:
        for user_index in range(random_rsvp_users):
            user = User()
            user.name = 'Random User %d' % user_index
            user.email = '%d@randomtraxuser.com' % user_index
            user.public_rsvps = True
            user.staff = False
            user.special_tag = None
            user.superuser = False
            generate_account_name(user)
            gravatar_image_update(user)
            for rsvp_index in range(user.points):
                rand = random.randint(0, len(existing_submissions) - 1)
                while user in existing_submissions[rand].rsvped_by:
                    rand = random.randint(0, len(existing_submissions) - 1)
                existing_submissions[rand].rsvped_by.append(user)
            user.points = 0
            penguicontrax.db.session.add(user)
        penguicontrax.db.session.commit()
        
    if as_convention == True:
        from event import generate_schedule, generate_timeslots
        generate_timeslots(convention, timeslot_limit)
        all_rooms = [room for room in existing_rooms.viewvalues()]
        hackerspace = [existing_rooms['Hackerspace A'], existing_rooms['Hackerspace B']]
        food = [existing_rooms['Food']]
        from copy import copy
        general_rooms = copy(all_rooms)
        general_rooms.remove(hackerspace[0])
        general_rooms.remove(hackerspace[1])
        general_rooms.remove(food[0])
        timeslots = [timeslot for timeslot in convention.timeslots]
        for submission in existing_submissions:
            if food[0] in submission.rooms:
                submission.suitable_rooms = food
            elif hackerspace[0] in submission.rooms or hackerspace[1] in submission.rooms:
                submission.suitable_rooms = hackerspace
            else:
                submission.suitable_rooms = general_rooms
        for room in all_rooms:
            room.available_timeslots = timeslots
        generate_schedule(convention)
            
