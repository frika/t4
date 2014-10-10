#!/usr/bin/python
# -*- coding: utf-8; mode: python; ispell-local-dictionary: "english"; -*-

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2014 by Diedrich Vorberg <diedrich@tux4web.de>
##
##  All Rights Reserved
##
##  For more Information on orm see the README file.
##
##  This program is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 2 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program; if not, write to the Free Software
##  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
##
##  I have added a copy of the GPL in the file gpl.txt.

"""
These classes represent rich text. They contain methods to
calculate information on the objects they represent (size on the page
etc.)  and functions draw them into a box.

The model is a tree of objects.

The root is a richtext objects, which contains 1..n
boxes, which each contain a mix of 1..n boxes and/or paragraphs.
paragraphs, which each contain 1..n
words, which each contain 1..n
syllables.

Note that “word” and “syllable” are technical not linguistic units here.
Refer to the class descriptions below for details.
"""

import types, unicodedata, itertools
from t4.utils import here_and_next

import styles

class _node(list):
    """
    An abstract base class for our node types.
    """
    def __init__(self, children=[], style=None):
        self._parent = None
        self._style = style
        
        for child in children:
            self.append(child)


    def _set_parent(self, parent):
        assert self.parent is None, ValueError(
            "The node %s has already been inserted." % repr(self))
        self._parent = parent

    @property
    def parent(self):
        return self._parent

    @property
    def style(self):
        assert self._parent is not None, AttributeError(
            "The style attribute is only available after the "
            "parent has been set. (%s)" % repr(self))
        return self.parent.style + self._style

        
    def remove_empty_children(self):
        for child in children:
            child.remove_empty_children()

        i = 0
        while i < len(self):
            if child[i].empty():
                del self[i]
            else:
                i += 1

    def empty(self):
        return len(self) == 0

    def __repr__(self):
        return self.__class__.__name__ + ":" + list.__repr__(self)
        

    # Methods from the list class we need to overload.
    def _check_child(self, child):
        raise NotImplemented("The _node class is an abstract base, don’t "
                             "instantiate it at all.")
        
    def append(self, child):
        self._check_child(child)
        child._set_parent(self)
        list.append(self, child)

    def __setitem__(self, key, child):
        self._check_child(child)
        child._set_parent(self)
        list.__setitem__(self, key, child)

    def __setslice__(self, i, j, sequence):
        map(self._check_child, sequence)
        map(lambda child: child._set_parent(self), sequence)
        list.__setslice__(self, i, j, squence)

    def _style_info(self):
        if self._parent is None:
            return "_" + repr(self._style)
        else:
            return repr(self.style)

    def __repr__(self):
        return self.__class__.__name__ + " " + self._style_info()
            
    def __print__(self, indentation=0):
        print indentation * "  ", repr(self)
            
        for child in self:
            child.__print__(indentation+1)
            
        

class richtext(_node):
    """
    This is the root node for a richtext tree.
    """
    def __init__(self, children=[], style=None):
        assert style is not None, ValueError(
            "A richtext’s style may not be None.")
        _node.__init__(self, children, style)
    
    def _check_child(self, child):
        assert isinstance(child, box), TypeError

    @property
    def style(self):
        return self._style        

class box(_node):
    """
    This is a box with margin, padding and background.
    """
    def _check_child(self, child):
        assert isinstance(child, (paragraph, box,)), TypeError(
            "Can’t add %s to a box, only paragraphs and boxes." % repr(child))

