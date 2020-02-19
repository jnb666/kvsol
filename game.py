from functools import partial
from kivy.core.window import Window
from kivy.config import Config
from kivy.logger import Logger

from cards import Card, Deck

# game base class - specific games inherit from this
class BaseGame(object):
    help = ""
    decks = 1
    num_tableau = 0
    num_waste = 0
    num_cols = 8
    num_rows = 5
    x_padding, y_padding = 0.02, 0.02
    fan_pile_scale = 0.18

    def __init__(self, root=None, on_move=None, menu_size=0):
        self.menu_size = menu_size
        self.set_scale(Window.width, Window.height, menu=menu_size)
        self.layout = root.layout
        self.move = on_move
        self.piles = dict(tableau=[], foundation=[], waste=[])
        self.num_foundation = 4*self.decks
        self.max_score = 52*self.decks
        self.num_piles = self.num_tableau + self.num_foundation + self.num_waste
        self.won = False

    # clear the board 
    def clear(self, base):
        Logger.debug("Cards: clear game (base=%d)" % base)
        for _, group in list(self.piles.items()):
            for pile in group: pile.clear(base)
        self.won = False

    # called on window resize
    def do_resize(self):
        width, height = Window.width, Window.height
        self.set_scale(width, height, menu=self.menu_size)
        for pile in self.all_piles():
            self.position_pile(pile)
            pile.redraw()
        Config.set('graphics', 'width', width)
        Config.set('graphics', 'height', height)
        Config.write()

    # split window into rows and cols
    def set_scale(self, width, height, menu=0):
        Logger.info("Cards: window size = %d x %d" % (width, height))
        self.padding = int(self.x_padding*width), int(self.y_padding*height)
        h = (height-menu)/self.num_rows - self.padding[1]
        csize = self._set_cell_size(int(h/Card.aspect_ratio), int(h))
        if self.num_cols*csize[0] <= width:
            self.x0 = int((width-csize[0]*self.num_cols)/2) + self.padding[0]/2
            self.y0 = height + self.padding[1]/2
            Logger.debug("Cards: set scale from window height: origin = %d %d" % (self.x0,self.y0))
        else:
            w = width/self.num_cols - self.padding[0]
            csize = self._set_cell_size(w, int(w*Card.aspect_ratio))
            self.x0 = self.padding[0]/2
            self.y0 = height + self.padding[1]/2
            Logger.debug("Cards: set scale from window width: origin = %d %d" % (self.x0,self.y0))
        Logger.info("Cards: card size = %d x %d" % self.card_size)
        self.fan_pile = int(self.fan_pile_scale*self.card_size[1])
        Logger.info("Cards: fan pile =  %d" % self.fan_pile)

    def _set_cell_size(self, w, h):
        self.card_size = (w, h)
        return w+self.padding[0], h+self.padding[1]

    # convert from column and row to screen coords
    def position_pile(self, pile): 
        pile.x = self.x0 + pile.col*(self.card_size[0]+self.padding[0])
        pile.y = self.y0 - (pile.row+1)*(self.card_size[1]+self.padding[1])
        Logger.debug("Cards: position pile %s @ %dx%d" % (pile, pile.x, pile.y))
        pile.xstep = self.fan_pile if pile.fan == 'right' else 0
        pile.ystep = self.fan_pile if pile.fan == 'down' else 0
        pile.csize = self.card_size

    # accessors
    def tableau(self): return self.piles['tableau']

    def foundation(self): return self.piles['foundation']

    def waste(self): return self.piles['waste']

    def all_piles(self): return self.piles['tableau']+self.piles['foundation']+self.piles['waste']

    # abstract methods
    def can_add(self, src, pile, group, num):
        raise NotImplementedError("can_add must be implemented")

    def can_join(self, pile, card):
        return True

    def on_moved(self, move):
        pass

    # add a new pile 
    def add_pile(self, pile):
        pile.index = len(self.piles[pile.type])
        pile.on_release = lambda auto=False: self.on_release(pile, auto)
        self.piles[pile.type].append(pile)

    # can we move num cards from orig to dest?
    def try_move(self, orig, dest, num, callback=False, collide=False):
        if dest is orig: return False
        Logger.debug("Cards: try_move %d from %r to %r" % (num, orig.pid(), dest.pid()))
        group = orig.top()
        if collide:
            if dest.ystep > 0 and dest.size() > 0:
                target = dest.top()
            else:
                target = dest.base()
            if not group.collide_widget(target):
                return False
        if self.can_add(orig, dest, group, num):
            # split flag is set if a new card was *not* uncovered
            is_split = group.cards() > num
            if not is_split and orig.size() > 1:
                if orig.next().top_card().faceup:
                    is_split = True
            self.move(orig, dest, num, split=is_split, callback=callback)
            return True
        return False

    # callback on card drag released - returns cards moved or None if no move
    def on_release(self, pile, auto=False):
        Logger.debug("Cards: on_release %s %d auto=%s" % (pile.type, pile.index, auto))
        top = pile.top()
        if top.cards() == 0 or top.top_card() is None: return False
        #Logger.debug("Cards: %d cards released top=%s bot=%s" % 
        #             (top.cards(), top.top_card(), top.bottom_card()))
        # build on foundation or tableau?
        if auto:
            for dest in self.foundation():
                if self.try_move(pile, dest, top.cards(), collide=False):
                    return top
        else:
            for dest in self.foundation() + self.tableau() + self.waste():
                if self.try_move(pile, dest, top.cards(), collide=True):
                    return top
        Logger.debug("Cards: move back")
        pile.move_cards_back()
        return None
   
    # check for any cards which can be moved to foundations
    def auto_drop(self):
        for orig in self.tableau() + self.waste():
            if orig.size() > 0 and orig.top().top_card().faceup:
                for dest in self.foundation():
                    if self.try_move(orig, dest, 1, callback=self.auto_drop):
                        return True
        return False

    # execute a move, returns affected piles and change in score
    def do_move(self, move, reverse=False):
        src, dst, num = move['src'], move['dst'], move['n']
        if reverse:
            move['src'], move['dst'] = dst, src
            # re-cover card in tableau which was uncovered?
            if src[0] == 'tableau' and not move.get('split',False): move['cover'] = True
        else:
            # expose card below when move from tableau
            if src[0] == 'tableau': move['expose'] = True
        # update score if moved to (or from) foundation
        score = 0
        if move['dst'][0] == 'foundation': score = num
        if move['src'][0] == 'foundation': score = -num
        # move from src to dst
        Logger.debug("Cards: do_move %r" % move)
        src, dst = move['src'], move['dst']
        orig = self.piles[src[0]][src[1]]
        dest = self.piles[dst[0]][dst[1]]
        orig.move_num_cards_to(dest, num, 'expose' in move, 'cover' in move, 'flip' in move)
        # any items we exposed should now be movable
        if orig.size() > 0 and orig.top().top_card() and orig.top().top_card().faceup:
            orig.top().lock(False)
        return orig, dest, score

    # deal top card from src to each of dest list of piles
    def deal_cards(self, src, dest, append=False):
        if src.size() > 0 and len(dest) > 0:
            cb = partial(self.deal_cards, src, dest[1:], True)
            self.move(src, dest[0], 1, flip=True, append=append, callback=cb)


