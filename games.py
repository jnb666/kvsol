from functools import partial
from kivy.logger import Logger
from cards import Deck
from pile import Foundation, Tableau, Waste
from game import BaseGame


class Yukon(BaseGame):
    name = 'Yukon'
    help = """\
Foundations are built up in suit from Ace to King.

The tableau piles build down by alternate colour. Any group of cards can be moved as long as the base card of the group can build on the top card of the destination pile. If the pile is empty then the base card must be a King.

Cards can also be moved back from the foundations.
    """
    decks = 1
    num_tableau = 7
    num_waste = 0
    num_cols = 8
    num_rows = 4.7
    tableau_pos = 0
    foundation_pos = [(7,i) for i in range(4)]
    tableau_depth = [(0,1)] + [(i,5) for i in range(1,7)]

    # setup the initial game layout
    def build(self):
        for i in range(self.num_tableau):
             self.add_pile(Tableau(self, i, self.tableau_pos, fan='down'))
        for i, s in enumerate(Deck.suits):
            self.add_pile(Foundation(self, *self.foundation_pos[i], suit=s))

    # deal initial cards to given pile
    def start(self, pile, deck):
        if pile.type == 'tableau':
            for i in range(self.tableau_depth[pile.index][0]):
                pile.add_card(deck.next())
            for i in range(self.tableau_depth[pile.index][1]):
                pile.add_card(deck.next(True))

    # can we add num cards from group to pile?
    def can_add(self, src, pile, group, num):
        if pile.type == 'foundation':
            # foundation builds by suit from ace
            return num == 1 and pile.by_rank(group.top_card(), base=Deck.ace, suit=pile.suit)
        elif pile.type == 'tableau':
            # tableau builds down by alternate color from king
            return pile.by_alt_color(group.bottom_card(), base=Deck.king, order=-1)


class Klondike(Yukon):
    name = 'Klondike'
    help = """\
Foundations are built up in suit from Ace to King.

The tableau piles build down by alternate colour. An empty space can only be filled by a sequence starting with a King.

Touch the deck at top left to deal onto the waste or to redeal the pack if empty. There is no limit to the number of redeals. Cards can also be moved back from the foundations.
    """
    num_waste = 2
    num_cols = 7
    num_rows = 4.25
    y_padding = 0.04
    tableau_pos = 1
    deal_by = 1
    foundation_pos = [(i+3,0) for i in range(4)]
    tableau_depth = [(i,1) for i in range(7)]

    # setup the initial game layout
    def build(self):
        super(Klondike, self).build()
        self.add_pile(Waste(self, 0, 0, show_count='base', on_touch=self.deal_next))
        self.add_pile(Waste(self, 1, 0, show_count='base'))

    # deal initial cards to given pile
    def start(self, pile, deck):
        super(Klondike, self).start(pile, deck)
        if pile.type == 'waste':
            if pile.index == 0:
                for _ in range(24-self.deal_by):
                    pile.add_card(deck.next())
            else:
                for _ in range(self.deal_by):
                    pile.add_card(deck.next(True))

    # callback to deal next 3 cards
    def deal_next(self):
        Logger.debug("Cards: deal")
        pile, waste = self.waste()
        if pile.size() > 0:
            self.move(pile, waste, min(self.deal_by, pile.size()), flip=True)
        else:
            num = waste.size()
            Logger.debug("Cards: pick up %d cards from waste" % num)
            self.move(waste, pile, num, flip=True, append=True)

    # auto-deal onto empty waste pile
    def on_moved(self, move):
         pile, waste = self.waste()
         if waste.size() == 0 and pile.size() > 0:
            self.move(pile, waste, min(self.deal_by, pile.size()), flip=True, append=True, callback=None)


class Klondike3(Klondike):
    name = 'Klondike by Threes'
    help = """\
As per Klondike, but cards are dealt three at a time from the pack.
"""
    deal_by = 3


