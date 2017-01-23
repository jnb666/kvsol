import random
import ast

# card object - has rank (1-13) and suit (c,d,h,s)
class Card(object):
    aspect_ratio = 314.0/226.0

    def __init__(self, rank, suit, faceup=False):
        self.rank = rank
        self.suit = suit
        self.faceup = faceup
   
    def __str__(self):
        return "%d%s faceup=%s" % (self.rank,self.suit,self.faceup)

    def image(self):
        if self.faceup:
            return "images/%d%s.png" % (self.rank,self.suit)
        else:
            return 'images/back2.png'

    def color(self):
        if self.suit == 'c' or self.suit == 's': return 1
        return -1

    def next_rank(self, order, wrap):
        next = self.rank + order
        if wrap:
            if next > Deck.king: next = Deck.ace
            if next < Deck.ace: next = Deck.king
        return next

    def export(self):
        return (self.rank,self.suit,True) if self.faceup else (self.rank,self.suit)

    @staticmethod
    def base_image(suit=''):
        return "images/bot%s.png" % suit


# deck is list of decks*52 cards - object with option to persist data
class Deck(object):
    suits = ['c', 's', 'h', 'd']
    ace = 1
    jack = 11
    queen = 12
    king = 13

    def __init__(self, decks, config=None):
        self.i = 0
        self.decks = decks
        if config is None:
            self.d = [Card(r,s) for _ in range(decks) for s in self.suits for r in range(1,14)]
        else:
            self.load(config)
 
    def rewind(self, shuffle=False):
        self.i = 0
        for card in self.d: card.faceup = False
        if shuffle: random.shuffle(self.d)

    def get(self, index):
        return self.d[index]

    def next(self, faceup=False):
        card = self.d[self.i]
        card.faceup = faceup
        self.i += 1
        return card

    def load(self, config):
        cards = ast.literal_eval(config.get('game', 'deck'))
        self.d = [Card(*c) for c in cards]

    def save(self, config):
        cards = [card.export() for card in self.d]
        config.set('game', 'deck', cards)


