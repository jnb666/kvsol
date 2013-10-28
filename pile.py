import ast
from kivy.core.window import Window
from kivy.properties import ListProperty, NumericProperty, ObjectProperty
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter
from kivy.logger import Logger

from cards import Card, Deck
from game import BaseGame

# mixin class for group of cards
class CardsList(object):
    images = ListProperty([])
    split = False

    def cards(self): return len(self.images)

    def card_list(self): return [i.card for i in self.images]

    def top_card(self): return self.images[-1].card

    def bottom_card(self): return self.images[0].card


# on screen card image
class CardImage(Image, CardsList):
    alpha = NumericProperty(0)
    yoffset = NumericProperty(0)
    callback = ObjectProperty(None)
    card = ObjectProperty(None)
 
    def __init__(self, **kwargs):
        super(CardImage, self).__init__(**kwargs)
        self.images.append(self)

    def on_touch_down(self, touch):
        if self.callback and self.collide_point(*touch.pos):
            touch.grab(self)
            self.callback()
            return True

    def lock(self, state): pass


# draggable set of one or more card images
class CardScatter(Scatter, CardsList):
    callback = ObjectProperty(None)
    pile = ObjectProperty(None)
    selected = 0
    
    # add a new image to top of pile
    def add_image(self, img, xstep, ystep):
        self.y -= ystep
        self.width += xstep
        self.height += ystep
        for child in self.images: 
            child.y += ystep
            child.yoffset += ystep
        self.images.append(img)
        self.add_widget(img)

    # remove bottom image, but keep widget in same place
    def remove_image(self):
        if not self.images: return None
        img = self.images.pop(0)
        self.remove_widget(img)
        self.width -= self.pile.xstep
        self.height -= self.pile.ystep
        img.y -= img.yoffset
        img.yoffset = 0
        return img
     
    # select one or more cards from the group
    def on_touch_down(self, touch):
        if not super(CardScatter, self).on_touch_down(touch): return False
        if self is self.pile.top():
            self.auto_bring_to_front = True
            # which image was touched?
            self.selected = 0
            for child in list(reversed(self.images)):
                child.alpha = 1
                self.selected += 1
                if touch.pos[1] <= self.y+child.y+child.height: break 
            Logger.debug("Cards: selected %d out of %d cards" % (self.selected, self.cards()))
            if self.selected < self.cards():
                self.split = self.pile.split_top_widget(self.selected)
        return True
 
    # release the selection, dragging to new location
    def on_touch_up(self, touch):
        if not super(CardScatter, self).on_touch_up(touch): return False
        if self.selected > 0:
            for child in self.images:
                child.alpha = 0
            if self.callback: self.callback()
            self.selected = 0
        return True

    # make the scatter not movable if covered
    def lock(self, state):
        self.auto_bring_to_front = not state
        self.do_translation_x = not state
        self.do_translation_y = not state
 

