#!/usr/bin/env python
import argparse
import sys
import codecs

if sys.version_info[0] == 2:
    from itertools import izip
else:
    izip = zip
from collections import defaultdict as dd
import re
import os.path
import gzip
import tempfile
import shutil
import atexit
import copy
import string

# Use word_tokenize to split raw text into words
from string import punctuation

import nltk
from nltk.tokenize import word_tokenize

scriptdir = os.path.dirname(os.path.abspath(__file__))

reader = codecs.getreader('utf8')
writer = codecs.getwriter('utf8')


def prepfile(fh, code):
    if type(fh) is str:
        fh = open(fh, code)
    ret = gzip.open(fh.name, code if code.endswith("t") else code + "t") if fh.name.endswith(".gz") else fh
    if sys.version_info[0] == 2:
        if code.startswith('r'):
            ret = reader(fh)
        elif code.startswith('w'):
            ret = writer(fh)
        else:
            sys.stderr.write("I didn't understand code " + code + "\n")
            sys.exit(1)
    return ret


def addonoffarg(parser, arg, dest=None, default=True, help="TODO"):
    ''' add the switches --arg and --no-arg that set parser.arg to true/false, respectively'''
    group = parser.add_mutually_exclusive_group()
    dest = arg if dest is None else dest
    group.add_argument('--%s' % arg, dest=dest, action='store_true', default=default, help=help)
    group.add_argument('--no-%s' % arg, dest=dest, action='store_false', default=default, help="See --%s" % arg)


class LimerickDetector:
    def __init__(self):
        """
        Initializes the object to have a pronunciation dictionary available
        """
        self._pronunciations = nltk.corpus.cmudict.dict()
        self._vowellist = {'AA': 1, 'AE': 2, 'AH': 3, 'AO': 4, 'AW': 5, 'AX': 6, 'AY': 7, 'EH': 8, 'ER': 9, 'EY': 10,
                           'IH': 11, 'IY': 12, 'OW': 13, 'OY': 14, 'UH': 15, 'UW': 16}

    def num_syllables(self, word):
        """
        Returns the number of syllables in a word.  If there's more than one
        pronunciation, take the shorter one.  If there is no entry in the
        dictionary, return 1.
        """
        word = word.lower()
        if word in self._pronunciations:
            min_num_syllable = 100
            for pronun in self._pronunciations[word]:
                count = 0
                for charcter in pronun:
                    vowel = filter(str.isalpha, charcter.encode())
                    if vowel in self._vowellist:
                        count += 1
                min_num_syllable = min(min_num_syllable, count)
            return min_num_syllable

        else:
            return 1
            # TODO: provide an implementation!

    def rhymes(self, a, b):
        """
        Returns True if two words (represented as lower-case strings) rhyme,
        False otherwise.
        """
        listA = []
        listB = []
        for unit in self._pronunciations[a]:
            templistA = []
            for a in unit:
                templistA.append(str(a))
            listA.append(templistA)
        for unit in self._pronunciations[b]:
            templistB = []
            for b in unit:
                templistB.append(str(b))
            listB.append(templistB)

        copyListA = copy.deepcopy(listA)
        copyListB = copy.deepcopy(listB)
        copyListA.extend(copyListB)

        lendict={}
        pronunlist=[]
        for pronun in copyListA:
            templist = []
            count=0
            for p in pronun:
                if p[:2] in self._vowellist or count==1:
                    templist.append(p)
                    count=1
            pronunlist.append(templist)
        for pl in pronunlist:
            unit=tuple(pl)
            if unit in lendict:
                return True
            lendict[unit] = len(unit)
        char=min(lendict.items(),key=lambda d:d[1])[0]

        copypronunlist=copy.deepcopy(pronunlist)
        copypronunlist.remove(list(char))
        for pl2 in copypronunlist:

            if pl2[-len(char):]==list(char):
                return True

        # TODO: provide an implementation!

        return False


    def is_limerick(self, text):
        """
        Takes text where lines are separated by newline characters.  Returns
        True if the text is a limerick, False otherwise.

        A limerick is defined as a poem with the form AABBA, where the A lines
        rhyme with each other, the B lines rhyme with each other, and the A lines do not
        rhyme with the B lines.


        Additionally, the following syllable constraints should be observed:
          * No two A lines should differ in their number of syllables by more than two.
          * The B lines should differ in their number of syllables by no more than two.
          * Each of the B lines should have fewer syllables than each of the A lines.
          * No line should have fewer than 4 syllables

        (English professors may disagree with this definition, but that's what
        we're using here.)


        """
        textafter = text.translate(None, '",.!@#$%^&*()_+{}|:<>?/;][=-')
        dealtext = textafter.split('\n')
        wordlist = []
        for line in dealtext:
            wordline = word_tokenize(line)
            if wordline:
                wordlist.append(wordline)

        Alines = []
        Blines = []
        taillist = []
        if len(wordlist) == 5:
            Alines.append(wordlist[0])
            Alines.append(wordlist[1])
            Alines.append(wordlist[4])
            Blines.append(wordlist[2])
            Blines.append(wordlist[3])
            copyAlines = copy.deepcopy(Alines)
            copyBlines = copy.deepcopy(Blines)
            for a in copyAlines:
                tailA = a.pop()
                taillist.append(tailA)
            for b in copyBlines:
                tailB = b.pop()
                taillist.append(tailB)
            if self.rhymes(taillist[0], taillist[1]) and self.rhymes(taillist[0], taillist[2]) and self.rhymes(
                    taillist[1], taillist[2]) and self.rhymes(taillist[3], taillist[4]) is True:
                numberlistA = []

                for eachline in Alines:
                    TotalnumberA = 0
                    for word in eachline:
                        numberA = self.num_syllables(word)
                        TotalnumberA = TotalnumberA + numberA
                    numberlistA.append(TotalnumberA)
                numberlistA.sort()
                if numberlistA[2] - numberlistA[0] > 2:
                    return False

                numberlistB = []
                for eachline in Blines:
                    TotalnumberB = 0
                    for word in eachline:
                        numberB = self.num_syllables(word)
                        TotalnumberB = TotalnumberB + numberB
                    numberlistB.append(TotalnumberB)
                numberlistB.sort()
                if numberlistB[1] - numberlistB[0] > 2:
                    return False

                if numberlistA[0] - numberlistB[1] < 0:
                    return False

                if numberlistA[0] < 4 or numberlistB[0] < 4:
                    return False

                return True
            else:
                return False


        else:
            return False

            # TODO: provide an implementation!


# The code below should not need to be modified
def main():
    parser = argparse.ArgumentParser(
        description="limerick detector. Given a file containing a poem, indicate whether that poem is a limerick or not",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    addonoffarg(parser, 'debug', help="debug mode", default=False)
    parser.add_argument("--infile", "-i", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input file")
    parser.add_argument("--outfile", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout,
                        help="output file")

    try:
        args = parser.parse_args()
    except IOError as msg:
        parser.error(str(msg))

    infile = prepfile(args.infile, 'r')
    outfile = prepfile(args.outfile, 'w')

    ld = LimerickDetector()
    lines = ''.join(infile.readlines())
    outfile.write("{}\n-----------\n{}\n".format(lines.strip(), ld.is_limerick(lines)))


if __name__ == '__main__':
    main()
