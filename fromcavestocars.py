#!/usr/bin/python3
"""
This is a game where you learn how things are made (at least according to 
ChatGPT).   In other words, what would a primitive human do in order to make
some item today?

This was done mostly as a learning exercise for me to really see what ChatGPT /
CoPilot can do and where it falls short.


I asked ChatGPT: "If I want to think of general things that humans produce as 
being constructed via steps, what would the inputs to those steps be?"


It responded: "To think about the inputs required for the construction of general things that humans produce, you can consider the following categories:

1) Raw Materials: Basic substances needed for production (e.g., wood, metal, fabric).

2) Tools and Equipment: Instruments required to manipulate raw materials (e.g., saws, hammers, machines).

3) Energy Sources: Power needed to perform tasks (e.g., electricity, fuel, human labor).

4) Knowledge and Skills: Expertise required to execute the processes effectively (e.g., craftsmanship, engineering).

5) Time: Duration needed to complete the construction process.

These inputs collectively contribute to the steps involved in producing various human-made items."


I will ask it for a breakdown of these items through the API, but will 
prioritize 1 and 2 first.

"""

import os
import subprocess

# This is read only for this program because we're just reading things in.
# I will need to store user state (possibly), but it goes elsewhere.
import fctcdb
ITEMDB = None
POSSIBLEITEMSTATS = {}   # What the user could possibly make.   Only picks ones
                         # that are user requested.   Contains stats

def init_stats_if_needed():

    def _get_user_requested(item):
        return item.user_requested

    global POSSIBLEITEMSTATS
    POSSIBLEITEMSTATS = {}
    possibleitems = ITEMDB.filter_items(_get_user_requested)
    for item in possibleitems:
        iteminfo = ITEMDB.get_item_count(item)

        # get a count of these...
        uniqueitems = iteminfo['uniquetools']+iteminfo['uniqueraw_materials']
        totalitems = iteminfo['totaltools']+iteminfo['totalraw_materials']

        thisitem = {'label': item, 'url': url_for('game', item_name=item, exploration_path=item, item_to_add=''), 'uniqueitems': uniqueitems, 'totalitems': totalitems}
        POSSIBLEITEMSTATS[item] = thisitem




# This is keyed by the session ID, and contains the user state.
# thw structure is:
# {'state': the state for the boxes.   This is a dict keyed session info, which
# is then a dict of the boxes
userstatedict = {}


from random import choice # to pick a random item


####### COMMON FLASK SETUP #######

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required, UserMixin
from flask_dance.contrib.google import make_google_blueprint, google
import secrets

app = Flask(__name__)

# Set the secret key to a random value for signing session data
# You should replace this with a more secure method to generate and store the key
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))


####### USER AUTHENTICATION #######

# --- Database setup ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fctc.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
USERDB = SQLAlchemy(app)

# --- Login manager ---
login_manager = LoginManager(app)
login_manager.login_view = 'register'


def finalize_login(user):

    # First log them in
    login_user(user)

    session['user_id'] = user.id

    # if we weren't a guest user, return.   Otherwise migrate data over
    guest_id = session.get('guest_id')
    if not guest_id:
        return

    session.pop('guest_id', None)

    # 2) Get the set of item names the user already has
    existing_names = { item.name for item in user.known_items.all() }

    # 3) Query all items belonging to the guest
    guest_items = Item.query.filter_by(guest_id=guest_id).all()

    for gi in guest_items:
        if gi.name in existing_names:
            # 4a) Duplicate — just delete the guest record
            USERDB.session.delete(gi)
        else:
            # 4b) New to the user — migrate it
            gi.user_id = user.id
            gi.guest_id = None

    # 5) Commit all deletes/updates in one transaction
    USERDB.session.commit()

    if guest_id in userstatedict:
        # copy the user's state over (what boxes are filled)...
        userstatedict[user.id] = userstatedict.pop(guest_id)