# pile of cards on screen
class Pile(object):
    type = ''
    index = 0

    def __init__(self, game, col, row, suit='', fan='', show_count='', on_touch=None):
        self.suit = suit
        self.xstep = game.fan_pile if fan == 'right' else 0
        self.ystep = game.fan_pile if fan == 'down' else 0
        Logger.debug("Cards: new pile type=%s pos=%d %d fan=%s %d %d" % 
                    (self.type, col, row, fan, self.xstep, self.ystep))
        self.game = game
        self.layout = game.layout
        self.csize = game.card_size
        self.x, self.y = game.pos(col, row)
        self.xpos, self.ypos = self.x, self.y
        self.widgets = []
        self.counter = None
        self.draw_base(Card.base_image(suit), on_touch, show_count)
        self.clear(1)

    # accessors
    def base(self): return self.widgets[0]

    def size(self): return len(self.widgets)-1

    def top(self): return self.widgets[-1]

    def bottom(self): return self.widgets[1]

    def next(self): return self.widgets[-2]

    def pid(self): return (self.type, self.index)

    def __str__(self): return "%s%d" % self.pid()

    # build rules
    def by_rank(self, card, base=None, order=1, suit=None, wrap=False):
        if suit is not None and card.suit != suit:
            return False
        else:
            if self.size() ==0:
                return base is None or card.rank == base
            else:
                top = self.top().top_card()
                return card.rank == top.next_rank(order,wrap)

    def by_alt_color(self, card, base=None, order=1, wrap=False):
        if self.size() == 0:
            return base is None or card.rank == base
        else:    
            top = self.top().top_card()
            return card.color() != top.color() and card.rank == top.next_rank(order,wrap)

    # draw bottom of pile
    def draw_base(self, image, on_touch, show_count):
        self.widgets.append(CardImage(source=image, size=self.csize, pos=(self.x,self.y)))
        if on_touch:
            self.base().callback = on_touch
        self.layout.add_widget(self.base())
        if show_count:
            if show_count == 'right':
                pos = self.x+self.csize[0], self.y+(self.csize[1]-Counter.ysize)/2
            elif show_count == 'left':
                pos = self.x-Counter.xsize, self.y+(self.csize[1]-Counter.ysize)/2
            else:
                pos = self.x+(self.csize[0]-Counter.xsize)/2, self.y-Counter.ysize
            self.counter = Counter(pos=pos)
            self.layout.add_widget(self.counter)
 
    # empty the pile
    def clear(self, base):
        self.xpos, self.ypos = self.x, self.y
        for w in self.widgets[base:]:
            self.layout.remove_widget(w)            
        del self.widgets[base:]
        if self.counter: 
            if base == 0: self.layout.remove_widget(self.counter)
            self.counter.count = 0

    # add list of cards
    def add_cards(self, cards, faceup=None):
        for c in cards:
            if faceup != None: c.faceup = faceup
            self.add_card(c)
        return len(cards)

    # add card onto top 
    def add_card(self, card):
        #Logger.debug("cards: add %s to %s %d" % (card, self.type, self.index))
        top = self.top()
        img = CardImage(card=card, source=card.image(), size=self.csize)
        if (card.faceup and self.type != 'waste' and
                top.top_card() and top.top_card().faceup and 
                self.game.can_join(self, card) ):
            #Logger.debug("cards: add to existing scatter")
            top.add_image(img, self.xstep, self.ystep)
        else:
            if card.faceup:
                top = CardScatter(size=self.csize, pos=(self.xpos,self.ypos), 
                        callback=self.on_release, pile=self)
                top.add_image(img, 0, 0)
            else:
                img.pos = (self.xpos,self.ypos)
                top = img
            # lock underneath widgets so we can't move em
            for under in self.widgets: under.lock(True)
            self.layout.add_widget(top)
            self.widgets.append(top)
        self.xpos += self.xstep
        self.ypos -= self.ystep
        if self.counter: self.counter.count += 1

    # pop the top card(s)
    def remove_cards(self):
        if self.size() == 0: return []
        w = self.widgets.pop()
        self.layout.remove_widget(w)
        self.xpos -= self.xstep*w.cards()
        self.ypos += self.ystep*w.cards()
        if self.counter: self.counter.count -= w.cards()
        return w.card_list()
    
    # pop top card(s) and optionally show card underneath
    def take_cards(self, expose=False, flip=False):
        cards = self.remove_cards()
        if flip:
            for c in cards: c.faceup = not(c.faceup)
        if expose and self.size() > 0:
            card2 = self.remove_cards()
            self.add_cards(card2, faceup=True)
        return cards

    # move top card(s) to another pile - returns no. of cards moved
    def move_cards_to(self, dest, expose=False, cover=False, flip=False):
        cards = self.take_cards(expose, flip)
        if cover and dest.size() > 0:
            # undo expose
            card2 = dest.remove_cards()
            dest.add_cards(card2, faceup=False)
        return dest.add_cards(cards)
 
    # move given number of cards to another pile
    def move_num_cards_to(self, dest, total, expose=False, cover=False, flip=False):
        moved = 0
        while moved < total:
            num = self.top().cards()
            if moved + num <= total:
                moved += self.move_cards_to(dest, expose, cover, flip)
            else:
                ok = self.split_top_widget(total-moved)
                if not ok: return

    # split the scatter on top into two as we've partally grabbed it
    # note: assumes fan='down'
    def split_top_widget(self, selected):
        top = self.top()
        if top.cards() <= selected:
            Logger.warning("Cards: can't split %d out of %d" % (selected, top.cards()))
            return False
        self.layout.remove_widget(top)
        ypos = top.y + top.cards()*self.ystep
        size = (self.csize[0], self.csize[1]-self.ystep)
        under = CardScatter(size=size, pos=(top.x, ypos), callback=top.callback, pile=self)
        for _ in range(top.cards()-selected):
            under.add_image(top.remove_image(), self.xstep, self.ystep)
        self.widgets.insert(-1, under)
        self.layout.add_widget(under)
        self.layout.add_widget(top)
        return True

    # move the top card(s) back to starting position
    def move_cards_back(self):
        w = self.top()
        if w.split:
            Logger.debug("Cards: rejoin split pile - cards=%d" % w.cards())
            self.move_cards_to(self)
        else:
            w.pos = (self.xpos-self.xstep, self.ypos+self.ystep)

    # writes cards on stack to config file
    def save(self, config):
        data = []
        for group in self.widgets[1:]:
            data += [card.export() for card in group.card_list()]
        config.set('piles', str(self), data)

    # read back the data
    def load(self, config):
        name = str(self)
        self.clear(1)
        if config.has_option('piles', name):
            cards = ast.literal_eval(config.get('piles', name))
            for card in cards:
                self.add_card(Card(*card))
            if self.counter: 
                self.counter.count = len(cards)


# types of pile
class Foundation(Pile):
    type = 'foundation'

class Tableau(Pile):
    type = 'tableau'

class Waste(Pile):
    type = 'waste'


# label with no. of cards in pile
class Counter(Label):
    count = NumericProperty(0)
    xsize = Window.width*0.03
    ysize = Window.height*0.03


