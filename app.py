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
                "name": venue.name,
                "num_upcoming_shows": Show.query.filter(Show.venue_id == venue.id,
                                                        Show.start_time > datetime.now()).count()
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
        flash('Venue: {0} created successfully'.format(request.form['name']))
    except Exception as err:
        flash('An error occurred creating the Venue: {0}. Error: {1}'.format(request.form['name'], err))
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
            "name": existing_venue.artist,
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
    data = [{
        "id": 4,
        "name": "Guns N Petals",
    }, {
        "id": 5,
        "name": "Matt Quevedo",
    }, {
        "id": 6,
        "name": "The Wild Sax Band",
    }]
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    response = {
        "count": 1,
        "data": [{
            "id": 4,
            "name": "Guns N Petals",
            "num_upcoming_shows": 0,
        }]
    }
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    data1 = {
        "id": 4,
        "name": "Guns N Petals",
        "genres": ["Rock n Roll"],
        "city": "San Francisco",
        "state": "CA",
        "phone": "326-123-5000",
        "website": "https://www.gunsnpetalsband.com",
        "facebook_link": "https://www.facebook.com/GunsNPetals",
        "seeking_venue": True,
        "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
        "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
        "past_shows": [{
            "venue_id": 1,
            "venue_name": "The Musical Hop",
            "venue_image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60",
            "start_time": "2019-05-21T21:30:00.000Z"
        }],
        "upcoming_shows": [],
        "past_shows_count": 1,
        "upcoming_shows_count": 0,
    }
    data2 = {
        "id": 5,
        "name": "Matt Quevedo",
        "genres": ["Jazz"],
        "city": "New York",
        "state": "NY",
        "phone": "300-400-5000",
        "facebook_link": "https://www.facebook.com/mattquevedo923251523",
        "seeking_venue": False,
        "image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
        "past_shows": [{
            "venue_id": 3,
            "venue_name": "Park Square Live Music & Coffee",
            "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
            "start_time": "2019-06-15T23:00:00.000Z"
        }],
        "upcoming_shows": [],
        "past_shows_count": 1,
        "upcoming_shows_count": 0,
    }
    data3 = {
        "id": 6,
        "name": "The Wild Sax Band",
        "genres": ["Jazz", "Classical"],
        "city": "San Francisco",
        "state": "CA",
        "phone": "432-325-5432",
        "seeking_venue": False,
        "image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
        "past_shows": [],
        "upcoming_shows": [{
            "venue_id": 3,
            "venue_name": "Park Square Live Music & Coffee",
            "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
            "start_time": "2035-04-01T20:00:00.000Z"
        }, {
            "venue_id": 3,
            "venue_name": "Park Square Live Music & Coffee",
            "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
            "start_time": "2035-04-08T20:00:00.000Z"
        }, {
            "venue_id": 3,
            "venue_name": "Park Square Live Music & Coffee",
            "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
            "start_time": "2035-04-15T20:00:00.000Z"
        }],
        "past_shows_count": 0,
        "upcoming_shows_count": 3,
    }
    data = list(filter(lambda d: d['id'] == artist_id, [data1, data2, data3]))[0]
    return render_template('pages/show_artist.html', artist=data)


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = {
        "id": 4,
        "name": "Guns N Petals",
        "genres": ["Rock n Roll"],
        "city": "San Francisco",
        "state": "CA",
        "phone": "326-123-5000",
        "website": "https://www.gunsnpetalsband.com",
        "facebook_link": "https://www.facebook.com/GunsNPetals",
        "seeking_venue": True,
        "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
        "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"
    }
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')


'''
SHOWS
'''


@app.route('/shows')
def shows():
    data = [{
        "venue_id": 1,
        "venue_name": "The Musical Hop",
        "artist_id": 4,
        "artist_name": "Guns N Petals",
        "artist_image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
        "start_time": "2019-05-21T21:30:00.000Z"
    }, {
        "venue_id": 3,
        "venue_name": "Park Square Live Music & Coffee",
        "artist_id": 5,
        "artist_name": "Matt Quevedo",
        "artist_image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
        "start_time": "2019-06-15T23:00:00.000Z"
    }, {
        "venue_id": 3,
        "venue_name": "Park Square Live Music & Coffee",
        "artist_id": 6,
        "artist_name": "The Wild Sax Band",
        "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
        "start_time": "2035-04-01T20:00:00.000Z"
    }, {
        "venue_id": 3,
        "venue_name": "Park Square Live Music & Coffee",
        "artist_id": 6,
        "artist_name": "The Wild Sax Band",
        "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
        "start_time": "2035-04-08T20:00:00.000Z"
    }, {
        "venue_id": 3,
        "venue_name": "Park Square Live Music & Coffee",
        "artist_id": 6,
        "artist_name": "The Wild Sax Band",
        "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
        "start_time": "2035-04-15T20:00:00.000Z"
    }]
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    flash('Show was successfully listed!')
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

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