# --- OAuth (Google example) ---
google_bp = make_google_blueprint(
    client_id="GOOGLE_CLIENT_ID",
    client_secret="GOOGLE_CLIENT_SECRET",
    scope=["profile", "email"],
    redirect_url="/oauth_callback"
)
app.register_blueprint(google_bp, url_prefix="/login")


# wipes all guest items.  
# TODO: If I was running a production service, I'd track the age of these
# and clean them up every day or so
def _clean_guest_items():
    Item.query.filter(Item.guest_id.isnot(None),
                      Item.user_id.is_(None)).delete()

# --- Known Item model ---
class Item(USERDB.Model):
    id      = USERDB.Column(USERDB.Integer, primary_key=True)
    name    = USERDB.Column(USERDB.String(120), nullable=False)
    user_id = USERDB.Column(USERDB.Integer, USERDB.ForeignKey('user.id'), nullable=True)
    guest_id = USERDB.Column(USERDB.String(36), nullable=True, index=True)

# --- User model ---
class User(UserMixin, USERDB.Model):
    id = USERDB.Column(USERDB.Integer, primary_key=True)
    username = USERDB.Column(USERDB.String(80), unique=True, nullable=True)
    # These are used to handle storing state for users / guests.
    guest_id = USERDB.Column(USERDB.String(36), nullable=True, index=True)

    password_hash = USERDB.Column(USERDB.String(128), nullable=True)
    oauth_provider = USERDB.Column(USERDB.String(50), nullable=True)
    oauth_id = USERDB.Column(USERDB.String(200), nullable=True)

    # one‐to‐many relationship: user.items will be a list of Item objects
    known_items = USERDB.relationship('Item', backref='user', lazy='dynamic')

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd,method='pbkdf2:sha256', salt_length=16)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Providing a uniform replacement for current_user ---

class UserProxy:
    def __init__(self, user=None, guest_id=None):
        self._user = user
        self._guest_id = guest_id

    @property
    def is_authenticated(self):
        return self._user is not None

    @property
    def username(self):
        return self._user.username if self._user else 'Guest'

    @property
    def known_items(self):
        if self._user:
            # this is a dynamic relationship: a BaseQuery
            return self._user.known_items
        else:
            # filter guest items by guest_id
            return Item.query.filter_by(guest_id=self._guest_id)

def get_current_user():
    """Return a UserProxy always, wrapping either a real user or a guest."""
    user = None
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
    guest_id = session.get('guest_id')
    return UserProxy(user=user, guest_id=guest_id)

@app.context_processor
def inject_user():
    return {'current_user': get_current_user()}

# --- Registration & login routes ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    error = None
    if request.method == "POST":
        username = request.form['username'].strip()
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            error = "Username already taken."
        else:
            user = User(username=username)
            user.set_password(password)
            USERDB.session.add(user)
            USERDB.session.commit()
            # Log in the user
            finalize_login(user)
            return redirect(url_for('home'))

    return render_template("register.html", error=error)



# --- OAuth callback ---
@app.route("/oauth_callback")
def oauth_callback():
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "error")
        return redirect(url_for('register'))

    info = resp.json()
    oauth_id = info["id"]
    provider = "google"
    user = User.query.filter_by(oauth_provider=provider, oauth_id=oauth_id).first()

    if not user:
        # Create new user record without a local password
        user = User(
            username=info.get("name"),
            oauth_provider=provider,
            oauth_id=oauth_id
        )
        USERDB.session.add(user)
        USERDB.session.commit()

    # Log in the user
    finalize_login(user)
    return redirect(url_for('home'))


# --- Login route ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        finalize_login(user)
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)  # marks them as logged in in the session
            next_page = request.args.get('next') or url_for('home')
            finalize_login(user)
            return redirect(next_page)
        else:
            return render_template('login.html', error="Invalid username or password.")

    return render_template('login.html')

# --- Logout route ---
@app.route('/logout')
@login_required
def logout():
    logout_user()   # clears the user from the session
    session.clear()  # clears the session data
    return redirect(url_for('home'))

# --- Guest ID ---
import uuid

