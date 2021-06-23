# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func
import logging
from logging import Formatter, FileHandler
from forms import *
import sys

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    genres = db.Column(db.ARRAY(db.String()))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref='Venue', lazy=True)

    def __repr__(self):
        return f'Venue {self.name}'


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String()))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref='Artist', lazy=True)

    def __repr__(self):
        return f'Artist {self.name}'

class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'Show artist_id: {self.artist_id} venue_id: {self.venue_id}'


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    all_locations = db.session.query(func.count(Venue.id), Venue.city, Venue.state) \
        .group_by(Venue.city, Venue.state).all()
    data = []

    for location in all_locations:
        city = location[1]
        state = location[2]
        location_venues = db.session.query(Venue).filter_by(city=city).filter_by(state=state).all()
        venues_data = []
        for venue in location_venues:
            venues_data.append({
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": len(db.session.query(Show).filter(not Show.venue_id)
                                          .filter(Show.start_time > datetime.now()).all())
            })
        data.append({
            "city": city,
            "state": state,
            "venues": venues_data
        })
    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    result = db.session.query(Venue).filter(Venue.name.ilike(f'%{search_term}%')).all()
    data = []

    for venue in result:
        data.append({
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": len(
                db.session.query(Show).filter(Show.venue_id == venue.id).filter(Show.start_time > datetime.now()).all())
        })
    response = {
        "count": len(result),
        "data": data
    }
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = db.session.query(Venue).get(venue_id)

    if not venue:
        return render_template('errors/404.html')

    venue_artists_shows_upcoming = db.session.query(Show).join(Artist).filter(Show.venue_id == venue_id) \
        .filter(Show.start_time > datetime.now()).all()

    shows_upcoming = []

    for show in venue_artists_shows_upcoming:
        shows_upcoming.append({
            "artist_id": show.artist_id,
            "artist_name": show.Artist.name,
            "artist_image_link": show.Artist.image_link,
            "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    venue_artists_shows_history = db.session.query(Show).join(Artist).filter(Show.venue_id == venue_id) \
        .filter(Show.start_time <= datetime.now()).all()

    shows_history = []

    for show in venue_artists_shows_history:
        shows_history.append({
            "artist_id": show.artist_id,
            "artist_name": show.Artist.name,
            "artist_image_link": show.Artist.image_link,
            "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.website,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": shows_history,
        "upcoming_shows": shows_upcoming,
        "past_shows_count": len(shows_history),
        "upcoming_shows_count": len(shows_upcoming),
    }
    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

    is_error = False

    try:
        new_venue = Venue()
        new_venue.name = request.form['name']
        new_venue.genres = request.form.getlist('genres')
        new_venue.city = request.form['city']
        new_venue.state = request.form['state']
        new_venue.address = request.form['address']
        new_venue.phone = request.form['phone']
        new_venue.website = request.form['website']
        new_venue.image_link = request.form['image_link']
        new_venue.facebook_link = request.form['facebook_link']
        new_venue.seeking_talent = True if 'seeking_talent' in request.form else False
        new_venue.seeking_description = request.form['seeking_description']

        db.session.add(new_venue)
        db.session.commit()
    except:
        is_error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if is_error:
        flash('An error occurred. Venue ' + request.form.get('name') + ' could not be listed.')
    else:
        flash('Venue ' + request.form.get('name') + ' was successfully listed!')

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    is_error = False
    try:
        venue = db.session.query(Venue).get(venue_id)
        db.session.delete(venue)
        db.session.commit()
    except:
        is_error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if is_error:
        flash(f'An error occurred. Venue could not be deleted')
    else:
        flash(f'Venue was successfully deleted.')

    return render_template('pages/home.html')


@app.route('/artists/<artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    is_error = False
    try:
        artist = db.session.query(Artist).get(artist_id)
        db.session.delete(artist)
        db.session.commit()
    except:
        is_error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if is_error:
        flash(f'An error occurred. Artist could not be deleted')
    else:
        flash(f'Artist was successfully deleted.')

    return render_template('pages/home.html')


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = db.session.query(Artist).all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    result = db.session.query(Artist).filter(Artist.name.ilike(f'%{search_term}%')).all()
    data = []

    for artist in result:
        data.append({
            "id": artist.id,
            "name": artist.name,
            "num_upcoming_shows": len(
                db.session.query(Show).filter(Show.venue_id == artist.id).filter(
                    Show.start_time > datetime.now()).all())
        })
    response = {
        "count": len(result),
        "data": data
    }
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = db.session.query(Artist).get(artist_id)

    if not artist:
        return render_template('errors/404.html')

    venue_artists_shows_upcoming = db.session.query(Show).join(Venue).filter(Show.artist_id == artist_id) \
        .filter(Show.start_time > datetime.now()).all()

    shows_upcoming = []

    for show in venue_artists_shows_upcoming:
        shows_upcoming.append({
            "venue_id": show.venue_id,
            "venue_name": show.Venue.name,
            "venue_image_link": show.Venue.image_link,
            "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    venue_artists_shows_history = db.session.query(Show).join(Venue).filter(Show.artist_id == artist_id) \
        .filter(Show.start_time <= datetime.now()).all()

    shows_history = []

    for show in venue_artists_shows_history:
        shows_history.append({
            "venue_id": show.venue_id,
            "venue_name": show.Venue.name,
            "venue_image_link": show.Venue.image_link,
            "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.website,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "past_shows": shows_history,
        "upcoming_shows": shows_upcoming,
        "past_shows_count": len(shows_history),
        "upcoming_shows_count": len(shows_upcoming),
    }
    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = db.session.query(Artist).get(artist_id)

    if not artist:
        return render_template('errors/404.html')

    # fill form
    form.name.data = artist.name
    form.genres.data = artist.genres
    form.city.data = artist.city
    form.state.data = artist.state
    form.phone.data = artist.phone
    form.website.data = artist.website
    form.facebook_link.data = artist.facebook_link
    form.image_link.data = artist.image_link
    form.seeking_venue.data = artist.seeking_venue
    form.seeking_description.data = artist.seeking_description

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    is_error = False
    artist = db.session.query(Artist).get(artist_id)

    try:
        artist.name = request.form['name']
        artist.genres = request.form.getlist('genres')
        artist.city = request.form['city']
        artist.state = request.form['state']
        artist.phone = request.form['phone']
        artist.website = request.form['website']
        artist.facebook_link = request.form['facebook_link']
        artist.image_link = request.form['image_link']
        artist.seeking_venue = True if 'seeking_venue' in request.form else False
        artist.seeking_description = request.form['seeking_description']
        db.session.commit()
    except:
        is_error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if is_error:
        flash(f'An error occurred. Artist {artist.name} could not be updated.')
    else:
        flash(f'Artist {artist.name} is updated successfully!')

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = db.session.query(Venue).get(venue_id)

    if not venue:
        return render_template('errors/404.html')

    # fill form
    form.name.data = venue.name
    form.genres.data = venue.genres
    form.city.data = venue.city
    form.state.data = venue.state
    form.address.data = venue.address
    form.phone.data = venue.phone
    form.website.data = venue.website
    form.facebook_link.data = venue.facebook_link
    form.image_link.data = venue.image_link
    form.seeking_talent.data = venue.seeking_talent
    form.seeking_description.data = venue.seeking_description

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    is_error = False
    venue = db.session.query(Venue).get(venue_id)

    try:
        venue.name = request.form['name']
        venue.genres = request.form.getlist('genres')
        venue.city = request.form['city']
        venue.address = request.form['address']
        venue.state = request.form['state']
        venue.phone = request.form['phone']
        venue.website = request.form['website']
        venue.facebook_link = request.form['facebook_link']
        venue.image_link = request.form['image_link']
        venue.seeking_talent = True if 'seeking_talent' in request.form else False
        venue.seeking_description = request.form['seeking_description']
        db.session.commit()
    except:
        is_error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if is_error:
        flash(f'An error occurred. Venue {venue.name} could not be updated.')
    else:
        flash(f'Venue {venue.name} is updated successfully!')

    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    is_error = False

    try:
        new_artist = Artist()
        new_artist.name = request.form['name']
        new_artist.genres = request.form.getlist('genres')
        new_artist.city = request.form['city']
        new_artist.state = request.form['state']
        new_artist.phone = request.form['phone']
        new_artist.website = request.form['website']
        new_artist.facebook_link = request.form['facebook_link']
        new_artist.image_link = request.form['image_link']
        new_artist.seeking_venue = True if 'seeking_venue' in request.form else False
        new_artist.seeking_description = request.form['seeking_description']

        db.session.add(new_artist)
        db.session.commit()
    except:
        is_error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if is_error:
        flash('An error occurred. Artist ' + request.form.get('name') + ' could not be listed.')
    else:
        flash('Artist ' + request.form.get('name') + ' was successfully listed!')

    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    all_shows = db.session.query(Show).join(Artist).join(Venue).all()

    data = []

    for show in all_shows:
        data.append({
            "venue_id": show.venue_id,
            "venue_name": show.Venue.name,
            "artist_name": show.Artist.name,
            "artist_image_link": show.Artist.image_link,
            "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    is_error = False
    try:
        new_show = Show()
        new_show.artist_id = request.form['artist_id']
        new_show.venue_id = request.form['venue_id']
        new_show.start_time = request.form['start_time']

        db.session.add(new_show)
        db.session.commit()
    except:
        is_error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if is_error:
        flash(f'An error occurred. Show could not be listed.')
    else:
        flash(f'Show was successfully listed')

    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
