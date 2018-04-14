from __future__ import unicode_literals

import argparse
import sys
import os
import re
import urllib
import urllib2
import spotipy
import youtube_dl
import eyed3
import spotipy.util as util

from spotipy.oauth2 import SpotifyClientCredentials
from bs4 import BeautifulSoup



# Spotify credentials
SPOTIFY_USER = ''
SPOTIFY_SCOPE = 'user-library-read'
SPOTIPY_CLIENT_ID =''
SPOTIPY_CLIENT_SECRET =''
SPOTIPY_REDIRECT_URI = 'http://localhost/'

os.environ['SPOTIPY_CLIENT_ID']= SPOTIPY_CLIENT_ID
os.environ['SPOTIPY_CLIENT_SECRET']= SPOTIPY_CLIENT_SECRET
os.environ['SPOTIPY_REDIRECT_URI']= SPOTIPY_REDIRECT_URI

def main():
	"""
	Main function.
	Converts arguments to Python and processes accordingly.
	"""

	parser = argparse.ArgumentParser(description='Download music from YouTube and auto-fill meta data.\n')
	parser.add_argument('search', metavar='U', type=str, nargs='*',
						help='YouTube video url or search term(song name and artist)')
	parser.add_argument('-sc', '--soundcloud', action='store_true',
						help='SoundCloud song url')
	parser.add_argument('-sp', '--spotify', action='store_true',
						help='Download spotify playlist')
	parser.add_argument('-l', '--list', action='store_true',
						help='Prompt user for more songs before downloading')
	args = parser.parse_args()
	vargs = vars(args)

	if vargs['search']:
		download_track(' '.join(vargs['search']))

	if vargs['list']:
		print "1) Type <song_name artist>"
		print "2) Press enter after each entry"
		print "3) Press enter on empty entry to begin downloading"
		print "4) Enter 'list' to display all entries"
		search_terms = []
		while True:
			entry = raw_input()
			if not entry:
				break
			search_terms.append(entry)
		for i, item in enumerate(search_terms):
			print "Downloading", i+1, "of" len(search_terms), item
			download_track(item)

def get_spotify_client():
	token = util.prompt_for_user_token(SPOTIFY_USER, SPOTIFY_SCOPE)
	return spotipy.Spotify(auth=token)

def download_track(query):
	queries = yt_spellcheck(query) # returns {corrected, original}
	meta = spotify_meta(queries)
	video_url = get_yt_url(queries, meta)
	
	if 'track_name' in meta:
		file_name = meta['track_name'].encode('utf-8') + ' - ' + meta['artist'].encode('utf-8')
	elif 'corrected' in queries:
		file_name = queries['corrected'].encode('utf-8')
	else:
		file_name = queries['original'].encode('utf-8')

	file_name = re.sub('[\\\\/:*?"<>|]', '', file_name).rstrip()
	command_tokens = [
	    'youtube-dl',
	    '--no-warnings',
	    '--extract-audio',
	    '--format bestaudio',
	    '--audio-format mp3',
	    '--audio-quality 0',
	    '--output', '"' + file_name + '.%(ext)s' + '"',
	    video_url]

	command_tokens.insert(1, '-q')
	command = ' '.join(command_tokens)
	os.system(command)
	edit_tags(file_name, meta)

def yt_spellcheck(query):
	# piggyback youtube's spellchecker & query corrector
	url = "https://www.youtube.com/results?search_query=" + urllib.quote(query) + "&sp=EgIgAQ%253D%253D"
	soup = BeautifulSoup(urllib2.urlopen(url).read(), "html.parser")
	queries = {'original':query}
	try:
		queries['corrected'] = soup.find('span', attrs={"class":"spell-correction-corrected"}).find_next('a').getText()
	except Exception as e: # Exception expected when no spell correction is found
		print
	return queries