@app.before_request
def ensure_guest_id():
    if 'guest_id' not in session:
        session['guest_id'] = str(uuid.uuid4())


####### WEBSERVER #######

# I'm going to create a webserver and have users interact with this using
# their webbrowser.

from flask import Flask, session, redirect, url_for, request, jsonify, render_template


from functools import wraps

# If you aren't logged in, redirect to the home page.
# This must be the last decorator before the function definition.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def ensure_guest_id():
    if 'guest_id' not in session:
        session['guest_id'] = secrets.token_hex(16)


def _get_user_id():
    if 'user_id' in session:
        return session['user_id']
    else:
        return session['guest_id']


def _get_git_version():
    """Get the current git commit hash."""
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], 
                                      stderr=subprocess.DEVNULL).strip().decode('utf-8')[:8]
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown"

@app.route("/")
@app.route("/home")
def home():
#
    uid = _get_user_id()
    if uid not in userstatedict:
        # Initialize user state
        userstatedict[uid]={}
        userstatedict[uid]['state'] = {}

    # Get the git version
    git_version = _get_git_version()

    # Generate the home page with links
    return render_template("home.html", 
                          current_user=current_user, 
                          backurl=url_for("home"),
                          git_version=git_version)


@app.route("/credits")
def credits():
    # Render the credits page with placeholder text
    return render_template("credits.html", current_user=current_user)


@app.route("/suggestion", methods=["POST"])
def suggestion():
    user_input = request.form.get("suggestion_text", "").strip()
    if not user_input:
        return jsonify(success=False, error="Empty suggestion"), 400

    global SUGGESTIONLOG
    SUGGESTIONLOG.write(user_input + "\n")
    SUGGESTIONLOG.flush()

    return jsonify(success=True)




# Dummy default user settings
DEFAULT_SETTINGS = {
    "only_useful": True,
    "skip_intro": False,
    "skip_make_text": False
}

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    session_id = _get_user_id()

    back_url = request.args.get("back_url", url_for("home"))

    # On POST, update the settings and redirect back to GET
    if request.method == "POST":
        # Read your toggles (they come in as strings "yes"/"no")
        only_useful = request.form.get("only_useful") == "yes"
        skip_intro  = request.form.get("skip_intro")  == "yes"
        skip_make_text  = request.form.get("skip_make_text")  == "yes"
        # Store in session or database; here we use session for simplicity
        session["settings"] = {
            "only_useful": only_useful,
            "skip_intro": skip_intro,
            "skip_make_text": skip_make_text
        }
        return redirect(url_for("profile", back_url=back_url))

    # On GET, load settings (fall back to defaults)
    settings = session.get("settings", DEFAULT_SETTINGS.copy())


    return render_template(
        "profile.html",
        current_user=current_user,
        session_id=session_id,
        settings=settings,
        back_url=back_url
    )

@app.route("/clear_account")
def clear_account():
    # Clear all user‐specific session state
    session.clear()
    return redirect(url_for("profile",back_url=url_for("home")))

@app.route('/win')
@login_required
def win():
    init_stats_if_needed()
    current_item = request.args.get('item_name', '', type=str)
    if not current_item:
        return redirect(url_for('home'))

    return render_template("win.html", item_name=current_item, uniqueitems=POSSIBLEITEMSTATS[current_item]['uniqueitems'], totalitems=POSSIBLEITEMSTATS[current_item]['totalitems'],current_user=current_user)



def _get_box(boxid, item, shape,exploration_path=None):

    thisitem = ITEMDB.items[item]
    thisbox = {'id': boxid, 'accepts': thisitem.name, 'shape': shape, 'description': thisitem.description}

    if hasattr(ITEMDB.items[item],'steps') and ITEMDB.items[item].steps:
        thisbox['arrow_url'] = url_for('game', item_name=thisitem.name, exploration_path=exploration_path+'/'+thisitem.name,item_to_add='')

    return thisbox