class FreeCell(BaseGame):
    name = 'Freecell'
    help = """\
Foundations are built up in suit from Ace to King. The four free cells at top left can hold any one card.

The tableau piles build down by alternate colour. The number of cards which can be moved is limited by the number of free cells. An empty space can be filled by a any sequence of cards.
    """
    decks = 1
    num_tableau = 8
    num_waste = 4
    num_cols = 9
    num_rows = 4.7

    # setup the initial game layout
    def build(self):
        for i in range(self.num_waste):
            self.add_pile(Waste(self, i, 0))
        for i, s in enumerate(Deck.suits):
            self.add_pile(Foundation(self, i+self.num_waste+1, 0, suit=s))
        for i in range(self.num_tableau):
            self.add_pile(Tableau(self, i+0.5, 1, fan='down'))

    # deal initial cards to given pile
    def start(self, pile, deck):
        if pile.type == 'tableau':
            depth = 7 if pile.index < 4 else 6
            for _ in range(depth):
                 pile.add_card(deck.next(True))

    # limit number of cards moved to number of free cells
    def free_cells(self):
        return sum([1 for p in self.waste() if p.size() == 0])

    # can we add num cards from group to pile?
    def can_add(self, src, pile, group, num):
        if pile.type == 'waste':
            # free cells take one card
            return num == 1 and pile.size() == 0
        elif pile.type == 'foundation':
            # build by suit on foundations
            return num == 1 and pile.by_rank(group.top_card(), base=Deck.ace, suit=pile.suit)
        elif pile.type == 'tableau':
            # build down by alternate colour on tableau
            return num <= self.free_cells()+1 and pile.by_alt_color(group.bottom_card(), order=-1)
 
    # can we pick up this card together with the given group
    def can_join(self, pile, card):
        if pile.type == 'tableau':
            return pile.by_alt_color(card, order=-1)
        else:
            return True


class Gypsy(BaseGame):
    name = 'Gypsy'
    help = """\
Foundations are built up in suit from Ace to King.

The tableau piles build down by alternate colour. An empty space can be filled by any sequence of cards.

Touch the deck at bottom right to deal a new card onto each of the tableau piles. Cards can also be moved back from the foundations.
    """
    decks = 2
    num_tableau = 8
    num_waste = 1
    num_cols = 10
    y_padding = 0.01
    num_rows = 5
    tableau_pos = (0,0)
    foundation_pos = [(8,i) for i in range(4)] + [(9,i) for i in range(4)]
    waste_pos = (8.5,4)
    tableau_depth = [3 for i in range(8)]
    waste_depth = 80

    # setup the initial game layout
    def build(self):
        for i in range(self.num_tableau):
            self.add_pile(Tableau(self, i+self.tableau_pos[0], self.tableau_pos[1], fan='down'))
        for i, s in enumerate(Deck.suits*self.decks):
            self.add_pile(Foundation(self, *self.foundation_pos[i], suit=s))
        self.add_pile(Waste(self, self.waste_pos[0], self.waste_pos[1], show_count='right', 
            on_touch=self.deal_next))

    # deal initial cards to given pile
    def start(self, pile, deck):
        if pile.type == 'tableau':
            for i in range(self.tableau_depth[pile.index]-1):
                pile.add_card(deck.next())
            pile.add_card(deck.next(True))
        elif pile.type == 'waste':
            for _ in range(self.waste_depth):
                pile.add_card(deck.next())

    # can we add num cards from group to pile?
    def can_add(self, src, pile, group, num):
        if pile.type == 'foundation':
            # build up by suit
            return num == 1 and pile.by_rank(group.top_card(), base=Deck.ace, suit=pile.suit)
        elif pile.type == 'tableau':
            # build down by alternate colour, anything on space
            return pile.by_alt_color(group.bottom_card(), order=-1)
        return False

    # can we pick up this card together with the given group
    def can_join(self, pile, card):
        if pile.type == 'tableau':
            return pile.by_alt_color(card, order=-1)
        else:
            return True

    # deal cards from waste onto tableau
    def deal_next(self):
        Logger.debug("Cards: deal to tableau")
        self.deal_cards(self.waste()[0], self.tableau())


class Hypotenuse(Gypsy):
    name = 'Hypotenuse'
    help = """\
Similar to Gypsy, but only Kings on empty spaces.
    """
    num_tableau = 10
    tableau_pos = (0,1)
    foundation_pos = [(2+i,0) for i in range(8)]
    tableau_depth = [10-i for i in range(10)]
    waste_pos = (0,0)
    waste_depth = 49

    # as per Gypsy but only Kings on empty tableau piles
    def can_add(self, src, pile, group, num):
        if pile.type == 'foundation':
            return num == 1 and pile.by_rank(group.top_card(), base=Deck.ace, suit=pile.suit)
        elif pile.type == 'tableau':
            return pile.by_alt_color(group.bottom_card(), order=-1, base=Deck.king)
        return False


