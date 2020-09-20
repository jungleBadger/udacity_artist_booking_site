import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import cast, String, func, distinct, ARRAY, Table
from sqlalchemy.dialects import postgresql
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from flask_migrate import Migrate
from forms import *
from model import Venue, Artist, Show

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "MM, d, y 'at' h:m"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


@app.route('/')
def index():
    return render_template('pages/home.html')


'''
VENUES
'''


@app.route('/venues')
def venues():
    data = Venue.query.with_entities(Venue.city, Venue.state,
                                     postgresql.array_agg(
                                         func.json_build_object('id', Venue.id, 'name', Venue.name)).label('venues')) \
        .group_by(Venue.city, Venue.state).all()
    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    data = dict(request.form or request.json or request.data)
    search_term = data.get('search_term')
    if search_term:
        venue_results = Venue.query.filter(Venue.name.ilike(
            f'%{search_term}%')
        ).all()

        response = {
            "count": len(venue_results),
            "data": [{
                "id": venue.id,
                "name": venue.name
            } for venue in venue_results]
        }

        return render_template('pages/search_venues.html', results=response,
                               search_term=search_term)
    else:
        return json.dumps({
            'success': False,
            'error': 'Missing params.'
        }), 400


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.filter_by(id=venue_id).one_or_none()
    if not venue:
        return json.dumps({
            'success':
                False,
            'error':
                'Venue #' + venue_id + ' not found'
        }), 404
    past_shows = []
    upcoming_shows = []
    available_shows = Show.query.filter_by(venue_id=venue_id).join(Artist, Show.artist_id == Artist.id).all()
    for show in available_shows:
        venue_show = {"artist_id": show.artist_id,
                      "artist_name": show.artist.name,
                      "artist_image_link": show.artist.image_link,
                      "start_time": str(show.start_time)
                      }

        current_date = datetime.now()

        if current_date < show.start_time:
            upcoming_shows.append(venue_show)
        else:
            past_shows.append(venue_show)

    data = {
        'id': venue.id,
        'name': venue.name,
        'genres': venue.genres,
        'address': venue.address,
        'city': venue.city,
        'state': venue.state,
        'phone': venue.phone,
        'image_link': venue.image_link,
        'facebook_link': venue.facebook_link,
        'seeking_talent': venue.seeking_talent,
        'seeking_description': venue.seeking_description,
        'website': venue.website,
        'past_shows': past_shows,
        'upcoming_shows': upcoming_shows,
        'past_shows_count': len(past_shows),
        'upcoming_shows_count': len(upcoming_shows),
    }

    return render_template('pages/show_venue.html', venue=data)


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    return render_template('forms/new_venue.html', form=VenueForm())


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    try:
        form = VenueForm(request.form)
        venue = Venue(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            address=form.address.data,
            phone=form.phone.data,
            genres=form.genres.data,
            facebook_link=form.facebook_link.data,
            image_link=form.image_link.data
        )

        db.session.add(venue)
        db.session.commit()
        flash('Venue: {0} created successfully'.format(venue.name))
    except Exception as err:
        flash('An error occurred creating the Venue: {0}. Error: {1}'.format(venue.name, err))
        db.session.rollback()
    finally:
        db.session.close()

    return render_template('pages/home.html'), 201


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    existing_venue = Venue.query.filter_by(id=venue_id).one_or_none()
    if not existing_venue:
        return json.dumps({
            'success':
                False,
            'error':
                'Venue #' + venue_id + ' not found'
        }), 404
    else:
        try:
            Venue.query.filter_by(id=venue_id).delete()
            db.session.commit()
            flash('Venue: {0} deleted successfully'.format(venue_id))
        except Exception as err:
            db.session.rollback()
            flash('An error occurred deleting the Venue: {0}. Error: {1}'.format(venue_id, err))
        finally:
            db.session.close()

        return venue_id


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue_form(venue_id):
    existing_venue = Venue.query.filter_by(id=venue_id).one_or_none()
    if not existing_venue:
        return json.dumps({
            'success':
                False,
            'error':
                'Venue #' + venue_id + ' not found'
        }), 404
    else:
        venue = {
            "id": existing_venue.id,
            "name": existing_venue.name,
            "genres": existing_venue.genres,
            "address": existing_venue.address,
            "city": existing_venue.city,
            "state": existing_venue.state,
            "phone": existing_venue.phone,
            "website": existing_venue.website,
            "facebook_link": existing_venue.facebook_link,
            "seeking_talent": existing_venue.seeking_talent,
            "seeking_description": existing_venue.seeking_description,
            "image_link": existing_venue.image_link
        }

        return render_template('forms/edit_venue.html', form=VenueForm(), venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['PATCH'])
def edit_venue_submission(venue_id):
    existing_venue = Venue.query.filter_by(id=venue_id).one_or_none()
    if not existing_venue:
        return json.dumps({
            'success':
                False,
            'error':
                'Venue #' + venue_id + ' not found'
        }), 404
    else:
        form = VenueForm(request.form)
        existing_venue.name = form.name.data or existing_venue.name
        existing_venue.city = form.city.data or existing_venue.city
        existing_venue.state = form.state.data or existing_venue.state
        existing_venue.phone = form.phone.data or existing_venue.phone
        existing_venue.genres = form.genres.data or existing_venue.genres,
        existing_venue.facebook_link = form.facebook_link.data or existing_venue.facebook_link,
        existing_venue.image_link = form.image_link.data or existing_venue.image_link

        try:
            db.session.commit()
            flash('Venue: {0} edted successfully'.format(venue_id))
        except Exception as err:
            db.session.rollback()
            flash('An error occurred editing the Venue: {0}. Error: {1}'.format(venue_id, err))
        finally:
            db.session.close()

        return render_template('forms/edit_venue.html', form=VenueForm(), venue=existing_venue)