def _step_to_box_groups(steps,exploration_path=None):
    """
    Convert steps to box groups.
    """
    box_groups = []
    boxid = 0
    for step in steps:
        thisbg = {}
        thisbg['label'] = step['step']
        thisbg['description'] = step['description']
        thisbg['boxes'] = []
        for item in step['raw_materials']:
            thisbg['boxes'].append(_get_box(boxid, item, 'oval',exploration_path=exploration_path))
            boxid += 1

        for item in step['tools']:
            thisbg['boxes'].append(_get_box(boxid, item, 'square',exploration_path=exploration_path))
            boxid += 1

        box_groups.append(thisbg)

    return box_groups
        
def _get_item(item,shape):
    return {'name':item,'url':ITEMDB.items[item].image[0]['link'],'shape':shape,'description':ITEMDB.items[item].description} 

def _get_base_items(box_groups):
    """
    Get the base items from the box groups.
    """
    base_items = []
    for bg in box_groups:
        for box in bg['boxes']:
            if not 'arrow_url' in box:
                thisitem = _get_item(box['accepts'],box['shape'])
                if thisitem not in base_items:
                    base_items.append(thisitem)
    return base_items

def _get_page_data(current_item,exploration_path=None):
    """
    Get the page data for the current item number.
    """

    header_title = ITEMDB.items[current_item].name
    box_groups = _step_to_box_groups(ITEMDB.items[current_item].steps,exploration_path=exploration_path)

    boxes = []
    for bg in box_groups:
        for box in bg['boxes']:
            boxes.append(box)

    # get the images, if they exist.
    if hasattr(ITEMDB.items[current_item],'image') and len(ITEMDB.items[current_item].image) > 0:
        header_image_url = ITEMDB.items[current_item].image[0]['thumbnailLink']
        completion_image_url = ITEMDB.items[current_item].image[0]['link']
    else:
        header_image_url = "/static/images/default.png"
        completion_image_url = "/static/images/default.png"

    # get the description, if it exists.
    if hasattr(ITEMDB.items[current_item],'description'):
        page_description = ITEMDB.items[current_item].description
    else:
        page_description = "No description available."

    base_items = _get_base_items(box_groups)
    
    return {
            'header_title':header_title,
            'box_groups':box_groups,
            'boxes':boxes,
            'header_image_url':header_image_url,
            'completion_image_url':completion_image_url,
            'page_description':page_description,
            'base_items':base_items
            }

def _get_header_tags(exploration_path):
    result=[]
    tagsofar = ""
    for tag in exploration_path.split('/'):
        if tagsofar == "":
            tagsofar = tag
        else:
            tagsofar = tagsofar + "/" + tag

        url = url_for('game', item_name=tag, exploration_path=tagsofar, item_to_add='')
        result.append({'label': tag, 'url': url})
    return result


@app.route('/choose')
@login_required
def choose():
    # This is the page where the user chooses what they want to make.
    
    init_stats_if_needed()

    # Generate the home page with links
    return render_template("choose.html", possibleitems=POSSIBLEITEMSTATS.values(), current_user=current_user)


def get_known_items():
    # 1) If they’re logged in…
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            # returns a list via the dynamic relationship
            retitemnames = []
            for item in user.known_items:
                retitemnames.append(item.name)
            return retitemnames

    # 2) Otherwise, treat them as guest
    guest_id = session.get('guest_id')
    if guest_id:
        retitemnames = []
        for item in Item.query.filter_by(guest_id=guest_id).all():
            retitemnames.append(item.name)
        return retitemnames

    print(f"Error: No user or guest ID found in get_known_items.")
    # 3) Fallback: nobody to track
    return []

def _add_known_item_to_current_user(item):
    # This is a helper function to add a known item to the user.
    if item not in get_known_items():
        # automatically converts current_user to the correct foreign key
        if current_user.is_authenticated:
            new_item = Item(name=item, user_id=current_user.id)
        else:
            new_item = Item(name=item, guest_id=session['guest_id'])
        USERDB.session.add(new_item)
        USERDB.session.commit()
        return True
    return False

