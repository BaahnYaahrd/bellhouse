#!/usr/bin/python3

import os
import sys
import signal
import multiprocessing

import simpleaudio
import RPi.GPIO as GPIO


class ThreadedPlayer:
	def __init__(self, audio_root, audio_func=None):
		self.thread = None
		self.audio_func = audio_func if audio_func is not None else self.play_wav_simpleaudio
		self.songs = dict()
		self.audio_root = os.path.abspath(audio_root)
		self.last_playlist_id = None
	
	def register_wav(self, audio_id, paths_wav):
		"""
		Registers audio files with an arbitrary ID key for later playback via play_threaded().
		Call play_threaded() with the ID value used to register the song.
		paths_wav can be a filename, or a list of filenames. Files are assumed to be in the audio_root folder.
		The ID key can be anything, for example the GPIO pin ID which GPIO passes as a first argument to all its callbacks.
		If multiple songs are registered for the same key, they form a playlist which will be cycled through by multiple calls to play_threaded() with the same key. 
		"""
		playlist = [paths_wav] if isinstance(paths_wav, str) else paths_wav
		self.songs[audio_id] = [playlist, 0]
		print(audio_id, self.songs[audio_id])
	
	def play_threaded(self, audio_id):
		"""
		Plays an audio file, specified by the ID value which was previously used to register it via register_wav().
		If an audio file is already playing, it will be terminated and the new one will be started.
		If the ID value refers to a multi-song playlist, pressing the same button again will cycle through the playlist.
		"""
		if self.thread is not None:
			self.thread.terminate()

		playlist, counter = self.songs[audio_id]
		if self.last_playlist_id != audio_id:
			counter = 0
		song_to_play = playlist[counter]
		song_to_play = os.path.join(self.audio_root, song_to_play)
		self.thread = multiprocessing.Process(target=self.audio_func, args=(song_to_play,))
		self.thread.start()
		self.last_playlist_id = audio_id
		counter += 1
		self.songs[audio_id][1] = counter % len(playlist)

	@staticmethod
	def play_wav_simpleaudio(path_wav):
		wav_obj = simpleaudio.WaveObject.from_wave_file(path_wav)
		play_obj = wav_obj.play()
		play_obj.wait_done()


def keyboard_interrupt_handler(sig, frame):
	"""
	This is called when Ctrl+C is pressed, to handle termination gracefully by
	releasing all assigned GPIO pins.
	"""
	GPIO.cleanup()
	sys.exit(0)


if __name__ == '__main__':
	path_audio = r'/home/pi/gpiobell/wav'
	
	pin_map = {
		22: 'Conni geht zelten.wav', #TODO: Choose and wire a different pin number here - pin 4 seems to not be the correct type Changed to pin22 on 31.01.22
		#10: 'doorbell-6.wav',
		23: ['doorbell-6.wav', 'boilingwater.wav',],
		17: 'boilingwater.wav',
		27: 'Wellerman.wav',
	}
	
	print('Configuring GPIO mode...')
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)

	print('Initializing player...')
	player = ThreadedPlayer(path_audio)
	print('Registering GPIO pins and callbacks...')
	for pin_nr, audio_source in pin_map.items():
		GPIO.setup(pin_nr, GPIO.IN)
		GPIO.add_event_detect(pin_nr, GPIO.RISING, callback=player.play_threaded, bouncetime=200)
		player.register_wav(pin_nr, audio_source)
	
	print('gpiobell running. Use Ctrl+C to terminate.')
	signal.signal(signal.SIGINT, keyboard_interrupt_handler)
	signal.pause()
	print('Exiting.')

