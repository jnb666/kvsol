## simpie solitaire card game
import ast
from functools import partial

import kivy
kivy.require('1.11.0')
from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.properties import NumericProperty, ObjectProperty
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.metrics import Metrics
from kivy.utils import platform

from cards import Deck
from game import BaseGame
import games

GAMES = {}

# load all game classes
def get_subclasses(base):
    cls = base.__subclasses__()
    for d in list(cls):
        cls.extend(get_subclasses(d))
    return cls  

def register_games():
    global GAMES
    for plugin in get_subclasses(BaseGame):
        Logger.info("Cards: load game %s" % plugin.name)
        GAMES[plugin.name] = plugin

# main app
class Solitaire(App):
    score = NumericProperty(0)
    moves = NumericProperty(0)
    max_moves = NumericProperty(0)
    game = ObjectProperty(None)
    font_size = NumericProperty(12)
    menu_height = NumericProperty(0.06*Window.height)
    pad_by = NumericProperty(0.007*Window.height)

    # initialise config file
    def build_config(self, config):
        #self.games = games.register()
        names = sorted(GAMES.keys())
        config.setdefaults('game', {'name': names[0], 'score': 0, 'won':False})
        config.setdefaults('moves', {'count': 0, 'max': 0})
        config.setdefaults('piles', {})
        config.setdefaults('settings', {'fps': 10, 'font_size': 16, 'help_font_size': 14, 
            'popup_width': 0.4, 'popup_height': 0.6})

    # settings panel
    def build_settings(self, settings):
        settings.add_json_panel('Solitaire', self.config, data='''[
            { "type": "numeric", "title": "FPS",
              "desc": "animation frames per second",
              "section": "settings", "key": "fps" },
            { "type": "numeric", "title": "Font size",
              "desc": "size of font for main screen",
              "section": "settings", "key": "font_size" },
            { "type": "numeric", "title": "Help font size",
              "desc": "size of font for help text",
              "section": "settings", "key": "help_font_size" },
            { "type": "numeric", "title": "Popup width",
              "desc": "width of popup as fraction of screen",
              "section": "settings", "key": "popup_width" },
            { "type": "numeric", "title": "Popup height",
              "desc": "height of popup as fraction of screen",
              "section": "settings", "key": "popup_height" }
        ]''')

    # user updated config 
    def on_config_change(self, config, section, key, value):
        if config is self.config and section == 'settings' and key == 'font_size':
            self.font_size = int(value)

    # initialise new game
    def set_game(self, name):
        self.game = GAMES[name](root=self.root, on_move=self.on_move, menu_size=self.menu_height)
        self.game.build()
        conf = self.config
        if not conf.has_section(name):
            conf.add_section(name)
            conf.set(name, 'played', 1)
            conf.set(name, 'won', 0)
            conf.set(name, 'best_moves', 0)
            conf.set(name, 'avg_moves', 0)
        conf.write()
 
    # shuffle the deck
    def shuffle(self):
        self.deck = Deck(self.game.decks)
        self.deck.rewind(shuffle=True)
        self.deck.save(self.config)
        self.config.set('game', 'won', False)
        if self.moves > 0:
            self.config.set(self.game.name, 'played', self.getval('played')+1)
        self.set_moves(0, True)
         
    # initialise the board
    def build(self):
        self.icon = 'icon.png'
        conf = self.config
        name = conf.get('game', 'name')
        self.font_size = conf.getint('settings', 'font_size')
        Logger.info("Cards: build game %s font size %d" % (name, self.font_size))
        chooser = self.root.chooser
        chooser.values = sorted(GAMES.keys())
        if not name in list(GAMES.keys()):
            name = sorted(GAMES.keys())[0]
        chooser.text = name
        chooser.bind(text=self.choose)
        self.set_game(name)
        self._starting = False
        if conf.has_option('game', 'deck'):
            # restore where we left off
            self.deck = Deck(self.game.decks, config=conf)
            self.moves = conf.getint('moves', 'count')
            self.max_moves = conf.getint('moves', 'max')
            self.score = conf.getint('game', 'score')
            for pile in self.game.all_piles():
                pile.load(conf)
        else:
            # first time initialisation
            self.shuffle()
            for pile in self.game.all_piles():
                self.game.start(pile, self.deck)
                pile.save(conf)
            conf.write()
        if platform == 'android':
            Window.bind(on_keyboard=self.hook_keyboard)
        Window.on_resize = self.resize
        delay = self.framerate();
        Logger.info("Cards: resize delay = %g", delay)
        self.resize_event = Clock.create_trigger(lambda dt: self.game.do_resize(), delay)

    # bind android back key
    def hook_keyboard(self, window, key, *args):
         if key == 27:
            self.undo()
            return True

    # called on window resize
    def resize(self, width, height):
        if self.resize_event.is_triggered:
            self.resize_event.cancel()
        self.resize_event()

    # draws the cards on new game - animate this
    # have some hacky logic here so this is not called while it is running
    def start(self, index, *args):
        if index == 0:
            self._starting = True
        pile = (self.game.tableau()+self.game.waste())[index]
        self.game.start(pile, self.deck)
        if index+1 < self.game.num_tableau + self.game.num_waste:
            Clock.schedule_once(partial(self.start, index+1), self.framerate())
        else:
            for pile in self.game.all_piles():
                pile.save(self.config)
            self.config.write()
            self._starting = False
 
    # callback from game chooser
    def choose(self, chooser, choice):
        if self._starting: return
        Logger.debug("Cards: choose game %s" % choice)
        self.config.set('game', 'name', choice)
        self.config.write()
        self.game.clear(0)
        self.set_game(choice)
        self.shuffle()
        self.start(0)

    # app button callbacks
    def new_game(self):
        if self._starting: return
        Logger.debug("Cards: new_game")
        self.game.clear(1)
        self.shuffle()
        self.start(0)
 
    def restart(self):
        if self._starting: return
        Logger.debug("Cards: restart")
        self.game.clear(1)
        self.deck.rewind()
        self.set_moves(0, True)
        self.start(0)

    def undo(self):
        Logger.debug("Cards: undo %d" % self.moves)
        if self.moves > 0:
            self.set_moves(self.moves-1)
            self.perform_move(self.moves, reverse=True)

    def redo(self):
        Logger.debug("Cards: redo %d of %d" % (self.moves, self.max_moves))
        if self.moves < self.max_moves:
            self.perform_move(self.moves)
            self.set_moves(self.moves+1)

    def auto(self):
        Logger.debug("Cards: auto drop")
        self.game.auto_drop()

    def stats(self, title=''):
        if not title:
            title = '%s statistics' % self.game.name
        data = [
            'moves', str(self.moves),
            'score', str(self.score),
            'played', self.getval('played', 'str'),
            'won', self.getval('won', 'str'), 
            'best moves', self.getval('best_moves', 'str'),
            'average moves', self.getval('avg_moves', 'str')       
        ]
        popup = self.new_popup(title, (0.4,0.1), data, self.font_size)
        popup.open()
        pass

    def help(self):
        font_size = self.config.getint('settings','help_font_size')
        popup = self.new_popup(self.game.name, (0.8,), [self.game.help], font_size)
        popup.open()
        pass

    def new_popup(self, title, col_width, data, font_size):
        width = self.config.getfloat('settings','popup_width')*Window.width
        height = self.config.getfloat('settings','popup_height')*Window.height
        popup = AppPopup(title=title, size=(width,height))
        columns = len(col_width)
        popup.body.cols = columns
        fsize = str(font_size) + "sp"
        for i, el in enumerate(data):
            w = width*col_width[i % columns]
            popup.body.add_widget(Label(text=el, text_size=(w,None), font_size=fsize))
        return popup

    # update stats and show popup on completed game
    def check_score(self):
        conf = self.config
        if self.score == self.game.max_score and not conf.getboolean('game','won'):
            conf.set('game', 'won', True)
            name = self.game.name
            won = self.getval('won')
            best = self.getval('best_moves')
            avg = self.getval('avg_moves', 'float')
            conf.set(name, 'won', won+1)
            if best == 0 or self.moves < best:
                conf.set(name, 'best_moves', self.moves)
            conf.set(name, 'avg_moves', (avg*won+self.moves)/(won+1))
            conf.write()
            self.stats(title='congratulations - you won!')
            return True

    # get value from config file
    def getval(self, key, typ='int'):
        if typ == 'int':
            val = self.config.getint(self.game.name, key)
        elif typ == 'float':
            val = self.config.getfloat(self.game.name, key)
        else:
            val = self.config.get(self.game.name, key)
        return val

    # logs the history and, if callback is set then defer drawing to animate
    def on_move(self, orig, dest, num, **args):
        Logger.debug("Cards: on_move %d" % self.moves)
        do_callback = False
        if 'callback' in args:
            do_callback = args['callback'] is not False
            callback = args['callback']
            del args['callback']
        args['src'] = orig.pid()
        args['dst'] = dest.pid()
        args['n'] = num
        conf = self.config
        if args.get('append', False):
            text = conf.get('moves', str(self.moves-1))
            text = text[:-1] + ',' + repr(args) + ']'
            conf.set('moves', str(self.moves-1), text)
            conf.write()
        else:
            conf.set('moves', str(self.moves), '[' + repr(args) + ']')
            self.set_moves(self.moves+1)
        # do it
        if do_callback:
            Clock.schedule_once(partial(self.draw, args, callback), self.framerate())
        else:
            self.do_move(args)

    # draw move from timer event
    def draw(self, move, callback, *args):
        self.do_move(move)
        if callback: callback()

    # read move from config and execute it
    def perform_move(self, count, reverse=False):
        text = self.config.get('moves', str(count))
        Logger.debug("Cards: perform_move %d" % count)
        moves = ast.literal_eval(text)
        if reverse:
            moves.reverse()
        self.move_cb(moves, reverse)

    # step through moves in list
    def move_cb(self, moves, reverse, *args):
        if len(moves) == 0: return
        self.do_move(moves[0], reverse, True)
        Clock.schedule_once(partial(self.move_cb, moves[1:], reverse), self.framerate())

    # execute move and update state
    def do_move(self, move, reverse=False, replay=False):
        orig, dest, score = self.game.do_move(move, reverse)
        Logger.debug("Cards: do_move %s to %s score %d += %d" % (orig, dest, self.score, score))
        if score:
            self.score += score
            self.config.set('game', 'score', self.score)
            self.check_score()
        orig.save(self.config)
        dest.save(self.config)
        self.config.write()
        # user callback
        if not replay:
            self.game.on_moved(move)
  
    # save no. of moves and reset score on new game
    def set_moves(self, val, reset=False):
        self.moves = val
        self.max_moves = val if reset else max(self.max_moves, val)
        conf = self.config
        conf.set('moves', 'count', self.moves)
        conf.set('moves', 'max', self.max_moves)
        if self.moves == 0 and reset:
            self.score = 0
            conf.set('game', 'score', 0)
        conf.write()

    # callbacks to allow android save and resume
    def on_pause(self):
        return True

    def on_resume(self):
        pass

    def framerate(self):
        return 1.0 / self.config.getfloat('settings','fps')

# defined in kv file
class AppPopup(Popup):
    pass

if __name__ == '__main__':
    register_games()
    Solitaire().run()