def _get_image_boxes(availableitems,box_groups):
    """
    Get the image boxes for the current item number.
    """
    unseenitems = availableitems[:]
    imageboxes = []
    for bg in box_groups:
        for box in bg['boxes']:
            if box['accepts'] in unseenitems:
                unseenitems.remove(box['accepts'])
                imageboxes.append(_get_item(box['accepts'],box['shape']))

    return imageboxes


@app.route('/game')
@login_required
def game():

    init_stats_if_needed()
    current_item = request.args.get('item_name', choice(list(POSSIBLEITEMSTATS.keys())), type=str)


    uid = _get_user_id()
    if current_item not in userstatedict[uid]['state']:
        # If the item is not in the user's state, add it
        userstatedict[uid]['state'][current_item] = {}

    exploration_path = request.args.get('exploration_path', current_item, type=str)
    page_data = _get_page_data(current_item,exploration_path=exploration_path)

    box_groups = page_data['box_groups']
    boxes = page_data['boxes']
    header_image_url = page_data['header_image_url']
    header_title = page_data['header_title']
    completion_image_url = page_data['completion_image_url']
    page_description = page_data['page_description']

    base_items = page_data['base_items']

    # TODO: Make this a splash page that comes up first...

    new_items = []
    # If I didn't know this, add it.
    for item in base_items:
        if _add_known_item_to_current_user(item['name']):
            new_items.append(item['name'])

    # If we just finished something, add it...
    item_to_add = request.args.get('item_to_add', '', type=str)
    if item_to_add != '':
        if item_to_add in get_known_items():
            # This is an error, because we already know this item.
            print(f"Error: {item_to_add} already known.")
        else:
            _add_known_item_to_current_user(item_to_add)

    # Exploration path is a string of tags separated by slashes
    header_tags = _get_header_tags(exploration_path)

    # Build the 'completed / won URL!'
    if len(header_tags) > 1:
        parent_path = exploration_path.rsplit('/', 1)[0]
        completion_url=url_for('game', item_name=header_tags[-2]['label'], exploration_path=parent_path, item_to_add=current_item)
    else:
        completion_url=url_for('win', item_name=current_item)

    availableitems = get_known_items()

    imageboxes = _get_image_boxes(availableitems,box_groups)
    

    return render_template(
        'game.html',
        header_image_url=header_image_url,
        header_title=header_title,
        header_tags=header_tags,
        box_groups=box_groups,
        completion_image_url=completion_image_url,
        page_description=page_description,
        item_name=current_item,
        new_items=new_items,
        exploration_path=exploration_path,
        boxes=boxes, 
        settings=session.get("settings", DEFAULT_SETTINGS.copy()),
        box_fills=userstatedict[uid]['state'][current_item],
        images=imageboxes,
        completion_url=completion_url,
    )

@login_required
@app.route('/drop', methods=['POST'])
def handle_drop():


    data = request.get_json()
    # What they dropped and where they dropped it
    image_name = data.get('name')
    image_url = data.get('image_url')
    box_id = data.get('box_id')

    uid = _get_user_id()

    # figure out enough to know if this is a valid box
    current_item = data.get('item_name')
    exploration_path = data.get('exploration_path')
    page_data = _get_page_data(current_item,exploration_path=exploration_path)

    # This shouldn't happen, because the game page should initialize this.
    if current_item not in userstatedict[uid]['state']:
        print(f"Error: {current_item} not in user state.")
        # If the item is not in the user's state, add it
        userstatedict[uid]['state'][current_item] = {}

    mystate = userstatedict[uid]['state'][current_item]

    # Prevent re-filling an already-filled box
    if box_id in mystate:
        print(f"Error: {box_id} already filled.")
        return jsonify({'status': 'already-filled'})

    # see if the image_name matches the accepted value
    for box in page_data['boxes']:
        # I'm not sure why box_id is a string and box['id'] is an int.  I'll
        # convert
        if str(box['id']) == box_id:
            # This is the box we are looking for
            if box['accepts'] == image_name:
                mystate[box_id] = image_url
                return jsonify({'status': 'locked'})
    else:
        return jsonify({'status': 'rejected'})