def spotify_meta(queries):
	# retrieve meta data from spotify
	print "Getting spotify data"
	client = get_spotify_client()
	meta = {}	
	try:
		spotify_search = client.search(q=queries['original'], limit=1)
		# print json.dumps(convert(spotify_search), indent = 2)
		track_name = spotify_search['tracks']['items'][0]['name']
	except Exception as e:
		if 'corrected' in queries:
			try:
				spotify_search = client.search(q=queries['corrected'], limit=1)
				track_name = spotify_search['tracks']['items'][0]['name']
			except:
				print "Unable to find", queries['original'], "or", queries['corrected'], "on Spotify"

	meta['track_name'] = track_name
	meta['cover_art'] = spotify_search['tracks']['items'][0]['album']['images'][0]['url']
	meta['artist'] = spotify_search['tracks']['items'][0]['album']['artists'][0]['name']
	meta['album'] = spotify_search['tracks']['items'][0]['album']['name']

	return meta

def get_yt_url(queries, meta):

	track_name = search = queries['original']
	if 'track_name' in meta:
		search = meta['track_name'] + " " + meta['artist']
		track_name = meta['track_name']
	elif queries['corrected']:
		search = queries['corrected']

	count = 0
	# Try to find YouTube's Topic Channel for the track
	search_list = get_search_list(search + " topic") 
	for item in search_list:
		count += 1
		if "Topic" in item[3] and track_name.lower() in item[2].lower() and "live" not in item[2].lower():
			if count < 2:
				return item[0]
	# No Topic channel was found, try other search
	search_list = get_search_list(track_name + " " + artist) 
	for item in search_list:
		if "live" not in item[2].lower() and "karaoke" not in item[2].lower():
			return item[0]
	return ""

#URLs from YouTube search
def get_search_list(query):
	query = urllib.quote(query)
	url = "https://www.youtube.com/results?search_query=" + query + "&sp=EgIgAQ%253D%253D"
	response = urllib2.urlopen(url)
	html = response.read()
	soup = BeautifulSoup(html, "html.parser")
	vid_list = []
	duration_list = []
	title_list = []
	channel_list = []
	for vid in soup.findAll(attrs={'class':'yt-uix-tile-link'}):
		vid_list.append('https://www.youtube.com'.encode('UTF8') + vid['href'].encode('UTF8'))
	# print "Found".encode('UTF8'), len(vid_list), "urls".encode('UTF8')
	for time in soup.findAll(attrs={'class':'video-time'}):
		duration_list.append(get_sec(time.text.encode('UTF8')))
	for title in soup.findAll(attrs={'aria-describedby':re.compile('description-id')}):
		title_list.append(title.text.encode('UTF8'))
	for channel in soup.findAll(attrs={'class':'yt-lockup-byline '}):
		channel_list.append(channel.text)
	# print "Comparing".encode('UTF8'), len(duration_list), "durations".encode('UTF8')
	search_list = zip(vid_list, duration_list, title_list, channel_list)
	return search_list



def edit_tags(file_name, meta):
	try:
		audio_file = eyed3.load(file_name + ".mp3")
	except Exception as e:
		print(e)
		try:
			audio_file = eyed3.load(file_name + ".m4a")
		except Exception as e:
			print(e)
			print "Tagging error"
	try:
		audio_file.tag.title = unicode(meta['track_name'])
		audio_file.tag.artist = unicode(meta['artist'])
		audio_file.tag.album = unicode(meta['album'])
	except Exception as e:
		print(e)
		print "Tagging error"

	# album art
	try:
		response = urllib2.urlopen(meta['cover_art'])  
		image_data = response.read()
		audio_file.tag.images.set(3, image_data , "image/jpeg" ,u"Discription")
		audio_file.tag.save(version=(1,None,None))
		audio_file.tag.save()
		audio_file.tag.save(version=(2,3,0))
	except:
		print "Error fetching album art"
		pass

def get_sec(time_str):
	if len(time_str) < 6:
		m, s = time_str.split(':')
		return int(m) * 60 + int(s)
	else:
		h, m, s = time_str.split(':')
		return int(h) * 3600 + int(m) * 60 + int(s)






####################################################################
# Main
####################################################################

if __name__ == '__main__':
	# try:
	sys.exit(main())
	# except Exception as e:
	# 	exc_type, exc_obj, exc_tb = sys.exc_info()
	# 	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	# 	print(exc_type, fname, exc_tb.tb_lineno)