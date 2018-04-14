AutoMagicMusic
==============

AutoMagicMusic lets you download music from YouTube and automatically fills in ID3 tags with meta data from Spotify

Usage
---------
You'll need Spotify API keys and user name. youtube-dl, spotipy, and eyed3 are among some of the dependencies needed. [ffmpeg]([https://github.com/adaptlearning/adapt_authoring/wiki/Installing-FFmpeg) is required for converting audio files.

To download a YouTube url:
```bash
python automagicmusic.py https://www.youtube.com/watch?v=KTlp91iSj5g
```

To search and download a song:
```bash
python automagicmusic.py Everybody wants to rule the world tears for fears
```

To input a list of songs before downloading
```bash
python automagicmusc.py -l
```