@app.route('/problem', methods=['GET', 'POST'])
def problem():

    if request.method == 'POST':
        # Process the form submission
        selected_image = request.form['selected_image_id']
        item_name = request.form['item_name']
        desc_accurate = request.form['description_accurate']
        correct_item = request.form['correct_item']
        good_image = request.form['good_image']
        referrer = request.form['referrer']

        # make this image the preferred one!
        if selected_image != '' and selected_image != '0':
            selected_image_no = int(selected_image)
            goodimage = ITEMDB.items[item_name].image.pop(selected_image_no)
            ITEMDB.items[item_name].image.insert(0,goodimage)
            ITEMDB.save()

        if selected_image and selected_image != '0':
            do_log(f"IMAGE_INACCURATE: {item_name}")
        if desc_accurate == 'no':
            do_log(f"DESC_INACCURATE: {item_name}")
        if correct_item == 'no':
            do_log(f"ITEM_INACCURATE: {item_name}")
        if good_image == 'no':
            do_log(f"ALL_IMAGES_INACCURATE: {item_name}")

        # Redirect to your desired URL
        return redirect(referrer)

    # I think this will always be filled in as an arg.   If not, use the
    # request.referrer from Flask
    referrer = request.args.get('referrer', request.referrer, type=str)

    item_name = request.args.get('item_name', '', type=str)
    description = ITEMDB.items[item_name].description

    imagelist = []
    for count,image in enumerate(ITEMDB.items[item_name].image):
        imagelist.append({'id': f"{count}", 'url': image['link']})

    return render_template("problem.html",
                           item_name=item_name,
                           description=description,
                           images=imagelist,
                           referrer=referrer,
                           post_url=url_for('problem'))




def run_webserver(hostname="localhost", port=59722):
    # Start the Flask web server
    app.run(host=hostname, port=port)


####### LOGGING #######



def do_log(logmessage):
    print(logmessage)
    LOGFILE.write(logmessage + "\n")


####### MAIN / ARGUMENT PARSING #######


import argparse

def main(clouddeploy=False):
    VERSION = "1.0.0"

    # This "database" is read only for this program.
    global ITEMDB
    ITEMDB = fctcdb.ItemDB("itemdb.json")
    ITEMDB.prevent_infinite_recursion()

    if clouddeploy:
        # Use defaults without argument parsing
        logfile = "problems.log"
        suggestionlog = "suggestions.log"
        ip = "0.0.0.0"
        port = int(os.environ.get("PORT", 8080))
    else:
        # Create the argument parser
        parser = argparse.ArgumentParser(
            description="From Caves To Cars Game Server. Runs the game server locally",
            usage="%(prog)s [options]"
        )

        # Add optional arguments for IP and port
        parser.add_argument("-i", "--ip", type=str, default="localhost", help="IP address for the web server (default: localhost)")
        parser.add_argument("-p", "--port", type=int, default=59722, help="Port number for the web server (default: 59722)")
        parser.add_argument("-s", "--suggestionlog", type=str, default="suggestions.log", help="Logfile for suggestions")
        parser.add_argument("-l", "--logfile", type=str, default="problems.log", help="Logfile for errors and issues")
        parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {VERSION}", help="Show version and exit")

        args = parser.parse_args()

        logfile = args.logfile
        suggestionlog = args.suggestionlog
        ip = args.ip
        port = args.port

    # Open log files
    global LOGFILE
    LOGFILE = open(logfile, "a+")

    global SUGGESTIONLOG
    SUGGESTIONLOG = open(suggestionlog, "a+")

    # Initialize user database
    with app.app_context():
        USERDB.create_all()

    # Run the web server, if I'm not in the cloud.   Otherwise gunicorn runs as
    # my web server.
    if not clouddeploy:
        print(f"Starting the web server with IP: {ip} and Port: {port}")
        print("Interrupt with Ctrl-C.")
        run_webserver(hostname=ip, port=port)

if __name__ == "__main__":
    main()

