import logging
import traceback
import mopidy
import mopidy.core
import pygame
from pkg_resources import Requirement, resource_filename

from .search_screen import SearchScreen
from .library_screen import LibraryScreen
from .main_screen import MainScreen
from .menu_screen import MenuScreen
from .playlist_screen import PlaylistScreen
from .screen_objects import Progressbar, ScreenObjectsManager, \
    TouchAndTextItem
from .input_manager import InputManager
from .tracklist import Tracklist


logger = logging.getLogger(__name__)

search_index = 0
main_screen_index = 1
tracklist_index = 2
library_index = 3
playlist_index = 4
menu_index = 5


class ScreenManager():
    def __init__(self, size, core, cache):
        self.size = size
        self.core = core
        self.fonts = {}
        self.current_screen = 0
        self.base_size = self.size[1] / 8
        font = resource_filename(
            Requirement.parse("mopidy-touchscreen"),
            "mopidy_touchscreen/icomoon.ttf")
        self.fonts['base'] = pygame.font.SysFont("verdana",
                                                 self.base_size)
        self.fonts['icon'] = pygame.font.Font(font, self.base_size)
        try:
            self.screens = [
                SearchScreen(size, self.base_size, self),
                MainScreen(size, self, cache, core, self.fonts),
                Tracklist(size, self.base_size, self),
                LibraryScreen(size, self.base_size, self),
                PlaylistScreen(size, self.base_size, self),
                MenuScreen(size, self.base_size, self)]
        except:
            traceback.print_exc()
        self.track = None
        self.input_manager = InputManager(size)
        self.top_bar_objects = ScreenObjectsManager()
        self.down_bar_objects = ScreenObjectsManager()
        self.selected_zone = self.top_bar_objects
        self.dirty_area = []
        self.screen_changed = True

        # Menu buttons

        button_size = (self.size[0] / 6, self.base_size)

         # Search button
        button = TouchAndTextItem(self.fonts['icon'], u" \ue986",
                                  (0, self.base_size * 7),
                                  button_size)
        self.down_bar_objects.set_touch_object("menu_0", button)
        x = button.get_right_pos()

        # Main button
        button = TouchAndTextItem(self.fonts['icon'], u" \ue600",
                                  (x, self.base_size * 7),
                                  button_size)
        self.down_bar_objects.set_touch_object("menu_1", button)
        x = button.get_right_pos()

        # Tracklist button
        button = TouchAndTextItem(self.fonts['icon'], u" \ue60d",
                                  (x, self.base_size * 7),
                                  button_size)
        self.down_bar_objects.set_touch_object("menu_2", button)
        x = button.get_right_pos()

        # Library button
        button = TouchAndTextItem(self.fonts['icon'], u" \ue604",
                                  (x, self.base_size * 7),
                                  button_size)
        self.down_bar_objects.set_touch_object("menu_3", button)
        x = button.get_right_pos()

        # Playlist button
        button = TouchAndTextItem(self.fonts['icon'], u" \ue605",
                                  (x, self.base_size * 7),
                                  button_size)
        self.down_bar_objects.set_touch_object("menu_4", button)
        x = button.get_right_pos()

        # Menu button
        button = TouchAndTextItem(self.fonts['icon'], u" \ue60a",
                                  (x, self.base_size * 7), None)
        self.down_bar_objects.set_touch_object("menu_5", button)

        # Down bar
        self.down_bar = pygame.Surface(
            (self.size[0], self.size[1] - self.base_size * 7),
            pygame.SRCALPHA)
        self.down_bar.fill((0, 0, 0, 128))

        self.options_changed()
        self.mute_changed(self.core.playback.mute.get())
        self.playback_state_changed(self.core.playback.state.get(),
                                    self.core.playback.state.get())
        self.screens[menu_index].check_connection()
        self.change_screen(library_index)


    def update(self):
        surface = pygame.Surface(self.size)
        surface.fill([200, 200, 200])
        self.screens[self.current_screen].update(surface,
                                                 self.screen_changed)
        surface.blit(self.down_bar, (0, self.base_size * 7))
        self.top_bar_objects.render(surface)
        self.down_bar_objects.render(surface)
        self.screen_changed = False
        return surface

    def track_started(self, track):
        self.track = track
        self.screens[main_screen_index].track_started(track.track)
        self.screens[tracklist_index].track_started(track)

    def track_playback_ended(self, tl_track, time_position):
        self.screens[main_screen_index].track_playback_ended(tl_track, time_position)

    def event(self, event):
        event = self.input_manager.event(event)
        if event is not None:
            if event.type == InputManager.click:
                objects = self.top_bar_objects.get_touch_objects_in_pos(
                    event.current_pos)
                objects.extend(
                    self.down_bar_objects.get_touch_objects_in_pos(
                        event.current_pos))
                self.click_on_objects(objects, event)
            elif event.type == InputManager.key and event.direction == InputManager.enter:
                objects = [self.selected_zone.selected_key]
                self.click_on_objects(objects, event)
            elif event.type == InputManager.key:
                if event.direction == InputManager.enter:
                    logger.error(self.selected_zone.selected_key)
                    self.click_on_objects(
                        [self.selected_zone.selected_key], event)
                else:
                    self.change_selection(event, None)
            self.screens[self.current_screen].touch_event(event)

    def volume_changed(self, volume):
        self.screens[main_screen_index].volume_changed(volume)



    def playback_state_changed(self, old_state, new_state):
        self.screens[main_screen_index].playback_state_changed(old_state, new_state)

    def mute_changed(self, mute):
        self.screens[main_screen_index].mute_changed(mute)

    def tracklist_changed(self):
        self.screens[tracklist_index].tracklist_changed()

    def options_changed(self):
        self.screens[main_screen_index].options_changed()

    def change_screen(self, new_screen):
        self.screen_changed = True
        self.down_bar_objects.get_touch_object(
            "menu_" + str(self.current_screen)).set_active(False)
        self.current_screen = new_screen
        self.down_bar_objects.get_touch_object(
            "menu_" + str(new_screen)).set_active(True)
        self.dirty_area.append(
            pygame.Rect(0, 0, self.size[0], self.size[1]))

    def click_on_objects(self, objects, event):
        if objects is not None:
            for key in objects:
                if key[:-1] == "menu_":
                    self.change_screen(int(key[-1:]))

    def playlists_loaded(self):
        self.screens[playlist_index].playlists_loaded()

    def set_connection(self, connection, loading):
        self.screens[main_screen_index].set_connection(connection, loading)

    def check_connection(self):
        self.screens[menu_index].check_connection()

    def search(self, query, mode):
        self.screens[search_index].search(query, mode)

    def change_selection(self, event, pos):
        if self.selected_zone == self.top_bar_objects:
            if not self.top_bar_objects.change_selected(
                    event.direction,
                    pos) and event.direction == InputManager.down:
                pos = self.top_bar_objects.selected.pos
                self.selected_zone = self.down_bar_objects
                self.top_bar_objects.set_selected(None)
                self.change_selection(event, pos)
        elif self.selected_zone == self.down_bar_objects:
            if not self.down_bar_objects.change_selected(
                    event.direction,
                    pos) and event.direction == InputManager.up:
                pos = self.down_bar_objects.selected.pos
                self.selected_zone = self.top_bar_objects
                self.down_bar_objects.set_selected(None)
                self.change_selection(event, pos)