class Spider(BaseGame):
    name = 'Spider'
    help = """\
Tableau piles build down, regardless of suit, but only sequences of the same suit can be moved. Any base card can be built on an empty space.

Only when a sequence of of 13 cards of the same suit is built can they be moved to the foundations.

Touch the deck at top left to deal a new card onto each of the tableau piles. 
    """
    decks = 2
    num_tableau = 10
    num_waste = 1
    num_cols = 10
    num_rows = 5
    y_padding = 0.01
    tableau_depth = [6,5,5,6,5,5,6,5,5,6]

    # setup the initial game layout
    def build(self):
        self.add_pile(Waste(self, 0, 0, show_count='right', on_touch=self.deal_next))
        for i in range(self.num_foundation):
            self.add_pile(Foundation(self, i+2, 0))
        for i in range(self.num_tableau):
            self.add_pile(Tableau(self, i, 1, fan='down'))

    # deal initial cards to given pile
    def start(self, pile, deck):
        if pile.type == 'tableau':
            for i in range(self.tableau_depth[pile.index]-1):
                 pile.add_card(deck.next())
            pile.add_card(deck.next(True))
        elif pile.type == 'waste':
            num = 52*self.decks-sum(self.tableau_depth)
            for _ in range(num):
                 pile.add_card(deck.next())

    # auto drop disabled
    def auto_drop(self):
        return False

    # can we add num cards from group to pile?
    def can_add(self, src, pile, group, num):
        if pile.type == 'foundation':
            # can only move whole pack to foundation
            return num == 13
        elif pile.type == 'tableau' and src.type == 'tableau':
            # build down by rank, any suit, anything on empty pile, no move back from foundation
            return pile.by_rank(group.bottom_card(), order=-1)
        return False

    # can only pickup groups by suit
    def can_join(self, pile, card):
        if pile.type == 'tableau':
            return pile.by_rank(card, order=-1, suit=pile.top().top_card().suit)
        else:
            return True

    # deal cards from waste onto tableau
    def deal_next(self):
        Logger.debug("Cards: deal spider")
        # can't deal onto empty piles
        for i, dest in enumerate(self.tableau()):
            if dest.size() == 0: return
        self.deal_cards(self.waste()[0], self.tableau())


class Forty(BaseGame):
    name = 'Forty Thieves'
    help = """\
Foundations are built up in suit from Ace to King.

The tableau piles build down by suit. Only the top card can be moved. An empty space can be filled by any card.

Touch the deck at top left to deal a new card onto the waste pile if empty. There is no redeal.
    """
    decks = 2
    num_tableau = 10
    num_waste = 2
    num_cols = 10
    y_padding = 0.04
    num_rows = 4.3

    # setup the initial game layout
    def build(self):
        for deck in range(self.decks):
            for i, s in enumerate(Deck.suits):
                self.add_pile(Foundation(self, 4*deck+i+2, 0, suit=s))
        for i in range(self.num_tableau):
            self.add_pile(Tableau(self, i, 1, fan='down'))
        self.add_pile(Waste(self, 0, 0, show_count='base', on_touch=self.deal_next))
        self.add_pile(Waste(self, 1, 0, show_count='base'))

    # deal initial cards to given pile
    def start(self, pile, deck):
        Logger.debug("Cards: Forty start pile %s" % pile)
        if pile.type == 'tableau':
            for i in range(4):
                pile.add_card(deck.next(True))
        elif pile.type == 'waste':
            if pile.index == 0:
                for _ in range(63):
                    pile.add_card(deck.next())
            else:
                pile.add_card(deck.next(True))

    # can only pick up one card at a time
    def can_join(self, pile, card):
        return False

    # can we add num cards from group to pile?
    def can_add(self, src, pile, group, num):
        if pile.type == 'foundation':
            # built on foundations by suit ascending from ace
            return pile.by_rank(group.top_card(), base=Deck.ace, suit=pile.suit)
        elif pile.type == 'tableau':
            # build on tableau by suit descending - only one card can be moved
            suit = pile.top().top_card().suit if pile.size() else None
            return pile.by_rank(group.top_card(), order=-1, suit=suit)
        return False

    # callback to deal next card - no redeal
    def deal_next(self):
        Logger.debug("Cards: deal forty")
        pile, waste = self.waste()
        if pile.size() > 0:
            self.move(pile, waste, 1, flip=True)

    # auto-deal onto empty waste pile
    def on_moved(self, move):
        pack, waste = self.waste()
        if waste.size() == 0 and pack.size() > 0:
            self.move(pack, waste, 1, flip=True, append=True, callback=None)


