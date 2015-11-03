import requests
from redis import Redis
from rq_scheduler import Scheduler

from twilio.rest import TwilioRestClient
from datetime import datetime
import pytz

# Open a connection to your Redis server.
redis_server = Redis()

# Create a scheduler object with your Redis server.
scheduler = Scheduler(connection=redis_server)

client = TwilioRestClient()


def get_next_pass(lat, lon):
    iss_url = 'http://api.open-notify.org/iss-pass.json'
    location = {'lat': lat, 'lon': lon}
    response = requests.get(iss_url, params=location).json()

    next_pass = response['response'][0]['risetime']
    next_pass_datetime = datetime.fromtimestamp(next_pass, tz=pytz.utc)

    print('Next pass for {}, {} is: {}'.format(next_pass_datetime, lat, lon))
    return next_pass_datetime


def add_to_queue(phone_number, lat, lon):
    # Add this phone number to Redis associated with "lat,lon"
    redis_server.set(phone_number, '{},{}'.format(lat, lon))

    # Get the datetime object representing the next ISS flyby for this number.
    next_pass_datetime = get_next_pass(lat, lon)

    # Schedule a text to be sent at the time of the next flyby.
    scheduler.enqueue_at(next_pass_datetime, notify_subscriber, phone_number)

    print('{} will be notified when ISS passes by {}, {}'
          .format(phone_number, lat, lon))


def notify_subscriber(phone_number):
    msg_body = 'Look up! You may not be able to see it, but the International' \
               ' Space Station is passing above you right now!'

    # Retrieve the latitude and longitude associated with this number.
    lat, lon = redis_server.get(phone_number).split(',')

    # Send a message to the number alerting them of an ISS flyby.
    client.messages.create(to=phone_number,
                           messaging_service_sid='MGf15479a3fb4fb150594723d52391c4f6',
                           body=msg_body)

    # Add the subscriber back to the queue to receive their next flyby message.
    add_to_queue(phone_number, lat, lon)

    print('Message has been sent to {}'.format(phone_number))
