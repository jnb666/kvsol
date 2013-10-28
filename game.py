from functools import partial
from kivy.core.window import Window
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
    fan_pile = 0.18

    def __init__(self, root=None, on_move=None, menu_size=0):
        self.padding = int(self.x_padding*Window.width), int(self.y_padding*Window.height)
        Logger.info("Cards: window size=%d %d menu size=%d" % (Window.width, Window.height, menu_size))
        self.set_scale(menu=menu_size)
        Logger.info("Cards: card size = %d x %d" % self.card_size)
        self.fan_pile = int(self.fan_pile*self.card_size[1])
        Logger.info("Cards: fan pile =  %d" % self.fan_pile)
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
        for _, group in self.piles.iteritems():
            for pile in group: pile.clear(base)
        self.won = False

    # split window into rows and cols
    def set_scale(self, width=Window.width, height=Window.height, menu=0, horiz=False):
        h = (height-menu)/self.num_rows - self.padding[1]
        csize = self._set_cell_size(int(h/Card.aspect_ratio), int(h))
        if self.num_cols*csize[0] <= Window.width:
            self.x0 = int((width-csize[0]*self.num_cols)/2) + self.padding[0]/2
            self.y0 = height + self.padding[1]/2
            Logger.info("Cards: set scale from window height: origin = %d %d" % (self.x0,self.y0))
        else:
            w = width/self.num_cols - self.padding[0]
            csize = self._set_cell_size(w, int(w*Card.aspect_ratio))
            self.x0 = self.padding[0]/2
            self.y0 = height + self.padding[1]/2
            Logger.info("Cards: set scale from window width: origin = %d %d" % (self.x0,self.y0))

    def _set_cell_size(self, w, h):
        self.card_size = (w, h)
        return w+self.padding[0], h+self.padding[1]

    # convert from column and row to screen coords
    def pos(self, col, row):
        x = self.x0 + col*(self.card_size[0]+self.padding[0])
        y = self.y0 - (row+1)*(self.card_size[1]+self.padding[1])
        return int(x), int(y)

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
        pile.on_release = lambda : self.on_release(pile)
        self.piles[pile.type].append(pile)

    # can we move num cards from orig to dest?
    def try_move(self, orig, dest, num, callback=False, collide=False):
        if dest is orig: return False
        #Logger.debug("Cards: try_move %d from %r to %r" % (num, orig.pid(), dest.pid()))
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
    def on_release(self, pile):
        Logger.debug("Cards: on_release %s %d" % (pile.type,pile.index))
        top = pile.top()
        if top.cards() == 0 or top.top_card() is None: return False
        Logger.debug("Cards: %d cards released top=%s bot=%s" % 
                     (top.cards(),top.top_card(),top.bottom_card()))
        # build on foundation or tableau?
        moved = False
        for typ in ['foundation','tableau','waste']:
            for dest in self.piles[typ]:
                moved = self.try_move(pile, dest, top.cards(), collide=True)
                if moved: break
            if moved: break
        else:
            Logger.debug("Cards: move back")
            pile.move_cards_back()
            return None
        return top
   
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