class Terrace(BaseGame):
    name = 'Terrace'
    help = """\
First move one of the 4 cards on the tableau to a foundation to set the base rank. After this foundations build up from this rank by alternate colour wrapping from King to Ace.

Tableau piles build down by alternate colour. Only a single card can be moved. Any empty spaces are automatically filled from the deck.

The reserve of 11 cards can only be played onto the foundation piles. Cards can not be moved back from the foundations. 
    """
    decks = 2
    num_tableau = 9
    num_waste = 3
    num_cols = 10.2
    num_rows = 5
    y_padding = 0.01
    foundation_suit = [''] * 8

    # setup the initial game layout
    def build(self):
        for i in range(self.num_foundation):
            self.add_pile(Foundation(self, i+0.5, 0, suit=self.foundation_suit[i]))
        for i in range(self.num_tableau):
            self.add_pile(Tableau(self, i, 1, fan='down'))
        self.add_pile(Waste(self, 9, 0, fan='down'))
        self.add_pile(Waste(self, 9, 3, show_count='right', on_touch=self.deal_next))
        self.add_pile(Waste(self, 9, 4, show_count='right', on_touch=self.deal_next))

    # deal initial cards to given pile
    def start(self, pile, deck):
        if pile.type == 'tableau' and pile.index < 4:
            pile.add_card(deck.next(True))
        elif pile.type == 'waste':
            if pile.index == 0:
                for _ in range(11):
                    pile.add_card(deck.next(True))
            elif pile.index == 1:
                for _ in range(89):
                    pile.add_card(deck.next())

    # can only pick up one card at a time
    def can_join(self, pile, card):
        return False

    # base of foundation piles
    def base_rank(self):
        for pile in self.foundation():
            if pile.size() > 0:
                return pile.bottom().bottom_card().rank
        return 0

    # can we add num cards from group to pile?
    def can_add(self, src, pile, group, num):
        card = group.top_card()
        reserve = self.waste()[0]
        base = self.base_rank()
        if base == 0:
            # first move must be from tableau to foundation
            return src.type == 'tableau' and pile.type == 'foundation'
        elif src.type != 'foundation':
            if pile.type == 'foundation':
                # build up by alternate colour, ace on king from base rank we selected
                return pile.by_alt_color(card, base=base, wrap=True)
            elif pile.type == 'tableau' and src is not reserve:
                # build down by alternate colour, king on ace, anything on space
                return pile.by_alt_color(card, order=-1, wrap=True)
        return False

    # deal one card from pile onto waste
    def deal_next(self, append=False, callback=False):
        pile, waste = self.waste()[1:]
        if pile.size() > 0 and self.base_rank() > 0:
            Logger.debug("Cards: terrace -> deal from pack")
            self.move(pile, waste, 1, flip=True, append=append, callback=callback)

    # refill waste from deck if empty and if any of the tableau piles are empty fill from waste
    # will implicitly call back this function 
    def on_moved(self, move):
        pile, waste = self.waste()[1:]
        if self.base_rank() == 0 or pile.size() == 0: return
        if waste.size() == 0:
            self.deal_next(True, None)
        else:
            for pile in self.tableau():
                if pile.size() == 0:
                    Logger.debug("Cards: deal to empty tableau pile %d" % pile.index)
                    self.move(waste, pile, 1, append=True, callback=None)
                    return


class Generals(Terrace):
    name = "General's Patience"
    help = """\
General's Patience is a varient of Terrace. Rules are the same except that foundations are built up by suit.
    """
    foundation_suit = Deck.suits * 2

    # like terrace but foundations build by suit
    # can we add num cards from group to pile?
    def can_add(self, src, pile, group, num):
        card = group.top_card()
        reserve = self.waste()[0]
        base = self.base_rank()
        if base == 0:
            # first move must be from tableau to foundation
            return src.type == 'tableau' and pile.type == 'foundation' and pile.suit == group.top_card().suit
        elif src.type != 'foundation':
            if pile.type == 'foundation':
                # build up by alternate colour, ace on king from base rank we selected
                return pile.by_rank(card, base=base, suit=pile.suit, wrap=True)
            elif pile.type == 'tableau' and src is not reserve:
                # build down by alternate colour, king on ace, anything on space
                return pile.by_alt_color(card, order=-1, wrap=True)
        return False