class paragraph(_node):
    """
    This is a block of text. Think <div>.
    """
    def _check_child(self, child):
        assert isinstance(child, word), TypeError(
            "Can’t add %s to a paragraph, only texts." % repr(child))

    def lines(self, width, first_word_idx=0):
        """
        Yield _line objects for the current paragraph, starting with the
        word at `first_word_idx`, fittet to a box `width`.
        """
        while True:
            line = self._line(self, width, first_word_idx)
            yield line
            if line.last:
                break

    def words_starting_with(self, index):
        """
        Yield pairs as (index, word), starting with the word in self
        at `index`.
        """
        for i, word in enumerate(self[index:]):
            yield index + i, word,
                
    class _line(object):
        """
        This class represents one line of a paragraph and allows to
        render it to a PostScript box (a t4.psg.drawing.box.canvas object).

        @ivar paragraph: The paragraph we’re part of.
        @ivar width: The box’s width we’ve been calculated for.
        @ivar first_word_idx: The index in the paragraph of the first word
           we contain.
        @ivar last_word_idx: Ditto, last word.
        @ivar space_used: Horizontal space used by all our words, including
           intermediate white space.
        @ivar word_space_used: Ditto, w/o the white space.
        @ivar white_space_used: The difference of above two.
        """
        def __init__(self, paragraph, width, first_word_idx):
            self.paragraph = paragraph
            self.width = width
            self.first_word_idx = first_word_idx

            # Ok, let’s see which words fit the width.
            self.words = []

            self.space_used = 0.0
            self.word_space_used = 0.0
            self.white_space_used = 0.0

            for idx, word in paragraph.words_starting_with(first_word_idx):
                word_width = word.width()
                space_width = word.space_width()
                if self.space_used + word_width <= width:
                    self.words.append(word)
                    
                    self.space_used += word_width + space_width
                    self.word_space_used += word_width
                    self.white_space_used += space_width
                else:
                    # This is where we’d have to ask word, if it can by
                    # hyphenated.
                    break
                    
            self.last_word_idx = idx
            self.last = ( idx == len(self.paragraph)-1 )

        def height(self):
            """
            The height of a line is the maximum height of the contained words.
            """
            return max(map(lambda word: word.height(), self))

        def cenders(self):
            """
            Return a tripple of floats, the maximum ascender, median and
            descender of all our syllables.
            """
            # This works exactly as word.cenders() and is a copy.
            cenders = map(lambda word: word.cenders(), self.words)
            ascenders, medians, descenders = zip(*cenders)
            return max(ascenders), max(medians), max(descenders),

        def render(self, canvas):
            ascender, median, descender = self.cenders()

            # The coordinate system’s origin is in the lower left.
            # The vertical coordinate of the baseline is the height of the
            # descender.
            baseline_y = descender

            # Translate the canvas’ coordinate system so that the baseline
            # is y=0.
            print >> canvas, "gsave"            
            print >> canvas, 0, baseline_y, "translate"
            print >> canvas, 0, 0, "moveto"
            
            # For word.render() to work properly, we need to position the
            # cursor on the baseline, at the beginning of the word.
            def left_xs():
                """
                Yield the x coordinate for each word on this line.
                """
                x = 0.0
                for word in self.words:
                    yield x
                    x += word.width() + word.space_width()

            # For the time being.
            right_xs = left_xs
            center_xs = left_xs
            justify_xs = left_xs
                
            xs = { "left": left_xs,
                   "right": right_xs,
                   "center": center_xs,
                   "justify": justify_xs, }[self.paragraph.style.text_align] 
            
            for x, word in zip(xs(), self.words):
                print >> canvas, x, 0, "moveto"
                word.render(canvas)
            
            print >> canvas, "grestore"
            
class word(_node):
    """
    A ‘word’ is a technical unit. Between words, line wrapping occurs.
    """
    def _check_child(self, child):
        assert isinstance(child, syllable), TypeError(
            "Can’t add %s to a word, only syllables." % repr(child))

    def width(self):
        """
        The width of a word is the sum of the widths of its syllables, duh.
        """
        return sum(map(lambda syllable: syllable.width(), self))

    def cenders(self):
        """
        Return a triplle of floats, the maximum ascender, median and
        descender of all our syllables.
        """
        cenders = map(lambda syllable: syllable.cenders(), self)
        ascenders, medians, descenders = zip(*cenders)
        return max(ascenders), max(medians), max(descenders)

    def height(self):
        """
        The height of a word is the sum of its cenders.
        """
        return sum(self.cenders())

    def space_width(self):
        """
        Return the width of the space charater in our last syllable’s font
        """
        return self[-1].space_width()
        
    def __repr__(self):
        return "%s %.1f×%.1f" % ( _node.__repr__(self),
                                  self.width(), self.height(), )

    def render(self, canvas):
        """
        Render the word on the canvas (t4.psg.drawing.box.canvas object).
        This function assumes that the baseline is y=0 and that the cursor
        is located at the position of the first letter.
        """
        for syllable in self:
            syllable.render(canvas)