'''
ARTISTS
'''


@app.route('/artists')
def artists():
    available_artists = Artist.query.all()
    return render_template('pages/artists.html',
                           artists=[{'id': artist.id, 'name': artist.name} for artist in available_artists])


@app.route('/artists/search', methods=['POST'])
def search_artists():
    data = dict(request.form or request.json or request.data)
    search_term = data.get('search_term')
    if search_term:
        artist_results = Artist.query.filter(Artist.name.ilike(
            f'%{search_term}%')
        ).all()

        response = {
            "count": len(artist_results),
            "data": [{
                "id": artist.id,
                "name": artist.name
            } for artist in artist_results]
        }

        return render_template('pages/search_artists.html', results=response,
                               search_term=search_term)
    else:
        return json.dumps({
            'success': False,
            'error': 'Missing params.'
        }), 400


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = Artist.query.filter_by(id=artist_id).one_or_none()

    if not artist:
        return json.dumps({
            'success':
                False,
            'error':
                'Artist #' + artist_id + ' not found'
        }), 404

    past_shows = []
    upcoming_shows = []
    available_shows = Show.query.filter_by(artist_id=artist_id).join(Venue, Show.venue_id == Venue.id).all()
    for show in available_shows:
        artist_show = {"venue_id": show.venue_id,
                       "venue_name": show.venue.name,
                       "venue_image_link": show.venue.image_link,
                       "start_time": str(show.start_time)
                       }

        current_date = datetime.now()

        if current_date < show.start_time:
            upcoming_shows.append(artist_show)
        else:
            past_shows.append(artist_show)

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "seeking_venue": artist.seeking_venue,
        "image_link": artist.image_link,
        "facebook_link": artist.facebook_link,
        "seeking_description": artist.seeking_description,
        "website": artist.website,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_artist.html', artist=data)


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    existing_artist = Artist.query.filter_by(id=artist_id).one_or_none()
    if not existing_artist:
        return json.dumps({
            'success':
                False,
            'error':
                'Artist #' + artist_id + ' not found'
        }), 404
    else:
        artist = {
            "id": existing_artist.id,
            "name": existing_artist.name,
            "genres": existing_artist.genres,
            "city": existing_artist.city,
            "state": existing_artist.state,
            "phone": existing_artist.phone,
            "website": existing_artist.website,
            "facebook_link": existing_artist.facebook_link,
            "seeking_venue": existing_artist.seeking_venue,
            "seeking_description": existing_artist.seeking_description,
            "image_link": existing_artist.image_link
        }

        return render_template('forms/edit_artist.html', form=ArtistForm(), artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['PATCH'])
def edit_artist_submission(artist_id):
    existing_artist = Artist.query.filter_by(id=artist_id).one_or_none()
    if not existing_artist:
        return json.dumps({
            'success':
                False,
            'error':
                'Artist #' + artist_id + ' not found'
        }), 404
    else:
        form = ArtistForm(request.form)

        existing_artist.name = form.name.data or existing_artist.name
        existing_artist.city = form.city.data or existing_artist.city
        existing_artist.state = form.state.data or existing_artist.state
        existing_artist.phone = form.phone.data or existing_artist.phone
        existing_artist.genres = form.genres.data or existing_artist.genres
        existing_artist.facebook_link = form.facebook_link.data or existing_artist.facebook_link
        existing_artist.image_link = form.image_link.data or existing_artist.image_link
        try:
            db.session.commit()
            flash('Artist: {0} edited successfully'.format(artist_id))
        except Exception as err:
            db.session.rollback()
            flash('An error occurred editing the Artist: {0}. Error: {1}'.format(artist_id, err))
        finally:
            db.session.close()

        return redirect('/artist/' + artist_id)


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    try:
        form = ArtistForm(request.form)
        artist = Artist(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            phone=form.phone.data,
            genres=form.genres.data,
            facebook_link=form.facebook_link.data,
            image_link=form.image_link.data
        )

        db.session.add(artist)
        db.session.commit()
        flash('Artist: {0} created successfully'.format(artist.name))
    except Exception as err:
        flash('An error occurred creating the Venue: {0}. Error: {1}'.format(artist.name, err))
        db.session.rollback()
    finally:
        db.session.close()

    return render_template('pages/home.html'), 201


'''
SHOWS
'''


@app.route('/shows')
def shows():
    available_shows = Show.query.join(Venue, Show.venue_id == Venue.id).join(Artist, Show.artist_id == Artist.id).all()

    return render_template('pages/shows.html', shows=[{
        "venue_id": show.venue_id,
        "venue_name": show.venue.name,
        "artist_id": show.artist_id,
        "artist_name": show.artist.name,
        "artist_image_link": show.artist.image_link,
        "start_time": format_datetime(str(show.start_time), format='full')
    } for show in available_shows])


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    try:
        form = ShowForm(request.form)

        show = Show(
            artist_id=form.artist_id.data,
            venue_id=form.venue_id.data,
            start_time=form.start_time.data
        )
        db.session.add(show)
        db.session.commit()
        flash('Show: {0} created successfully'.format(show.id))
    except Exception as err:
        flash('An error occurred creating the Show: {0}. Error: {1}'.format(show.id, 'Invalid information'))
        db.session.rollback()
    finally:
        db.session.close()

    return render_template('pages/home.html'), 201


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

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