class syllable(_node):
    """
    A ‘syllable’ is a technical unit. It is the smallest, non-splittable
    collection of letters rendered in one text style. Its sequence argument
    is a unicode string, not a list!
    """
    soft_hyphen_character = unicodedata.lookup("soft hyphen")
    hyphen_character = unicodedata.lookup("hyphen")
    
    def __init__(self, letters, style=None, whitespace_style=None,
                 soft_hyphen=None):
        if type(letters) == types.StringType:
            letters = unicode(letters)
            
        assert type(letters) == types.UnicodeType, TypeError
        assert letters != u"", ValueError

        if letters[-1] == self.soft_hyphen_character:
            self._soft_hyphen = True
            letters = letters[:-1]
        else:
            self._soft_hyphen = soft_hyphen

        assert self.soft_hyphen_character not in letters, ValueError(
            "Soft hyphens are only allowed as the last character of "
            "a syllable.")

        self.letters = letters
        _node.__init__(self, list(letters), style)
        self._whitespace_style = whitespace_style

    def append(self, letter):
        self._check_child(letter)
        list.append(self, letter)
        
    def _check_child(self, child):
        assert type(child) == types.UnicodeType, TypeError(
            "Need Unicode letter, not %s" % repr(child))
        
    @property
    def soft_hyphen(self):
        return self._soft_hyphen

    @property
    def font(self):
        ff = self.style.font_family
        return ff.getfont(self.style.text_style,
                          self.style.font_weight)
        
    @property
    def font_metrics(self):
        return self.font.metrics
        
    def width(self):
        """
        Return the width of this syllable on the page in PostScript units.
        """
        return self.font_metrics.stringwidth(
            self.letters,
            self.style.font_size,
            self.style.kerning,
            self.style.char_spacing)

    def height(self):
        return self.style.line_height

    def cenders(self, pad_for_line_height=True):
        """
        Return a tripple of floats, ascender, median and descender of the
        current font scaled to our text style’s size.
        """
        factor = self.style.font_size / 1000.0
        ascender, descender = ( self.font_metrics.ascender * factor,
                                self.font_metrics.descender * factor, )
        median = self.style.font_size - (ascender + descender)

        if pad_for_line_height:
            padding = ( self.style.line_height - ( self.style.font_size ) ) / 2
            return ascender + padding, median, descender + padding
        else:
            return ascender, median, descender


    def space_width(self):
        """
        Return the with of a space character in our font.
        """
        if self._whitespace_style:
            whitespace_style = self._whitespace_style
        else:
            whitespace_style = self.parent.style

        # This assumes the font has a space character. If this makes your
        # program crash, the bug is in the font file :-P
        metric = self.font_metrics[32].width # 32 = " "
        return metric * whitespace_style.font_size / 1000.0
    
    def __repr__(self, indentation=0):
        return "%s %s %s %.1f×%.1f" % ( self.__class__.__name__,
                                        repr("".join(self)),
                                        self._style_info(),
                                        self.width(), self.height(), )
        
    def __print__(self, indentation=0):
        print indentation * "  ", repr(self)

        
    def render(self, canvas):
        """
        Render this syllable to `canvas`. This assumes the cursor is located
        right at our first letter.
        """
        font = self.style.font_family.getfont(self.style.text_style,
                                              self.style.font_weight)
        font_wrapper = canvas.page.register_font(font)
        font_size = self.style.font_size        
        
        current_font = getattr(canvas.page, "_syllable__current_font", None)
        if current_font:
            ps_name, size, color = current_font
        else:
            ps_name, size, color = None, None, None,

        if not (ps_name == font.ps_name and \
                size == font_size and \
                color == self.style.color ):
            
            # We have to set and select the font
            print >> canvas, "/%s findfont" % font_wrapper.ps_name()
            print >> canvas, "%f scalefont" % font_size
            print >> canvas, "setfont"
            print >> canvas, self.style.color

            canvas.page._syllable__current_font = ( font_wrapper.ps_name,
                                                    font_size,
                                                    self.style.color, )

        def kerning_for_pairs():
            """
            For each characters in this syllable, return the kerning between
            it and the next character.
            """
            for char, next_ in here_and_next(self):
                if next_ is None:
                    yield 0.0
                else:
                    yield font_wrapper.font.metrics.kerning_pairs.get(
                        ( char, next_, ), 0.0)

        if self.style.kerning:
            kerning = kerning_for_pairs()
        else:
            kerning = itertools.repeat(0.0)

        spacing = self.style.char_spacing
        char_widths = map(lambda char: font_wrapper.font.metrics.stringwidth(
            char, font_size), self)
        char_offsets = map(lambda (width, kerning,): width + kerning + spacing,
                           zip(char_widths, kerning))
        char_offsets = map(lambda f: "%.2f" % f, char_widths)        
        glyph_representation = font_wrapper.postscript_representation(
            map(ord, self))
        
        print >> canvas, "(%s) [ %s ] xshow" % ( glyph_representation,
                                                 " ".join(char_offsets), )
        
            
            